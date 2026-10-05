"""Generate a deterministic, public-safe receivables demo dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


CUSTOMERS = [
    "晨曦医疗科技",
    "远航智能制造",
    "青禾生物",
    "星海数字科技",
    "华川供应链",
    "云杉新材料",
    "北辰仪器",
    "澄明数据服务",
    "启元工业",
    "江岚医药",
    "栖木电子",
    "锐光自动化",
]


def build_sample_data(seed: int = 20261005, rows: int = 96) -> pd.DataFrame:
    """Return reproducible synthetic invoices with varied collection risk."""
    rng = np.random.default_rng(seed)
    analysis_date = pd.Timestamp("2026-10-05")
    issue_dates = pd.to_datetime(
        rng.integers(
            pd.Timestamp("2025-11-01").value // 10**9,
            pd.Timestamp("2026-09-20").value // 10**9,
            size=rows,
        ),
        unit="s",
    ).normalize()
    terms = rng.choice([30, 45, 60, 90], size=rows, p=[0.45, 0.25, 0.2, 0.1])
    due_dates = issue_dates + pd.to_timedelta(terms, unit="D")
    amounts = np.round(rng.uniform(8_000, 260_000, size=rows), 2)
    collection_state = rng.choice(
        ["paid", "partial", "unpaid"], size=rows, p=[0.56, 0.29, 0.15]
    )

    received = np.zeros(rows)
    actual_dates: list[pd.Timestamp | None] = []
    for index, state in enumerate(collection_state):
        if state == "paid":
            received[index] = amounts[index]
            delay = int(rng.integers(-8, 75))
            actual_dates.append(min(due_dates[index] + pd.Timedelta(days=delay), analysis_date))
        elif state == "partial":
            received[index] = round(amounts[index] * rng.uniform(0.15, 0.75), 2)
            actual_dates.append(None)
        else:
            received[index] = 0.0
            actual_dates.append(None)

    frame = pd.DataFrame(
        {
            "客户名称": rng.choice(CUSTOMERS, size=rows),
            "账单编号": [f"INV-{20260001 + index}" for index in range(rows)],
            "账单金额": amounts,
            "实收金额": received,
            "应付日期": due_dates,
            "实际到账日": actual_dates,
            "账单周期": issue_dates.to_period("Q").astype(str),
        }
    )
    return frame.sort_values("应付日期").reset_index(drop=True)


def write_sample_files(output_dir: Path | None = None) -> tuple[Path, Path]:
    """Write CSV and Excel sample files and return their paths."""
    target = output_dir or Path(__file__).resolve().parents[1] / "data"
    target.mkdir(parents=True, exist_ok=True)
    frame = build_sample_data()
    csv_path = target / "sample_receivables.csv"
    excel_path = target / "sample_receivables.xlsx"
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    frame.to_excel(excel_path, index=False)
    return csv_path, excel_path


if __name__ == "__main__":
    csv_file, excel_file = write_sample_files()
    print(f"Generated: {csv_file}")
    print(f"Generated: {excel_file}")

