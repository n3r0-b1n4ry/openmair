# Change Tracking — Multi-Agent AIOps MoA

---

## [2026-06-14] Integration of Executor Agent, Real-time Logging, and Dashboard Updates
- **Executor Agent**: Implemented `ExecutorAgent` to translate Judge remediation recommendations into concrete actions, adding Human-in-the-Loop CLI validation before executing scripts/commands.
- **Real-time Logging Pipeline**: Added queue-based asynchronous `ElasticsearchLogHandler` to stream live agent reasoning and executor action traces to Elasticsearch.
- **Judge Evaluation Integration**: Integrated the Judge evaluation scores into the indexed proposer reports' metadata in Elasticsearch.
- **Dashboard Upgrades**: Added **Action History** log panels and **Average Proposer Scores** bar gauge charts to both Grafana and Kibana dashboards.
- **Model Upgrades**: Replaced `"SaoLa4-small"` with `"DeepSeek-V4-Flash"` as proposer, set default Judge model to `"gpt-5.4"`, and default Executor model to `"gpt-5.4-nano"`.

---

## [2026-05-15] Documentation Update for Latest Models & Infrastructure
- Synchronized all documentation to match `config.py` model variables (Qwen 3.6 27B, GPT OSS 20B, SaoLa4-medium, Gemma 4 26B A4B IT, Qwen3-32B, GPT-5.5, GPT-5.4-mini).
- Updated Elasticsearch logging pipeline documentation to reflect changes in benchmark ingestion.

---

## [2026-03-19] Full Repo Review & Bug Fixes

### 🔴 Critical Fixes (5)

| # | File | Description |
|---|------|-------------|
| 1 | `agents/proposers.py` | Migrate `ChatOllama` import from `langchain_community` (deprecated) → `langchain_ollama` |
| 2 | `agents/model_router.py` | Fix dynamic attribute `balanced_score` assignment on `@dataclass` → use helper function |
| 3 | `orchestrator/state.py` | Fix `AIOpsState` to use `Annotated[list, operator.add]` (LangGraph standard) instead of Pydantic `Field()` on TypedDict |
| 4 | `infrastructure/vector_db.py` | Remove `AnthropicEmbeddings` (Anthropic does not provide an embedding API) |
| 5 | `infrastructure/vector_db.py` | Migrate `PineconeVectorDB` from Pinecone SDK v1 (`pinecone.init()`) → v3+ (`Pinecone()`) |

### 🟡 High Fixes (4)

| # | File | Description |
|---|------|-------------|
| 6 | `main.py` | Simplify `initial_state` — remove redundant keys (LangGraph auto-initializes from reducer) |
| 7 | `AGENTS.md` | Update model list to match code (Llama 3.3, QwQ-32B, DeepSeek R1 Distill) |
| 8 | `requirements-core.txt` | Remove `deepseek-openai` (does not exist on PyPI); add `langchain-ollama`, `langchain-community` |
| 9 | `prompts/` | Empty package → create `prompts/templates.py` containing prompt templates extracted from proposers.py and judge.py |

### 🟢 Medium Fixes (4)

| # | File | Description |
|---|------|-------------|
| 10 | `agents/proposers.py` | Replace `asyncio.get_event_loop().time()` (deprecated Python ≥3.10) → `datetime.now().isoformat()` |
| 11 | `agents/model_router.py` | Fix type hint `fallback_chain: List[str]` → `List[List[str]]` |
| 12 | `evals/__init__.py` | Add exports for evaluator classes |
| 13 | `infrastructure/__init__.py` | Add exports for infrastructure classes |

---

## [2026-03] 2026 Update — Refactor Notes

### Key Changes

1. **LLM Model List Upgrade (2026):**
   - **Proposers:** Replace Llama 3.1 70B → Llama 3.3 70B (lighter, benchmark comparable to 400B)
   - **Proposers:** Replace Mistral Large 2 → QwQ-32B (better chain-of-thought reasoning)
   - **Proposers:** Add DeepSeek R1 Distill Llama 70B (powerful reasoning model)
   - **Judge:** Default Judge → Claude 3.7 Sonnet (best hybrid reasoning)
   - **Judge:** Fallback Judge → OpenAI o3-mini (for extremely difficult code/log logic with reasoning_effort)

2. **Orchestrator & Graph Improvements:**
   - Improved routing logic in `orchestrator/router.py` with graceful degradation
   - Added `route_after_evaluation` router to decide whether to run the executor
   - All node functions validate inputs to prevent graph crashes

3. **Dependencies Optimization:**
   - Split `requirements.txt` into 2 files:
     - `requirements-core.txt`: Core dependencies to run the system
     - `requirements-eval.txt`: Evaluation frameworks (only used for offline benchmarking)
   - Reduced dependency footprint for production environments

4. **Docker Compose Light:**
   - Added `infrastructure/docker-compose.light.yml` for single-GPU lab
   - Runs only 1 vLLM container + Redis (saves RAM/VRAM)
   - Removed Milvus, MinIO, etcd, Nginx, Prometheus, Grafana

### Model Router Updates

- Updated `ModelCapability` with new costs and performance for 2026 models
- Updated `fallback_chain` to prioritize Claude 3.7 Sonnet and o3-mini for critical tasks
- Added support for the reasoning_effort parameter for o3-mini

### Migration Guide

If you are using an older version:
1. Update dependencies: `pip install -r requirements-core.txt`
2. Update environment variables in `config.py` (already updated)
3. Restart Docker services: `docker-compose down && docker-compose up -d`
4. (Optional) Switch to the light profile: `docker-compose -f infrastructure/docker-compose.light.yml up -d`
