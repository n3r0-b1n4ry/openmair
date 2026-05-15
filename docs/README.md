# Multi-Agent AIOps System with LLM-As-A-Judge Mechanism

## Introduction

This system is an advanced AIOps (AI for IT Operations) solution using a Mixture-of-Agents architecture combined with an LLM-as-a-Judge mechanism to automate the process of detecting, analyzing, and resolving incidents in modern IT infrastructure.

## System Architecture

The system consists of three main types of agents:

1. **Proposers (Candidate Agents)**: State-of-the-art open-source LLMs (Qwen 3.6 27B, GPT OSS 20B, SaoLa4-medium, Gemma 4 26B A4B IT, Qwen3-32B) running locally via vLLM, responsible for analyzing incident logs and generating independent RCA reports.

2. **Judge (Evaluator Agent)**: A premium LLM (GPT-5.5 - default, GPT-5.4-mini - fallback, Gemini 3.1 Pro) acting as a judge, evaluating and synthesizing reports from Proposers to make the final decision.

3. **Executor (Execution Agent)**: Performs incident remediation actions based on the Judge's decision.

The entire workflow is orchestrated by LangGraph, maintaining a global state shared across all agents.

## Directory Structure

```
.
├── agents/                 # Agent definitions
│   ├── proposers.py        # Proposer agents
│   ├── judge.py            # Judge agent
│   └── executor.py         # Executor agent
├── orchestrator/           # Orchestrator
│   ├── state.py            # State definitions
│   ├── router.py           # Router
│   └── graph.py            # Workflow graph (uses router)
├── infrastructure/         # Infrastructure configuration
│   ├── docker-compose.yml  # Full Docker Compose configuration
│   ├── docker-compose.light.yml # Lightweight configuration for single-GPU lab
│   └── nginx.conf          # Nginx configuration
├── prompts/                # Prompt templates
├── evals/                  # Evaluation toolkit
├── .cursor/
│   └── rules/              # Rules for Cursor IDE
├── AGENTS.md               # Architecture overview
├── requirements.txt        # Dependencies (full)
├── requirements-core.txt   # Core libraries to run the system
├── requirements-eval.txt   # Libraries for evaluation frameworks (optional)
├── main.py                 # Main entry point
└── README.md               # Documentation
```

## System Requirements

- Python 3.8+
- Docker and Docker Compose
- NVIDIA GPU (to run local LLM models)

## Installation

1. Install the core Python libraries to run the system:
   ```bash
   pip install -r requirements-core.txt
   ```

2. (Optional) Install additional evaluation frameworks for advanced benchmarking:
   ```bash
   pip install -r requirements-eval.txt
   ```

3. Configure environment variables:
   - Copy the `config.py` file and modify the necessary parameters
   - Ensure `OPENAI_API_KEY` is configured for the Judge Agent

4. Start vLLM services and infrastructure:
   - **Full** (4+ models, ELK, Milvus, Prometheus, Grafana):
     ```bash
     cd infrastructure
     docker-compose up -d
     ```
   - **Lightweight for single-GPU lab** (1 model + Redis):
     ```bash
     cd infrastructure
     docker-compose -f docker-compose.light.yml up -d
     ```
   
   **Note:** The `docker-compose.light.yml` profile only runs 1 vLLM container (e.g., Qwen 3.6 27B) and Redis, suitable for personal machines or labs with a single GPU. To switch models, modify the `model_id` in the `docker-compose.light.yml` file.

## Usage

Run the system:
```bash
python main.py
```

## Benchmarking and Evaluation

The system comes with 10 built-in incident scenarios to evaluate the multi-agent problem-solving and root cause analysis capabilities:

1. **DDoS Attack**: High volume of requests causing API Gateway rate limiting.
2. **Brute Force Login**: Multiple failed authentication attempts and Account Lockout.
3. **DB Connection Pool Exhaustion**: Services failing to acquire DB connections.
4. **Out of Memory Crash**: Memory leak leading to pod termination by OS OOM killer.
5. **Disk Full**: "No space left on device" errors causing app crashes.
6. **DNS Resolution Failure**: Internal service unable to resolve hostname.
7. **Third-Party API Outage**: Payment provider returning 503 or timing out.
8. **Bad Config Deployment**: Invalid credentials deployed causing authentication errors.
9. **Message Queue Backup**: Kafka/RabbitMQ consumer lag spiking.
10. **Database Deadlock**: Concurrent transactions causing deadlocks.

To run the benchmarking script:

```bash
# Run a specific scenario by name or ID
python benchmark.py --scenario ddos

# Run all 10 scenarios sequentially
python benchmark.py --all

# List all available scenarios
python benchmark.py --list
```

## Configuration

Configuration parameters can be modified in the `config.py` file.

### API Keys
- `OPENAI_API_KEY`: API key for OpenAI (required if using GPT-4o)
- `ANTHROPIC_API_KEY`: API key for Anthropic (optional, if using Claude)
- `GOOGLE_API_KEY`: API key for Google (optional, if using Gemini)

### LangSmith Tracing
- `LANGCHAIN_TRACING_V2`: Enable/disable tracing with LangSmith
- `LANGCHAIN_API_KEY`: API key for LangSmith (optional)
- `LANGCHAIN_PROJECT`: Project name in LangSmith

### vLLM Endpoints (2026)
- `LLM_API_BASEURL`: Base URL for the vLLM gateway or services.
- `LLM_API_KEY`: API key for accessing the local models.

### Model Selection (2026)
- `JUDGE_MODEL`: Model for the Judge Agent (default: gpt-5.5)
- `JUDGE_ALTERNATIVE`: Alternative model for the Judge (default: gpt-5.4-mini)
- `GEMINI_PRO_MODEL`: Gemini model for the Judge (default: gemini-3.1-pro)
- `EXECUTOR_MODEL`: Model for the Executor Agent (default: gpt-4o-mini)

### Logging & Optimization
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_CACHING`: Enable/disable caching (default: true)
- `ENABLE_STREAMING`: Enable/disable streaming (default: true)
- `MAX_RETRIES`: Maximum number of retries (default: 3)
- `RETRY_DELAY`: Delay between retries (default: 1.0 seconds)

## Customization

- To change the LLM models used, edit `agents/proposers.py` and `agents/judge.py`
- To adjust Docker configuration, edit `infrastructure/docker-compose.yml` or `infrastructure/docker-compose.light.yml`
- To modify Cursor IDE rules, edit the files in `.cursor/rules/`

## Contributing

Please create an issue or pull request to contribute to the project.
