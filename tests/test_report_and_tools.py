from datetime import date

import pandas as pd

from src.analytics import analyze_receivables
from src.report import generate_html_report, generate_markdown_report
from src.tools import build_analysis_tools


def analyzed_frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "客户名称": ["甲公司", "乙公司"],
            "账单编号": ["A-1", "B-1"],
            "账单金额": [1000.0, 3000.0],
            "实收金额": [1000.0, 0.0],
            "应付日期": pd.to_datetime(["2026-01-01", "2026-01-01"]),
            "实际到账日": pd.to_datetime(["2026-01-10", None]),
            "账单周期": ["2026Q1", "2026Q1"],
        }
    )
    return analyze_receivables(frame, analysis_date=date(2026, 5, 1))


def test_reports_include_metrics_and_customer() -> None:
    frame = analyzed_frame()
    markdown = generate_markdown_report(frame)
    html = generate_html_report(frame)

    assert "¥3,000.00" in markdown
    assert "乙公司" in markdown
    assert "应收账款风险分析报告" in html
    assert "乙公司" in html


def test_analysis_tools_are_bound_to_current_frame() -> None:
    tools = {tool.__name__: tool for tool in build_analysis_tools(analyzed_frame())}

    assert '"总未收金额": 3000.0' in tools["get_portfolio_overview"]()
    assert "乙公司" in tools["get_top_outstanding_customers"](1)
    assert "90天以上" in tools["get_aging_analysis"]()
    assert "没有找到" in tools["analyze_customer"]("不存在")
    assert "催收建议" not in tools["generate_receivables_report"]()
    assert "## 建议" in tools["generate_receivables_report"]()

