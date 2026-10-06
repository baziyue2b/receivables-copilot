"""Generate portable receivables risk reports."""

from __future__ import annotations

from html import escape

import pandas as pd

from src.analytics import aging_summary, customer_risk_summary, summary_metrics


def _money(value: float) -> str:
    return f"¥{value:,.2f}"


def generate_markdown_report(frame: pd.DataFrame) -> str:
    """Build a concise, deterministic Markdown risk report."""
    metrics = summary_metrics(frame)
    aging = aging_summary(frame)
    customers = customer_risk_summary(frame)
    high_risk = customers[customers["风险等级"].eq("高")].head(10)
    analysis_date = frame.attrs.get("analysis_date", "未指定")

    lines = [
        "# 应收账款风险分析报告",
        "",
        f"> 分析日期：{analysis_date}",
        "",
        "## 核心指标",
        "",
        f"- 总账单金额：{_money(float(metrics['总账单金额']))}",
        f"- 总实收金额：{_money(float(metrics['总实收金额']))}",
        f"- 总未收金额：{_money(float(metrics['总未收金额']))}",
        f"- 逾期金额：{_money(float(metrics['逾期金额']))}",
        f"- 高风险客户数：{metrics['高风险客户数']}",
        "",
        "## 账龄结构",
        "",
        "| 账龄区间 | 账单数量 | 未收金额 |",
        "| --- | ---: | ---: |",
    ]
    for bucket, row in aging.iterrows():
        lines.append(
            f"| {bucket} | {int(row['账单数量'])} | {_money(float(row['未收金额']))} |"
        )

    lines.extend(["", "## 高风险客户", ""])
    if high_risk.empty:
        lines.append("当前没有被识别为高风险的客户。")
    else:
        lines.extend(
            [
                "| 客户名称 | 未收金额 | 最大逾期天数 |",
                "| --- | ---: | ---: |",
            ]
        )
        for _, row in high_risk.iterrows():
            lines.append(
                f"| {row['客户名称']} | {_money(float(row['未收金额']))} "
                f"| {int(row['最大逾期天数'])} |"
            )

    lines.extend(
        [
            "",
            "## 建议",
            "",
            "1. 优先跟进高风险且未收金额较大的客户。",
            "2. 对 61 天以上账龄建立每周催收清单。",
            "3. 对持续部分回款客户重新评估授信额度和付款条件。",
        ]
    )
    return "\n".join(lines)


def generate_html_report(frame: pd.DataFrame) -> str:
    """Build a standalone HTML report without external assets."""
    markdown_report = generate_markdown_report(frame)
    metrics = summary_metrics(frame)
    customers = customer_risk_summary(frame).head(10)
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(row['客户名称']))}</td>"
        f"<td>{_money(float(row['未收金额']))}</td>"
        f"<td>{int(row['最大逾期天数'])}</td>"
        f"<td><span class='risk risk-{row['风险等级']}'>{row['风险等级']}</span></td>"
        "</tr>"
        for _, row in customers.iterrows()
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>应收账款风险分析报告</title>
<style>
body {{ margin: 0; background: #f4f1e8; color: #12233f; font-family: 'Noto Serif SC', serif; }}
main {{ max-width: 980px; margin: 40px auto; padding: 42px; background: #fffdf7; border: 1px solid #ded7c7; }}
h1 {{ font-size: 34px; margin-top: 0; }}
.date {{ color: #657086; }}
.metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 28px 0; }}
.card {{ padding: 18px; background: #eef2f1; border-top: 3px solid #d36b32; }}
.card span {{ display: block; color: #657086; font-size: 13px; }}
.card strong {{ display: block; margin-top: 8px; font-size: 24px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 12px; border-bottom: 1px solid #ded7c7; text-align: left; }}
.risk {{ padding: 3px 10px; border-radius: 999px; }}
.risk-高 {{ background: #f8d7cf; color: #8f2f1f; }}
.risk-中 {{ background: #f5e7bc; color: #755512; }}
.risk-低 {{ background: #dcebdc; color: #245b35; }}
pre {{ white-space: pre-wrap; background: #f7f5ee; padding: 18px; }}
</style>
</head>
<body><main>
<h1>应收账款风险分析报告</h1>
<p class="date">分析日期：{escape(str(frame.attrs.get('analysis_date', '未指定')))}</p>
<section class="metrics">
<div class="card"><span>总账单金额</span><strong>{_money(float(metrics['总账单金额']))}</strong></div>
<div class="card"><span>总未收金额</span><strong>{_money(float(metrics['总未收金额']))}</strong></div>
<div class="card"><span>逾期金额</span><strong>{_money(float(metrics['逾期金额']))}</strong></div>
</section>
<h2>客户风险排行</h2>
<table><thead><tr><th>客户</th><th>未收金额</th><th>最大逾期天数</th><th>风险</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2>完整摘要</h2><pre>{escape(markdown_report)}</pre>
</main></body></html>"""

