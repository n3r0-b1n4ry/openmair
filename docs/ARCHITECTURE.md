# System Architecture & Flow Diagrams

This document provides a comprehensive visual guide to the Multi-Agent AIOps System. It covers the overall architecture, the internal workflow managed by LangGraph, the step-by-step incident processing sequence, infrastructure deployment topology, the smart model routing logic, and the error handling resilience patterns.

---

## 1. High-Level Architecture

The system follows a **Mixture-of-Agents (MoA)** pattern with three distinct agent tiers. Incident logs enter through the LangGraph Orchestrator, which dispatches them to multiple Proposer agents running in parallel. Each Proposer independently analyzes the logs and produces a Root Cause Analysis (RCA) report. The Judge agent then evaluates all reports, filters out hallucinations, and synthesizes a single optimal solution. Finally, the Executor agent carries out the approved remediation actions using **gpt-5.4-nano** with Human-in-the-Loop CLI validation.

> **Key design principle:** By using multiple diverse LLMs as Proposers and a premium LLM as the Judge, the system reduces individual model biases and hallucinations through cross-validation.

```mermaid
graph TB
    subgraph Input
        LOGS["📋 Incident Logs<br/>(Real-time from Microservices)"]
    end

    subgraph Proposers["Proposer Agents (tini-cybersec-8b-a1b via LM Studio)"]
        P1["tini-cybersec-8b-a1b<br/>(temp=0.2, top_k=40)"]
        P2["tini-cybersec-8b-a1b<br/>(temp=0.3, top_k=42)"]
        P3["tini-cybersec-8b-a1b<br/>(temp=0.4, top_k=45)"]
        P4["tini-cybersec-8b-a1b<br/>(temp=0.5, top_k=48)"]
        P5["tini-cybersec-8b-a1b<br/>(temp=0.6, top_k=50)"]
    end

    subgraph Judge["Judge Agent (Oracle LLM)"]
        J1["DeepSeek-V4-Flash<br/>(default)"]
        J2["gpt-5.4<br/>(alternative)"]
        J3["gpt-5.4-mini<br/>(fallback)"]
        J4["Gemini 3.1 Pro<br/>(alternative)"]
    end

    subgraph Executor["Executor Agent"]
        E1["DeepSeek-V4-Flash<br/>(default)"]
        E2["gpt-5.4-nano<br/>(alternative)"]
    end

    subgraph Orchestrator["LangGraph Orchestrator"]
        STATE["Global State<br/>(AIOpsState)"]
        ROUTER["Conditional Router"]
    end

    LOGS --> ROUTER
    ROUTER --> P1 & P2 & P3 & P4 & P5
    P1 & P2 & P3 & P4 & P5 -->|"Independent RCA Reports"| STATE
    STATE --> J1
    J1 -->|"Synthesized Final Report"| STATE
    STATE --> E1
    E1 -->|"Executed Actions"| OUTPUT["✅ Remediation Result"]

    style Proposers fill:#1a1a2e,stroke:#16213e,color:#e94560
    style Judge fill:#0f3460,stroke:#16213e,color:#e94560
    style Executor fill:#533483,stroke:#16213e,color:#e94560
    style Orchestrator fill:#16213e,stroke:#0f3460,color:#e94560
```

**Component summary:**

| Component | Description | Models |
|-----------|-------------|--------|
| **Proposers** | 5 instances of the tini-cybersec-8b-a1b model running in parallel on a local LM Studio server. Each instance uses unique hyperparameters (temperature, top_k, top_p, repeat_penalty) to diversify analysis perspectives. | tini-cybersec-8b-a1b (x5 with varied parameters) |
| **Judge** | A single premium/local LLM that acts as an oracle. It does not analyze from scratch — instead it evaluates, compares, and synthesizes the Proposers' outputs. | DeepSeek-V4-Flash (default), gpt-5.4 (alternative), gpt-5.4-mini (fallback), Gemini 3.1 Pro (alternative) |
| **Executor** | A lightweight/local model that translates the Judge's final report into concrete remediation actions (e.g., API calls, scripts, restarts). | DeepSeek-V4-Flash (default), gpt-5.4-nano (alternative) |
| **Orchestrator** | LangGraph-based state machine that maintains a shared `AIOpsState` and routes data between agents using conditional edges. | — |

---

## 2. LangGraph Workflow (State Machine)

The workflow is implemented as a **LangGraph StateGraph** with conditional routing. The `route_incident_analysis` function at the entry point inspects the current state to decide which node to enter — this enables the graph to resume from any intermediate state (e.g., if proposals already exist, it skips directly to the Judge).

After the Judge produces an evaluation, a second router (`route_after_evaluation`) checks whether the final report contains valid data before deciding to proceed to the Executor or terminate.

```mermaid
stateDiagram-v2
    [*] --> RouteIncident: START
    
    RouteIncident --> Proposers: Has incident_logs
    RouteIncident --> Judge: Has proposals, no evaluations
    RouteIncident --> Executor: Has evaluations + valid report
    RouteIncident --> [*]: No incident_logs / Already executed
    
    Proposers --> Judge: Proposals generated
    Judge --> EvaluateProposals: Evaluation completed
    
    EvaluateProposals --> RouteAfterEval: Extract final_report
    
    RouteAfterEval --> Executor: Valid final_report
    RouteAfterEval --> [*]: No valid report
    
    Executor --> [*]: Actions executed

    note right of Proposers
        Runs all 5 proposers in parallel
        using asyncio.gather()
    end note

    note right of Judge
        1. Anonymize proposals
        2. Shuffle order (anti-bias)
        3. Chain-of-Thought evaluation
        4. Synthesize optimal solution
    end note

    note right of Executor
        Human-in-the-Loop approval
        before executing actions
    end note
```

**State fields** (defined in `orchestrator/state.py`):

| Field | Type | Description |
|-------|------|-------------|
| `incident_logs` | `str` | Raw incident log text from the monitoring system |
| `proposals` | `Annotated[list, operator.add]` | Accumulated RCA proposals from all Proposers (uses LangGraph reducer) |
| `evaluations` | `Annotated[list, operator.add]` | Judge evaluations (scores, reasoning, final report) |
| `final_report` | `Optional[IncidentReport]` | The synthesized optimal report after Judge evaluation |
| `executed_actions` | `Annotated[list, operator.add]` | List of remediation actions taken by the Executor |

**Routing logic** (defined in `orchestrator/router.py`):

1. **No `incident_logs`** → Terminate immediately (nothing to analyze)
2. **Has `proposals` but no `evaluations`** → Skip to Judge (proposals already generated in a previous run)
3. **Has `evaluations` + valid `final_report`** → Skip to Executor
4. **Has `executed_actions`** → Terminate (already completed)
5. **Default** → Start with Proposers

---

## 3. Incident Processing Sequence

This sequence diagram shows the end-to-end flow for a single incident, from log submission to remediation. The key insight is that **all 5 Proposers run concurrently** using `asyncio.gather()`, which significantly reduces total processing time compared to sequential execution.

The Judge applies several **anti-bias techniques** before evaluation:
- **Identity anonymization**: Proposer IDs are replaced with generic labels (Assistant A, B, C…) so the Judge cannot be influenced by model reputation
- **Order shuffling**: Proposals are randomly reordered to prevent position bias (first/last item bias)
- **Chain-of-Thought**: The Judge first analyzes the logs independently before reading any proposals, ensuring its own reasoning is not anchored by Proposer outputs

```mermaid
sequenceDiagram
    participant User as User/System
    participant Orch as LangGraph Orchestrator
    participant P1 as tini-cybersec-8b-a1b (temp=0.2)
    participant P2 as tini-cybersec-8b-a1b (temp=0.3)
    participant P3 as tini-cybersec-8b-a1b (temp=0.4)
    participant P4 as tini-cybersec-8b-a1b (temp=0.5)
    participant P5 as tini-cybersec-8b-a1b (temp=0.6)
    participant Judge as Judge (DeepSeek-V4-Flash)
    participant Exec as Executor (DeepSeek-V4-Flash)

    User->>Orch: Submit incident logs
    
    Note over Orch: Route: START → Proposers

    par Parallel Analysis
        Orch->>P1: Analyze logs
        Orch->>P2: Analyze logs
        Orch->>P3: Analyze logs
        Orch->>P4: Analyze logs
        Orch->>P5: Analyze logs
    end

    P1-->>Orch: RCA Report A
    P2-->>Orch: RCA Report B
    P3-->>Orch: RCA Report C
    P4-->>Orch: RCA Report D
    P5-->>Orch: RCA Report E

    Note over Orch: Store proposals in State

    Orch->>Judge: Evaluate 5 proposals
    
    Note over Judge: 1. Anonymize identities<br/>2. Shuffle order<br/>3. Chain-of-Thought analysis<br/>4. Score each report (0-10)<br/>5. Synthesize final report

    Judge-->>Orch: Evaluation + Final Report

    Note over Orch: Route: valid report → Executor

    Orch->>Exec: Execute remediation
    Exec-->>Orch: Executed actions
    Orch-->>User: Final result + actions taken
```

**Output structure** — the Judge produces an `Evaluation` object containing:
- `scores`: A list of scores (0–10) for each proposal, allowing comparison
- `best_proposal`: Index of the highest-scoring proposal
- `reasoning`: Detailed Chain-of-Thought explanation of the verdict
- `final_report`: An optimized `IncidentReport` that combines the best elements from all proposals

---

## 4. Infrastructure Deployment

The system leverages **LM Studio** to host the 5 proposer agent instances (utilizing the `tini-cybersec-8b-a1b` model) on a single local OpenAI-compatible server. 

The supporting services are deployed using **Docker Compose** and include the ELK Stack, Redis, Milvus vector database, Prometheus, and Grafana. The application connects directly to LM Studio via the `LOCAL_LLM_API_BASEURL` endpoint.

```mermaid
graph LR
    subgraph Local_Server["Local LLM Server (LM Studio)"]
        LMS["tini-cybersec-8b-a1b<br/>:1234"]
    end

    subgraph Services["Supporting Services"]
        REDIS["Redis<br/>:6379<br/>(Cache + Rate Limit)"]
    end

    subgraph Monitoring["Monitoring Stack"]
        ES["Elasticsearch<br/>:9200"]
        LS["Logstash<br/>:5044"]
        KB["Kibana<br/>:5601"]
        PROM["Prometheus<br/>:9090"]
        GRAF["Grafana<br/>:3000"]
    end

    subgraph VectorDB["Vector Database"]
        MILVUS["Milvus<br/>:19530"]
        ETCD["etcd"]
        MINIO["MinIO"]
    end

    APP["Python App<br/>(main.py)"] --> LMS
    APP --> REDIS
    APP --> ES
    APP --> MILVUS
    MILVUS --> ETCD & MINIO
    LS --> ES
    ES --> KB
    PROM --> GRAF

    style Local_Server fill:#1a1a2e,stroke:#e94560,color:#eee
    style Services fill:#16213e,stroke:#0f3460,color:#eee
    style Monitoring fill:#0f3460,stroke:#533483,color:#eee
    style VectorDB fill:#533483,stroke:#e94560,color:#eee
```

**Port mapping reference:**

| Service | Port | Purpose |
|---------|------|---------|
| LM Studio | 1234 | tini-cybersec-8b-a1b inference (OpenAI-compatible API) |
| Redis | 6379 | Response caching and API rate limiting |
| Elasticsearch | 9200 | Centralized log storage and search |
| Logstash | 5044 | Log processing pipeline |
| Kibana | 5601 | Log visualization dashboard |
| Milvus | 19530 | Vector database for semantic log search |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Metrics visualization dashboard |

---

## 5. Model Router Decision Flow

The **Smart Model Router** (`agents/model_router.py`) dynamically selects the best model for any given task based on a complexity score. The score is computed from four factors:

1. **Input length** — longer inputs score higher (e.g., >10K chars = +3)
2. **Context length** — larger context windows score higher
3. **Reasoning requirement** — tasks needing deep reasoning get +3
4. **Accuracy requirement** — tasks needing high accuracy get +2

The total score maps to one of four complexity tiers: **LOW** (< 2), **MEDIUM** (2–4), **HIGH** (5–7), **CRITICAL** (≥ 8). Within each tier, the router further optimizes for cost, speed, accuracy, or a balanced weighted combination.

```mermaid
flowchart TD
    INPUT["Input Task"] --> ESTIMATE["Estimate Task Complexity"]
    
    ESTIMATE --> |"score >= 8"| CRITICAL["CRITICAL"]
    ESTIMATE --> |"score >= 5"| HIGH["HIGH"]
    ESTIMATE --> |"score >= 2"| MEDIUM["MEDIUM"]
    ESTIMATE --> |"score < 2"| LOW["LOW"]

    CRITICAL --> C_SELECT{"Optimize for?"}
    C_SELECT --> |"accuracy"| C_ACC["Claude Opus 4.7"]
    C_SELECT --> |"cost"| C_COST["Gemini 3.1 Pro"]
    C_SELECT --> |"balanced"| C_BAL["GPT-4o"]

    HIGH --> H_SELECT{"Optimize for?"}
    H_SELECT --> |"accuracy"| H_ACC["DeepSeek R1 Distill 70B"]
    H_SELECT --> |"cost"| H_COST["Devstral Small 2 24B"]
    H_SELECT --> |"balanced"| H_BAL["Gemma 4 27B"]

    MEDIUM --> M_SELECT{"Optimize for?"}
    M_SELECT --> |"accuracy"| M_ACC["Qwen 3.5 27B"]
    M_SELECT --> |"speed"| M_SPEED["Llama 4 17B"]
    M_SELECT --> |"balanced"| M_BAL["Qwen 3.5 27B"]

    LOW --> L_SELECT["GPT-4o Mini"]

    style CRITICAL fill:#e94560,color:#fff
    style HIGH fill:#f39c12,color:#fff
    style MEDIUM fill:#3498db,color:#fff
    style LOW fill:#2ecc71,color:#fff
```

**Fallback behavior:** If the selected model fails (e.g., timeout or API error), the router automatically walks down a pre-defined fallback chain. For example, if **Claude Opus 4.7** fails at the CRITICAL tier, the chain proceeds to **GPT-4o → Gemini 3.1 Pro → DeepSeek R1 Distill → Devstral Small 2 → Gemma 4 → Qwen 3.5 → Llama 4 → GPT-4o Mini**.

---

## 6. Error Handling & Resilience

Every LLM API call in the system is wrapped with **three layers of protection**, applied as stacked decorators via `@with_all_protections()` in `agents/retry_handler.py`:

1. **Rate Limiter** (outermost) — Uses a Token Bucket algorithm to enforce a maximum of 10 requests/second, preventing API throttling and cost spikes
2. **Retry Handler** (middle) — Automatically retries failed requests up to 3 times with exponential backoff (1s → 2s → 4s), handling transient network errors and temporary API outages
3. **Circuit Breaker** (innermost) — After 5 consecutive failures, the circuit "opens" and blocks all requests for 60 seconds. This prevents cascade failures where a broken downstream service is repeatedly hammered with requests. After the recovery timeout, a single test request is sent (HALF_OPEN state) — if it succeeds, the circuit resets to CLOSED.

```mermaid
graph TD
    REQ["LLM API Request"] --> RL{"Rate Limiter<br/>(10 req/s)"}
    
    RL -->|"Allowed"| RETRY["Retry Handler<br/>(3 attempts, exp backoff)"]
    RL -->|"Exceeded"| WAIT["Wait & Retry"]
    WAIT --> RL
    
    RETRY -->|"Success"| SUCCESS["✅ Response"]
    RETRY -->|"Failure"| CB{"Circuit Breaker<br/>(5 failures threshold)"}
    
    CB -->|"CLOSED"| RETRY
    CB -->|"OPEN"| BLOCK["❌ Request Blocked<br/>(60s recovery)"]
    BLOCK -->|"Recovery timeout"| HALF["HALF_OPEN<br/>(Test request)"]
    HALF -->|"Success"| RESET["Reset to CLOSED"]
    HALF -->|"Failure"| BLOCK
    
    RESET --> RETRY

    style SUCCESS fill:#2ecc71,color:#fff
    style BLOCK fill:#e94560,color:#fff
```

**Graceful degradation in the graph:** Beyond the per-request protections above, each LangGraph node function also implements its own graceful degradation. If the Proposers node fails entirely, it returns an empty `proposals` list rather than crashing the graph. The Judge node checks for empty proposals and returns an empty `evaluations` list. The Executor checks for a valid `final_report` before attempting any actions. This ensures the graph always terminates cleanly, even under partial failure conditions.
