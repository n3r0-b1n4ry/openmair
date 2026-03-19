# Theo Dõi Thay Đổi — AIOps Đa Tác Nhân MoA

---

## [2026-03-19] Review & Sửa Lỗi Toàn Bộ Repo

### 🔴 Critical Fixes (5)

| # | File | Mô tả |
|---|------|-------|
| 1 | `agents/proposers.py` | Migrate import `ChatOllama` từ `langchain_community` (deprecated) → `langchain_ollama` |
| 2 | `agents/model_router.py` | Sửa gán dynamic attribute `balanced_score` lên `@dataclass` → dùng helper function |
| 3 | `orchestrator/state.py` | Sửa `AIOpsState` dùng `Annotated[list, operator.add]` (chuẩn LangGraph) thay vì Pydantic `Field()` trên TypedDict |
| 4 | `infrastructure/vector_db.py` | Xóa `AnthropicEmbeddings` (Anthropic không cung cấp embedding API) |
| 5 | `infrastructure/vector_db.py` | Migrate `PineconeVectorDB` từ Pinecone SDK v1 (`pinecone.init()`) → v3+ (`Pinecone()`) |

### 🟡 High Fixes (4)

| # | File | Mô tả |
|---|------|-------|
| 6 | `main.py` | Simplify `initial_state` — bỏ các key thừa (LangGraph tự khởi tạo từ reducer) |
| 7 | `AGENTS.md` | Cập nhật danh sách model cho khớp code (Llama 3.3, QwQ-32B, DeepSeek R1 Distill) |
| 8 | `requirements-core.txt` | Xóa `deepseek-openai` (không tồn tại trên PyPI); thêm `langchain-ollama`, `langchain-community` |
| 9 | `prompts/` | Package trống → tạo `prompts/templates.py` chứa prompt templates tách từ proposers.py và judge.py |

### 🟢 Medium Fixes (4)

| # | File | Mô tả |
|---|------|-------|
| 10 | `agents/proposers.py` | Thay `asyncio.get_event_loop().time()` (deprecated Python ≥3.10) → `datetime.now().isoformat()` |
| 11 | `agents/model_router.py` | Sửa type hint `fallback_chain: List[str]` → `List[List[str]]` |
| 12 | `evals/__init__.py` | Thêm exports cho các evaluator classes |
| 13 | `infrastructure/__init__.py` | Thêm exports cho các infrastructure classes |

---

## [2026-03] Cập Nhật 2026 — Refactor Notes

### Thay đổi chính

1. **Nâng cấp danh sách LLM Models (2026):**
   - **Proposers:** Thay thế Llama 3.1 70B → Llama 3.3 70B (nhẹ hơn, bench tương đương 400B)
   - **Proposers:** Thay thế Mistral Large 2 → QwQ-32B (reasoning chain-of-thought tốt hơn)
   - **Proposers:** Thêm DeepSeek R1 Distill Llama 70B (model reasoning mạnh mẽ)
   - **Judge:** Default Judge → Claude 3.7 Sonnet (hybrid reasoning tốt nhất)
   - **Judge:** Fallback Judge → OpenAI o3-mini (cho logic code/log cực khó với reasoning_effort)

2. **Cải thiện Orchestrator & Graph:**
   - Cải thiện logic routing trong `orchestrator/router.py` với graceful degradation
   - Thêm router `route_after_evaluation` để quyết định có chạy executor không
   - Tất cả node functions đều kiểm tra đầu vào để tránh crash graph

3. **Tối ưu Dependencies:**
   - Tách `requirements.txt` thành 2 file:
     - `requirements-core.txt`: Core dependencies để chạy hệ thống
     - `requirements-eval.txt`: Evaluation frameworks (chỉ dùng khi benchmark offline)
   - Giảm kích thước dependencies cho môi trường production

4. **Docker Compose Light:**
   - Thêm `infrastructure/docker-compose.light.yml` cho lab 1 GPU
   - Chỉ chạy 1 container vLLM + Redis (tiết kiệm RAM/VRAM)
   - Loại bỏ Milvus, MinIO, etcd, Nginx, Prometheus, Grafana

### Model Router Updates

- Cập nhật `ModelCapability` với chi phí và performance mới cho các model 2026
- Cập nhật `fallback_chain` để ưu tiên Claude 3.7 Sonnet và o3-mini cho tasks critical
- Thêm support cho reasoning_effort parameter cho o3-mini

### Migration Guide

Nếu bạn đang sử dụng version cũ:
1. Cập nhật dependencies: `pip install -r requirements-core.txt`
2. Cập nhật biến môi trường trong `config.py` (đã được cập nhật)
3. Restart các services Docker: `docker-compose down && docker-compose up -d`
4. (Tùy chọn) Chuyển sang profile light: `docker-compose -f infrastructure/docker-compose.light.yml up -d`
