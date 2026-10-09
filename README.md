# Receivables Copilot

一个面向应收账款管理的本地 AI Agent。它使用 Pandas 完成可验证的财务计算，使用 Agno 编排只读分析工具，并通过 Ollama 在本地运行 `qwen3:4b`，不需要把账款数据发送到云端模型。

## 核心能力

- 上传 CSV、XLSX 或 XLSM 应收账款文件。
- 自动计算未收金额、历史逾期天数、账龄区间和风险等级。
- 按客户生成 0–100 分的可解释催收优先级、主要原因和建议动作。
- 展示核心指标、账龄分布和客户风险敞口排行。
- 通过自然语言查询客户、金额、账龄和催收优先级。
- 导出分析后 CSV、Markdown 报告和独立 HTML 报告。
- Ollama 不可用时，数据看板仍可正常工作。

## 架构

```text
Streamlit UI
    |
    +-- data_service.py  -> 文件读取、类型转换、字段校验
    +-- analytics.py     -> 金额、逾期、账龄、风险确定性计算
    +-- report.py        -> Markdown / HTML 报告
    +-- tools.py         -> Agent 可调用的只读工具
    +-- agent.py         -> Agno + Ollama qwen3:4b
```

模型不能执行任意 Python 代码，也不能直接修改上传文件。金额和日期由分析引擎计算，Agent 只调用结构化工具并解释结果。

## 快速开始

### 1. 创建 Python 环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. 安装本地模型

从 [Ollama Windows 官方页面](https://ollama.com/download/windows) 安装 Ollama，然后重新打开 PowerShell：

```powershell
ollama pull qwen3:4b
ollama list
```

`qwen3:4b` 下载量约 2.5GB，适合 4GB 显存设备。看板可以在模型下载完成前运行，只是 Agent 对话暂不可用。

### 3. 启动应用

```powershell
python -m streamlit run app.py
```

浏览器访问 `http://localhost:8501`。不上传文件时，应用自动使用 `data/sample_receivables.csv`。

## 输入字段

| 字段 | 说明 |
| --- | --- |
| 客户名称 | 客户或付款方名称 |
| 账单编号 | 唯一账单编号 |
| 账单金额 | 大于 0 的账单金额 |
| 实收金额 | 已收到的金额 |
| 应付日期 | 合同约定付款日期 |
| 实际到账日 | 全额回款日期，未结清时可为空 |
| 账单周期 | 例如 `2026Q3` |

## 示例问题

```text
未收金额最高的五个客户是谁？
90 天以上逾期金额是多少？
分析晨曦医疗科技的回款风险。
按账龄汇总未收金额。
今天最应该优先催收哪些客户？
生成一份应收账款风险报告。
```

## 风险规则

- 高风险：逾期超过 90 天，或未收比例不低于 80% 且逾期超过 60 天。
- 中风险：逾期超过 30 天，或未收比例不低于 50%。
- 低风险：其他情况以及已全额回款账单。

## 催收优先级

催收优先级由 Pandas 确定性计算，满分 100 分：

- 最大逾期天数占 40 分。
- 客户未收金额占 30 分。
- 客户未收比例占 20 分。
- 当前逾期未结清账单率占 10 分。

评分结果分为紧急、高、中、低四档，并生成可解释原因和固定建议动作。大模型只查询和解释结果，不参与评分。

## 测试

```powershell
python -m pytest tests -q
```

测试覆盖数据校验、金额精度、账龄与风险边界、催收优先级评分、全额回款除零处理、Agent 工具白名单、报告生成和 Streamlit 整页冒烟测试。

## 项目结构

```text
.
|-- app.py
|-- data/
|   |-- sample_receivables.csv
|   `-- sample_receivables.xlsx
|-- scripts/
|   `-- generate_sample.py
|-- src/
|   |-- agent.py
|   |-- analytics.py
|   |-- data_service.py
|   |-- report.py
|   `-- tools.py
|-- tests/
|-- requirements.txt
`-- .env.example
```

## 安全说明

- `.env`、上传文件、生成报告和虚拟环境不会提交到 Git。
- 不要把 API Key 写入源码或截图。
- 账款数据默认只在本机处理。
- Agent 只拥有预先定义的只读分析工具。

## 简历描述

> 基于 Agno、Ollama、Pandas 和 Streamlit 开发本地应收账款风险分析 Agent，实现账款校验、账龄分析、客户级催收优先级评分、自然语言工具调用及多格式报告导出；采用确定性财务计算与本地大模型分工架构，并使用 Pytest 覆盖核心业务规则和页面冒烟测试。

