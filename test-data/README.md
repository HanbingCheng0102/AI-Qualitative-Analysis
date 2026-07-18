# Test Data

## `strict_completed_smoke_1row.csv`

This one-row synthetic CSV verifies only the real Ollama first-cluster naming
branch and the `pipelineRuns.status = "completed"` persistence path. It does not
exercise assignment to an existing cluster and is not evidence that a model can
complete a 20- or 150-fragment LLM Semantic run.

Documents generated from this file are development smoke-test data and must not
enter the formal experiment or analysis.
