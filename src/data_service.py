"""Load and validate receivables data from CSV and Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd


REQUIRED_COLUMNS = (
    "客户名称",
    "账单编号",
    "账单金额",
    "实收金额",
    "应付日期",
    "实际到账日",
    "账单周期",
)
AMOUNT_COLUMNS = ("账单金额", "实收金额")
DATE_COLUMNS = ("应付日期", "实际到账日")


class DataValidationError(ValueError):
    """Raised when uploaded receivables data cannot be analyzed safely."""


def _source_name(source: str | Path | BinaryIO) -> str:
    return str(getattr(source, "name", source)).lower()


def _read_table(source: str | Path | BinaryIO) -> pd.DataFrame:
    name = _source_name(source)
    if name.endswith(".csv"):
        return pd.read_csv(source, encoding="utf-8-sig")
    if name.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(source)
    raise DataValidationError("仅支持 CSV、XLSX 和 XLSM 文件。")


def _row_numbers(mask: pd.Series) -> str:
    return "、".join(str(index + 2) for index in mask[mask].index)


def _normalize_amounts(frame: pd.DataFrame) -> None:
    for column in AMOUNT_COLUMNS:
        raw = frame[column]
        cleaned = (
            raw.astype("string")
            .str.strip()
            .str.replace(",", "", regex=False)
            .str.replace("￥", "", regex=False)
            .str.replace("¥", "", regex=False)
        )
        converted = pd.to_numeric(cleaned, errors="coerce")
        invalid = converted.isna()
        if invalid.any():
            raise DataValidationError(
                f"{column} 包含无法识别的金额，Excel 行号：{_row_numbers(invalid)}。"
            )
        frame[column] = converted.astype(float)


def _normalize_dates(frame: pd.DataFrame) -> None:
    due_dates = pd.to_datetime(frame["应付日期"], errors="coerce", format="mixed")
    invalid_due = due_dates.isna()
    if invalid_due.any():
        raise DataValidationError(
            f"应付日期包含无法识别的日期，Excel 行号：{_row_numbers(invalid_due)}。"
        )
    frame["应付日期"] = due_dates

    actual_raw = frame["实际到账日"]
    actual_dates = pd.to_datetime(actual_raw, errors="coerce", format="mixed")
    provided = actual_raw.notna() & actual_raw.astype("string").str.strip().ne("")
    invalid_actual = provided & actual_dates.isna()
    if invalid_actual.any():
        raise DataValidationError(
            "实际到账日包含无法识别的日期，Excel 行号："
            f"{_row_numbers(invalid_actual)}。"
        )
    frame["实际到账日"] = actual_dates


def _validate_business_rules(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise DataValidationError("文件中没有可分析的数据。")

    empty_customer = frame["客户名称"].astype("string").str.strip().eq("")
    if empty_customer.any() or frame["客户名称"].isna().any():
        invalid = empty_customer | frame["客户名称"].isna()
        raise DataValidationError(
            f"客户名称不能为空，Excel 行号：{_row_numbers(invalid)}。"
        )

    frame["客户名称"] = frame["客户名称"].astype("string").str.strip()
    frame["账单编号"] = frame["账单编号"].astype("string").str.strip()
    duplicated = frame["账单编号"].duplicated(keep=False)
    if duplicated.any():
        values = "、".join(frame.loc[duplicated, "账单编号"].drop_duplicates())
        raise DataValidationError(f"发现重复的账单编号：{values}。")

    if (frame["账单金额"] <= 0).any():
        raise DataValidationError("账单金额必须大于 0。")
    if (frame["实收金额"] < 0).any():
        raise DataValidationError("实收金额不能小于 0。")
    if (frame["实收金额"] > frame["账单金额"]).any():
        raise DataValidationError("实收金额不能大于账单金额。")

    paid_without_date = (
        frame["实收金额"].eq(frame["账单金额"])
        & frame["实际到账日"].isna()
    )
    if paid_without_date.any():
        raise DataValidationError(
            "已全额回款的账单必须填写实际到账日，Excel 行号："
            f"{_row_numbers(paid_without_date)}。"
        )


def load_receivables(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Read, normalize, and validate one receivables data file."""
    try:
        frame = _read_table(source)
    except DataValidationError:
        raise
    except Exception as exc:
        raise DataValidationError(f"文件读取失败：{exc}") from exc

    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataValidationError(f"缺少必需字段：{'、'.join(missing)}。")

    frame = frame.loc[:, list(REQUIRED_COLUMNS)]
    _normalize_amounts(frame)
    _normalize_dates(frame)
    _validate_business_rules(frame)
    return frame.reset_index(drop=True)
