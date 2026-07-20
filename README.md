# Multi-Agent AIOps System with LLM-As-A-Judge Mechanism

An advanced AIOps (AI for IT Operations) solution using a **Mixture-of-Agents (MoA)** architecture combined with an **LLM-as-a-Judge** mechanism to automate incident detection, analysis, and remediation in modern IT infrastructure.

## Quick Start

```bash
# Install core dependencies
pip install -r requirements-core.txt

# Configure environment variables
cp infrastructure/env.example .env
# Edit .env with your API keys

# Run the system
python main.py
```

## Architecture

The system uses three types of agents:

| Agent | Role | Models |
|-------|------|--------|
| **Proposers** | Analyze incident logs, generate RCA reports | tini-cybersec-8b-a1b (5 instances with varied parameters) |
| **Judge** | Evaluate and synthesize proposals | DeepSeek-V4-Flash, gpt-5.4, gpt-5.4-mini, Gemini 3.1 Pro |
| **Executor** | Execute remediation actions | DeepSeek-V4-Flash, gpt-5.4-nano |

All proposers run in parallel via **LM Studio** (OpenAI compatible), orchestrated by **LangGraph**.

## Documentation

| Document | Description |
|----------|-------------|
| [README](docs/README.md) | Full installation, configuration, and usage guide |
| [AGENTS](docs/AGENTS.md) | Agent architecture and system overview |
| [MODELS](docs/MODELS.md) | LLM models, performance comparison, recommendations |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | System flow diagrams (Mermaid) |
| [TRACK_CHANGES](docs/TRACK_CHANGES.md) | Changelog and migration guide |

## Project Structure

```
.
├── agents/                 # Agent definitions (Proposers, Judge, Executor)
├── orchestrator/           # LangGraph workflow (State, Router, Graph)
├── prompts/                # Prompt templates
├── infrastructure/         # Docker Compose, Nginx configs
├── evals/                  # Evaluation toolkit
├── docs/                   # Documentation
├── config.py               # System configuration
├── main.py                 # Main entry point
└── requirements-core.txt   # Core dependencies
```

## License

Please create an issue or pull request to contribute to the project.
