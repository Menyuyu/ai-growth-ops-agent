# Acknowledgements

This project builds upon concepts and tools from the following open-source projects and research.

## Design Patterns & Concepts

### Circuit Breaker Pattern
- **Reference**: Netflix Hystrix Circuit Breaker design
- **URL**: https://github.com/Netflix/Hystrix
- **Usage**: The 3-state machine (CLOSED → OPEN → HALF_OPEN) in `core/circuit_breaker.py` is inspired by the Hystrix pattern. Implementation is from scratch.

### Observability Pattern
- **Reference**: OpenTelemetry span/event model
- **URL**: https://opentelemetry.io/
- **Usage**: The structured event logging, span tracking, and token/cost tracking in `core/observability.py` follow OpenTelemetry concepts. Implementation is from scratch.

### Agent Autonomy Levels
- **Reference**: Anthropic agent escalation patterns
- **URL**: https://docs.anthropic.com/claude/docs/agent-escalation
- **Usage**: The 4-level autonomy system (manual / review / auto_safe / auto) in `core/orchestrator.py` is inspired by agent escalation patterns. Implementation is from scratch.

### Harness Engineering & Benchmarking
- **Reference**: Harbor benchmark framework (laude-institute)
- **URL**: https://github.com/laude-institute/harbor
- **Usage**: The concept of agent-based benchmarking with numeric scoring in `tests/benchmark.py` is inspired by Harbor. The test implementation is custom-built for this project's specific agents.

## Open-Source Libraries

### scipy.stats
- **URL**: https://scipy.org/
- **Usage**: `utils/stats.py` uses `scipy.stats.norm.cdf` for Z-test proportions and `scipy.stats.chi2_contingency` for chi-square tests in A/B test analysis.

### pandas
- **URL**: https://pandas.pydata.org/
- **Usage**: `utils/rfm.py` uses `pandas.qcut` for quantile-based RFM scoring.

## Datasets

### Kaggle AIGC Tool Dataset
- **Source**: Kaggle platform
- **URL**: https://www.kaggle.com/ (specific dataset to be added)
- **Usage**: `data/insight_engine.py` loads Kaggle AIGC tool reviews for sentiment analysis, keyword extraction, and competitive landscape analysis. When raw data is unavailable, the system falls back to pre-computed insights.

## Project Structure

This project was developed as a personal project demonstrating AI-driven growth operations capabilities. All core business logic, agent implementations, and orchestration code are original implementations.
