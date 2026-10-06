# Receivables Copilot Design

## Goal

Build a resume-ready local accounts receivable analysis agent in three days. The application accepts CSV or Excel data, calculates receivables risk metrics, answers natural-language questions through safe tools, displays charts, and exports a report. The demo runs locally and is recorded as a short portfolio video.

## Technology

- Python 3.11
- Streamlit for the user interface
- Pandas for validation and financial calculations
- Agno for agent and tool orchestration
- Ollama with `qwen3:4b` for local inference
- Plotly for interactive charts
- Pytest for automated tests

The application remains useful when Ollama is unavailable: data upload, metrics, tables, and charts continue working, while the chat area shows a clear model-connection error.

## Architecture

The project uses focused modules with explicit responsibilities:

- `app.py`: Streamlit layout, session state, file upload, dashboard, chat, and downloads.
- `src/data_service.py`: CSV/Excel loading, column normalization, type conversion, and validation.
- `src/analytics.py`: deterministic financial calculations and aggregations.
- `src/tools.py`: safe, read-only tools exposed to the agent.
- `src/agent.py`: Ollama model configuration and Agno agent construction.
- `src/report.py`: Markdown and HTML report generation.
- `scripts/generate_sample.py`: reproducible synthetic receivables dataset generation.
- `tests/`: unit tests for deterministic business logic and validation.

The language model cannot execute arbitrary Python or issue unrestricted file-system commands. It can only call predefined read-only analysis tools and a report-generation tool whose output is constrained to the application's output directory.

## Input Schema

The sample dataset and uploaded files use these required columns:

- `客户名称`
- `账单编号`
- `账单金额`
- `实收金额`
- `应付日期`
- `实际到账日`
- `账单周期`

`实际到账日` may be empty for unpaid invoices. Amount columns must be numeric after removal of common formatting such as commas and surrounding spaces. Date columns are converted with Pandas and invalid values are reported with row numbers.

## Derived Fields

- `未收金额 = max(账单金额 - 实收金额, 0)`
- If `未收金额 == 0`, `历史逾期天数 = max(实际到账日 - 应付日期, 0)`.
- If `未收金额 > 0`, `历史逾期天数 = max(分析日期 - 应付日期, 0)`.
- `账龄区间` is one of `未逾期`, `1-30天`, `31-60天`, `61-90天`, or `90天以上`.
- `风险等级` is `低`, `中`, or `高` based on overdue days and unpaid ratio.

Risk rules for the first version:

- High risk: overdue more than 90 days, or unpaid ratio at least 80% and overdue more than 60 days.
- Medium risk: overdue more than 30 days, or unpaid ratio at least 50%.
- Low risk: all other invoices.

The analysis date defaults to the current local date and is shown in the interface so calculations are reproducible.

## Dashboard

The main page contains:

1. File upload and bundled sample-data selection.
2. Summary cards for billed amount, received amount, outstanding amount, overdue amount, and high-risk customer count.
3. Aging-distribution chart, customer-risk ranking, and invoice detail table.
4. Agent chat with example questions.
5. Download buttons for cleaned data and the generated risk report.

The visual direction is a light financial dashboard with high contrast, restrained blue and amber accents, and clear risk colors. Desktop is the primary demo target, while the layout remains usable on a narrow screen.

## Agent Capabilities

The agent supports questions such as:

- Which five customers have the highest outstanding balances?
- What is the total balance overdue by more than 90 days?
- Analyze the collection risk for a named customer.
- Summarize balances by aging bucket.
- Generate an accounts receivable risk report.

Tools return structured dictionaries or compact Markdown rather than the entire DataFrame. This keeps prompts small and prevents the model from inventing calculations that should be performed deterministically.

## Error Handling

- Empty or unsupported files produce a user-facing message without stopping the app.
- Missing required columns are listed explicitly.
- Invalid amounts and dates report affected columns and row numbers.
- Duplicate bill numbers produce a validation warning and require correction.
- Ollama connection failures disable chat but do not disable the dashboard.
- Tool failures are logged and returned to the agent as concise safe errors.
- Report generation failure does not discard the analyzed dataset.

## Testing

Unit tests cover:

- Outstanding balance calculation.
- Paid and unpaid overdue-day calculation.
- Aging bucket boundaries.
- Risk-level boundaries.
- Required-column validation.
- Numeric and date conversion errors.
- Customer and aging aggregations.

A manual end-to-end check covers sample generation, upload, dashboard rendering, five representative agent questions, and report download.

## Security

- `.env`, API keys, uploaded files, generated reports, caches, and virtual environments are excluded from Git.
- Existing hard-coded credentials are removed before any application source is committed.
- The local model receives only aggregated data or tool results needed to answer the current question.
- No arbitrary code-execution tool is exposed to the model.

## Acceptance Criteria

- A new user can install dependencies and run the app from README instructions.
- The bundled sample file loads without manual editing.
- All dashboard metrics match deterministic test expectations.
- The app answers the five representative questions through tool calls using local Ollama.
- The app exports cleaned CSV data and a readable risk report.
- Tests pass in a clean environment.
- The repository includes screenshots, architecture explanation, sample questions, and a short demo script suitable for a resume portfolio.
