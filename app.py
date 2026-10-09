"""Streamlit entry point for Receivables Copilot."""

from __future__ import annotations

import os
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.generate_sample import write_sample_files
from src.agent import (
    DEFAULT_MODEL,
    OLLAMA_HOST,
    AgentUnavailableError,
    ask_agent,
    available_ollama_models,
    build_agent,
)
from src.analytics import (
    AGING_ORDER,
    aging_summary,
    analyze_receivables,
    customer_risk_summary,
    summary_metrics,
    collection_priority_summary,
)
from src.data_service import DataValidationError, load_receivables
from src.report import generate_html_report, generate_markdown_report


ROOT = Path(__file__).resolve().parent
SAMPLE_FILE = ROOT / "data" / "sample_receivables.csv"
MODEL_ID = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
MODEL_HOST = os.getenv("OLLAMA_HOST", OLLAMA_HOST)
RISK_COLORS = {"高": "#b84b35", "中": "#d9a441", "低": "#3f7d62"}


st.set_page_config(
    page_title="Receivables Copilot",
    page_icon="RC",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --ink: #10233f;
    --muted: #6b7482;
    --paper: #f4f1e8;
    --panel: #fffdf7;
    --line: #ded7c7;
    --accent: #d36b32;
}
.stApp { background: radial-gradient(circle at 88% 4%, #e5ece7 0, transparent 25%), var(--paper); }
[data-testid="stSidebar"] { background: #12233f; }
[data-testid="stSidebar"] * { color: #f8f4e8; }
[data-testid="stSidebar"] input { color: #10233f; }
.block-container { max-width: 1440px; padding-top: 2rem; }
h1, h2, h3 { font-family: "Noto Serif SC", "Source Han Serif SC", Georgia, serif; color: var(--ink); }
.eyebrow { color: var(--accent); font-size: .76rem; font-weight: 800; letter-spacing: .18em; text-transform: uppercase; }
.hero { padding: 1.6rem 0 1.2rem; border-bottom: 1px solid var(--line); margin-bottom: 1.2rem; }
.hero h1 { font-size: clamp(2.2rem, 5vw, 4.8rem); line-height: .98; margin: .45rem 0 .8rem; }
.hero p { color: var(--muted); max-width: 760px; font-size: 1.03rem; }
[data-testid="stMetric"] { background: var(--panel); border: 1px solid var(--line); border-top: 4px solid var(--accent); padding: 1rem; }
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stMetricValue"] { color: var(--ink); font-family: Georgia, serif; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); }
.status-ok, .status-warn { padding: .8rem 1rem; border-radius: 4px; margin: .5rem 0 1rem; }
.status-ok { background: #dcebdc; color: #245b35; }
.status-warn { background: #f5e7bc; color: #755512; }
.stButton > button, .stDownloadButton > button { border-radius: 2px; border-color: var(--ink); }
</style>
""",
    unsafe_allow_html=True,
)


def money(value: float | int) -> str:
    return f"¥{float(value):,.0f}"


@st.cache_data(show_spinner=False)
def load_uploaded_file(content: bytes, filename: str) -> pd.DataFrame:
    stream = BytesIO(content)
    stream.name = filename
    return load_receivables(stream)


@st.cache_data(ttl=5, show_spinner=False)
def model_status(host: str, model_id: str) -> tuple[bool, str]:
    try:
        models = available_ollama_models(host)
    except AgentUnavailableError as exc:
        return False, str(exc)
    available = any(name == model_id or name.startswith(f"{model_id}:") for name in models)
    if not available:
        return False, f"Ollama 已启动，但尚未下载 {model_id}。"
    return True, f"本地模型 {model_id} 已就绪"


def dataset_fingerprint(frame: pd.DataFrame) -> int:
    return int(pd.util.hash_pandas_object(frame, index=True).sum())


def get_or_create_agent(frame: pd.DataFrame):
    fingerprint = dataset_fingerprint(frame)
    if st.session_state.get("agent_fingerprint") != fingerprint:
        st.session_state.receivables_agent = build_agent(
            frame, model_id=MODEL_ID, host=MODEL_HOST
        )
        st.session_state.agent_fingerprint = fingerprint
        st.session_state.chat_messages = []
    return st.session_state.receivables_agent


if not SAMPLE_FILE.exists():
    write_sample_files(SAMPLE_FILE.parent)

with st.sidebar:
    st.markdown("## 数据控制台")
    uploaded = st.file_uploader("上传账款文件", type=["csv", "xlsx", "xlsm"])
    st.caption("不上传时自动使用公开的模拟数据。")
    analysis_date = st.date_input("分析日期", value=date.today())
    st.divider()
    st.markdown("### 本地 Agent")
    ready, status_message = model_status(MODEL_HOST, MODEL_ID)
    status_class = "status-ok" if ready else "status-warn"
    st.markdown(
        f'<div class="{status_class}">{status_message}</div>', unsafe_allow_html=True
    )
    st.caption(f"服务地址：{MODEL_HOST}")

try:
    if uploaded is None:
        source_frame = load_receivables(SAMPLE_FILE)
        source_label = "模拟数据集"
    else:
        source_frame = load_uploaded_file(uploaded.getvalue(), uploaded.name)
        source_label = uploaded.name
    analyzed = analyze_receivables(source_frame, analysis_date=analysis_date)
except DataValidationError as exc:
    st.error(str(exc))
    st.stop()

metrics = summary_metrics(analyzed)
customer_summary = customer_risk_summary(analyzed)
aging = aging_summary(analyzed).reset_index()
collection_priorities = collection_priority_summary(analyzed)


st.markdown(
    f"""
<section class="hero">
  <div class="eyebrow">Receivables intelligence / {source_label}</div>
  <h1>应收账款<br>风险驾驶舱</h1>
  <p>把分散的账单转化为可验证的账龄、风险和催收优先级。所有金额由 Pandas 确定性计算，Agent 只负责调用工具与解释结果。</p>
</section>
""",
    unsafe_allow_html=True,
)

metric_columns = st.columns(5)
metric_items = [
    ("总账单金额", metrics["总账单金额"]),
    ("总实收金额", metrics["总实收金额"]),
    ("总未收金额", metrics["总未收金额"]),
    ("逾期金额", metrics["逾期金额"]),
]
for column, (label, value) in zip(metric_columns[:4], metric_items):
    column.metric(label, money(value))
metric_columns[4].metric("高风险客户", f"{metrics['高风险客户数']} 家")

st.markdown("## 风险结构")
chart_left, chart_right = st.columns([1, 1.25])
with chart_left:
    aging_chart = px.bar(
        aging,
        x="账龄区间",
        y="未收金额",
        category_orders={"账龄区间": AGING_ORDER},
        color="未收金额",
        color_continuous_scale=["#dce8e0", "#d9a441", "#b84b35"],
        text_auto=".2s",
        title="未收金额账龄分布",
    )
    aging_chart.update_layout(
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title=None,
        yaxis_title="人民币",
    )
    st.plotly_chart(aging_chart, width="stretch")

with chart_right:
    top_customers = customer_summary.head(10).sort_values("未收金额")
    customer_chart = px.bar(
        top_customers,
        x="未收金额",
        y="客户名称",
        orientation="h",
        color="风险等级",
        color_discrete_map=RISK_COLORS,
        title="客户风险敞口 Top 10",
        hover_data=["最大逾期天数", "账单数量"],
    )
    customer_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="未收金额（人民币）",
        yaxis_title=None,
        legend_title=None,
    )
    st.plotly_chart(customer_chart, width="stretch")

st.markdown("## 催收优先级")
st.caption("综合逾期天数、未收金额、未收比例和逾期账单率生成确定性评分。")

priority_columns = [
    "排名",
    "客户名称",
    "优先分数",
    "优先等级",
    "未收金额",
    "最大逾期天数",
    "主要原因",
    "建议动作",
]

st.dataframe(
    collection_priorities.head(10)[priority_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "优先分数": st.column_config.ProgressColumn(
            "优先分数",
            min_value=0,
            max_value=100,
            format="%.1f",
        ),
        "未收金额": st.column_config.NumberColumn(format="¥ %.2f"),
    },
)

st.markdown("## 账单明细")
filter_columns = st.columns(3)
customer_options = ["全部"] + sorted(analyzed["客户名称"].astype(str).unique())
selected_customer = filter_columns[0].selectbox("客户", customer_options)
selected_aging = filter_columns[1].multiselect("账龄", AGING_ORDER, default=AGING_ORDER)
selected_risk = filter_columns[2].multiselect(
    "风险", ["高", "中", "低"], default=["高", "中", "低"]
)

filtered = analyzed[
    analyzed["账龄区间"].isin(selected_aging)
    & analyzed["风险等级"].isin(selected_risk)
]
if selected_customer != "全部":
    filtered = filtered[filtered["客户名称"].eq(selected_customer)]

display_columns = [
    "客户名称",
    "账单编号",
    "账单金额",
    "实收金额",
    "未收金额",
    "应付日期",
    "历史逾期天数",
    "账龄区间",
    "风险等级",
]
st.dataframe(
    filtered[display_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "账单金额": st.column_config.NumberColumn(format="¥ %.2f"),
        "实收金额": st.column_config.NumberColumn(format="¥ %.2f"),
        "未收金额": st.column_config.NumberColumn(format="¥ %.2f"),
        "应付日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
    },
)

markdown_report = generate_markdown_report(analyzed)
html_report = generate_html_report(analyzed)
download_columns = st.columns(3)
download_columns[0].download_button(
    "下载分析后 CSV",
    analyzed.to_csv(index=False).encode("utf-8-sig"),
    file_name="receivables_analyzed.csv",
    mime="text/csv",
    width="stretch",
)
download_columns[1].download_button(
    "下载 Markdown 报告",
    markdown_report.encode("utf-8"),
    file_name="receivables_report.md",
    mime="text/markdown",
    width="stretch",
)
download_columns[2].download_button(
    "下载 HTML 报告",
    html_report.encode("utf-8"),
    file_name="receivables_report.html",
    mime="text/html",
    width="stretch",
)

st.markdown("## 询问 Receivables Copilot")
st.caption("示例：未收金额最高的五个客户是谁？分析晨曦医疗科技的风险。")
for message in st.session_state.get("chat_messages", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not ready:
    st.info(f"完成 Ollama 安装并执行 `ollama pull {MODEL_ID}` 后，即可启用本地 Agent。")
else:
    question = st.chat_input("询问账龄、客户风险或生成报告")
    if question:
        st.session_state.setdefault("chat_messages", []).append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("正在调用分析工具..."):
                try:
                    agent = get_or_create_agent(analyzed)
                    answer = ask_agent(agent, question)
                except AgentUnavailableError as exc:
                    answer = str(exc)
            st.markdown(answer)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )
