from datetime import date

import pandas as pd

from src import agent as agent_module
from src.analytics import analyze_receivables


def test_build_agent_registers_safe_analysis_tools(monkeypatch) -> None:
    frame = pd.DataFrame(
        {
            "客户名称": ["甲公司"],
            "账单编号": ["A-1"],
            "账单金额": [1000.0],
            "实收金额": [0.0],
            "应付日期": pd.to_datetime(["2026-01-01"]),
            "实际到账日": pd.to_datetime([None]),
            "账单周期": ["2026Q1"],
        }
    )
    analyzed = analyze_receivables(frame, analysis_date=date(2026, 5, 1))
    monkeypatch.setattr(
        agent_module, "available_ollama_models", lambda host: ["qwen3:4b"]
    )

    result = agent_module.build_agent(analyzed)
    tool_names = {tool.__name__ for tool in result.tools}

    assert result.name == "Receivables Copilot"
    assert tool_names == {
        "get_portfolio_overview",
        "get_top_outstanding_customers",
        "get_aging_analysis",
        "analyze_customer",
        "generate_receivables_report",
    }
