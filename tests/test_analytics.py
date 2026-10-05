from datetime import date

import pandas as pd

from src.analytics import (
    aging_summary,
    analyze_receivables,
    customer_risk_summary,
    summary_metrics,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "客户名称": ["甲公司", "乙公司", "丙公司", "丁公司"],
            "账单编号": ["INV-001", "INV-002", "INV-003", "INV-004"],
            "账单金额": [1000.0, 2000.0, 1000.0, 1000.0],
            "实收金额": [1000.0, 400.0, 400.0, 1000.0],
            "应付日期": pd.to_datetime(
                ["2026-01-10", "2026-01-01", "2026-03-01", "2026-03-20"]
            ),
            "实际到账日": pd.to_datetime(
                ["2026-01-20", None, None, "2026-03-15"]
            ),
            "账单周期": ["2026Q1"] * 4,
        }
    )


def test_analyze_receivables_calculates_financial_fields() -> None:
    result = analyze_receivables(sample_frame(), analysis_date=date(2026, 4, 1))

    assert result["未收金额"].tolist() == [0.0, 1600.0, 600.0, 0.0]
    assert result["历史逾期天数"].tolist() == [10, 90, 31, 0]
    assert result["账龄区间"].tolist() == ["1-30天", "61-90天", "31-60天", "未逾期"]
    assert result["风险等级"].tolist() == ["低", "高", "中", "低"]


def test_aging_bucket_boundaries() -> None:
    frame = sample_frame().iloc[[1]].copy()
    frame["应付日期"] = pd.to_datetime(["2026-01-31"])
    expected = {
        date(2026, 1, 31): "未逾期",
        date(2026, 2, 1): "1-30天",
        date(2026, 3, 2): "1-30天",
        date(2026, 3, 3): "31-60天",
        date(2026, 4, 1): "31-60天",
        date(2026, 4, 2): "61-90天",
        date(2026, 5, 1): "61-90天",
        date(2026, 5, 2): "90天以上",
    }

    for analysis_date, bucket in expected.items():
        result = analyze_receivables(frame, analysis_date=analysis_date)
        assert result.iloc[0]["账龄区间"] == bucket


def test_summary_metrics_and_groupings() -> None:
    analyzed = analyze_receivables(sample_frame(), analysis_date=date(2026, 4, 1))

    metrics = summary_metrics(analyzed)
    assert metrics == {
        "总账单金额": 5000.0,
        "总实收金额": 2800.0,
        "总未收金额": 2200.0,
        "逾期金额": 2200.0,
        "高风险客户数": 1,
    }

    aging = aging_summary(analyzed)
    assert aging.loc["31-60天", "未收金额"] == 600.0
    assert aging.loc["61-90天", "未收金额"] == 1600.0

    customers = customer_risk_summary(analyzed)
    assert customers.iloc[0]["客户名称"] == "乙公司"
    assert customers.iloc[0]["风险等级"] == "高"
