"""Deterministic accounts receivable calculations and aggregations."""

from __future__ import annotations

from datetime import date

import pandas as pd


AGING_ORDER = ["未逾期", "1-30天", "31-60天", "61-90天", "90天以上"]
RISK_ORDER = {"低": 0, "中": 1, "高": 2}


def _aging_bucket(days: int) -> str:
    if days <= 0:
        return "未逾期"
    if days <= 30:
        return "1-30天"
    if days <= 60:
        return "31-60天"
    if days <= 90:
        return "61-90天"
    return "90天以上"


def _risk_level(outstanding: float, unpaid_ratio: float, overdue_days: int) -> str:
    if outstanding <= 0:
        return "低"
    if overdue_days > 90 or (unpaid_ratio >= 0.8 and overdue_days > 60):
        return "高"
    if overdue_days > 30 or unpaid_ratio >= 0.5:
        return "中"
    return "低"


def analyze_receivables(
    frame: pd.DataFrame,
    analysis_date: date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Add outstanding, overdue, aging, and risk fields to validated data."""
    result = frame.copy()
    current = pd.Timestamp(analysis_date or date.today()).normalize()

    result["未收金额"] = (result["账单金额"] - result["实收金额"]).clip(lower=0)
    result["未收比例"] = result["未收金额"] / result["账单金额"]

    end_dates = result["实际到账日"].where(result["未收金额"].eq(0), current)
    overdue = (end_dates - result["应付日期"]).dt.days.clip(lower=0)
    result["历史逾期天数"] = overdue.astype(int)
    result["账龄区间"] = result["历史逾期天数"].map(_aging_bucket)
    result["风险等级"] = result.apply(
        lambda row: _risk_level(
            float(row["未收金额"]),
            float(row["未收比例"]),
            int(row["历史逾期天数"]),
        ),
        axis=1,
    )
    result.attrs["analysis_date"] = current.date().isoformat()
    return result


def summary_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    """Return headline metrics used by the dashboard and tools."""
    overdue_mask = frame["未收金额"].gt(0) & frame["历史逾期天数"].gt(0)
    high_risk_customers = frame.loc[
        frame["风险等级"].eq("高"), "客户名称"
    ].nunique()
    return {
        "总账单金额": float(frame["账单金额"].sum()),
        "总实收金额": float(frame["实收金额"].sum()),
        "总未收金额": float(frame["未收金额"].sum()),
        "逾期金额": float(frame.loc[overdue_mask, "未收金额"].sum()),
        "高风险客户数": int(high_risk_customers),
    }


def aging_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate balances by aging bucket in business order."""
    summary = (
        frame.groupby("账龄区间", observed=True)
        .agg(账单数量=("账单编号", "count"), 未收金额=("未收金额", "sum"))
        .reindex(AGING_ORDER, fill_value=0)
    )
    summary.index.name = "账龄区间"
    return summary


def customer_risk_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate customer balances and rank them by outstanding exposure."""
    working = frame.copy()
    working["风险分值"] = working["风险等级"].map(RISK_ORDER)
    grouped = (
        working.groupby("客户名称", as_index=False)
        .agg(
            账单数量=("账单编号", "count"),
            账单金额=("账单金额", "sum"),
            实收金额=("实收金额", "sum"),
            未收金额=("未收金额", "sum"),
            最大逾期天数=("历史逾期天数", "max"),
            风险分值=("风险分值", "max"),
        )
        .sort_values(["未收金额", "最大逾期天数"], ascending=False)
        .reset_index(drop=True)
    )
    reverse_risk = {value: key for key, value in RISK_ORDER.items()}
    grouped["风险等级"] = grouped.pop("风险分值").map(reverse_risk)
    return grouped

