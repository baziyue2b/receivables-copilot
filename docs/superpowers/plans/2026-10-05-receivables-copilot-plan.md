# Receivables Copilot Implementation Plan

## Phase 1: Deterministic Data Foundation

1. Add repository security rules and dependency metadata.
2. Define required input columns and validation errors.
3. Implement CSV and Excel loading with numeric and date normalization.
4. Implement outstanding balance, overdue days, aging buckets, and risk levels.
5. Add unit tests for calculations, validation, and aggregation boundaries.
6. Generate a reproducible synthetic portfolio dataset.

## Phase 2: Dashboard and Reporting

1. Build the Streamlit upload and sample-data flow.
2. Add summary cards, aging distribution, customer ranking, and invoice table.
3. Add filters for customer, aging bucket, and risk level.
4. Generate Markdown and HTML risk reports.
5. Add cleaned CSV and report downloads.
6. Verify the dashboard manually with the sample dataset.

## Phase 3: Local Agent

1. Install Ollama and pull `qwen3:4b`.
2. Install Agno and its Ollama client dependency.
3. Define read-only tools that return deterministic analysis results.
4. Construct one reusable Agno agent with concise Chinese instructions.
5. Add chat history and clear connection-error handling.
6. Verify five representative questions and tool calls.

## Phase 4: Portfolio Finish

1. Add README setup, architecture, screenshots, and example questions.
2. Add an `.env.example` without secrets.
3. Run unit tests and an end-to-end smoke check.
4. Scan tracked files for secrets.
5. Add a one-minute demo script and resume-ready project description.

