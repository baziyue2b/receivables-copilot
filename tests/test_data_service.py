from io import BytesIO

import pandas as pd
import pytest

from src.data_service import DataValidationError, load_receivables


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "客户名称": ["甲公司", "乙公司"],
            "账单编号": ["INV-001", "INV-002"],
            "账单金额": ["1,000.00", "2000"],
            "实收金额": ["400", "2,000"],
            "应付日期": ["2026-01-01", "2026-02-01"],
            "实际到账日": [None, "2026-02-10"],
            "账单周期": ["2026Q1", "2026Q1"],
        }
    )


def as_csv(frame: pd.DataFrame) -> BytesIO:
    stream = BytesIO(frame.to_csv(index=False).encode("utf-8-sig"))
    stream.name = "receivables.csv"
    return stream


def test_load_receivables_normalizes_types() -> None:
    result = load_receivables(as_csv(valid_frame()))

    assert result["账单金额"].tolist() == [1000.0, 2000.0]
    assert result["实收金额"].tolist() == [400.0, 2000.0]
    assert pd.api.types.is_datetime64_any_dtype(result["应付日期"])
    assert pd.isna(result.loc[0, "实际到账日"])


def test_missing_columns_are_reported() -> None:
    frame = valid_frame().drop(columns=["账单周期", "客户名称"])

    with pytest.raises(DataValidationError, match="客户名称.*账单周期"):
        load_receivables(as_csv(frame))


def test_invalid_numeric_rows_are_reported() -> None:
    frame = valid_frame()
    frame.loc[1, "账单金额"] = "不是金额"

    with pytest.raises(DataValidationError, match="账单金额.*3"):
        load_receivables(as_csv(frame))


def test_invalid_dates_are_reported() -> None:
    frame = valid_frame()
    frame.loc[0, "应付日期"] = "错误日期"

    with pytest.raises(DataValidationError, match="应付日期.*2"):
        load_receivables(as_csv(frame))


def test_duplicate_bill_numbers_are_rejected() -> None:
    frame = valid_frame()
    frame.loc[1, "账单编号"] = "INV-001"

    with pytest.raises(DataValidationError, match="重复的账单编号.*INV-001"):
        load_receivables(as_csv(frame))


def test_non_positive_bill_amount_is_rejected() -> None:
    frame = valid_frame()
    frame.loc[0, "账单金额"] = "0"

    with pytest.raises(DataValidationError, match="账单金额必须大于 0"):
        load_receivables(as_csv(frame))
