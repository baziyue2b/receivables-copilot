"""Safe read-only tools exposed to the receivables agent."""

from __future__ import annotations

import json
from collections.abc import Callable

import pandas as pd

from src.analytics import (
    aging_summary,
    collection_priority_summary,
    customer_risk_summary,
    summary_metrics,
)
from src.report import generate_markdown_report


def _records_json(frame: pd.DataFrame) -> str:
    return json.dumps(frame.to_dict(orient="records"), ensure_ascii=False, default=str)


def build_analysis_tools(frame: pd.DataFrame) -> list[Callable[..., str]]:
    """Bind one analyzed dataset to a small set of safe agent tools."""

    def get_portfolio_overview() -> str:
        """获取应收账款组合的总账单、实收、未收、逾期及高风险客户指标。"""
        return json.dumps(summary_metrics(frame), ensure_ascii=False)

    def get_top_outstanding_customers(limit: int = 5) -> str:
        """按未收金额从高到低返回客户，limit 必须在 1 到 20 之间。"""
        safe_limit = max(1, min(int(limit), 20))
        return _records_json(customer_risk_summary(frame).head(safe_limit))

    def get_collection_priorities(limit: int = 10) -> str:
        """按催收优先分数返回客户，limit 必须在 1 到 20 之间。"""
        safe_limit = max(1, min(int(limit), 20))
        priorities = collection_priority_summary(frame).head(safe_limit)
        return _records_json(priorities)

    def get_aging_analysis() -> str:
        """按未逾期、1-30天、31-60天、61-90天、90天以上返回账龄统计。"""
        result = aging_summary(frame).reset_index()
        return _records_json(result)

    def analyze_customer(customer_name: str) -> str:
        """按客户名称查询账单、未收金额、最大逾期天数和风险等级。"""
        normalized = customer_name.strip()
        customers = customer_risk_summary(frame)
        matched = customers[
            customers["客户名称"].astype(str).str.contains(normalized, regex=False)
        ]
        if matched.empty:
            return json.dumps(
                {"error": f"没有找到包含“{normalized}”的客户。"}, ensure_ascii=False
            )
        return _records_json(matched)

    def generate_receivables_report() -> str:
        """生成包含核心指标、账龄、高风险客户和催收建议的 Markdown 报告。"""
        return generate_markdown_report(frame)

    return [
        get_portfolio_overview,
        get_top_outstanding_customers,
        get_collection_priorities,
        get_aging_analysis,
        analyze_customer,
        generate_receivables_report,
    ]

