# Hệ Thống AIOps Đa Tác Nhân Kết Hợp Cơ Chế LLM-As-A-Judge

## Giới thiệu

Hệ thống này là một giải pháp AIOps (AI for IT Operations) tiên tiến sử dụng kiến trúc Đa Tác Nhân (Mixture-of-Agents) kết hợp với cơ chế LLM-as-a-Judge để tự động hóa quy trình phát hiện, phân tích và xử lý sự cố trong hạ tầng công nghệ thông tin hiện đại.

## Kiến trúc hệ thống

Hệ thống bao gồm ba loại tác nhân chính:

1. **Proposers (Tác nhân Đề xuất)**: Các LLM mã nguồn mở mới nhất (Qwen 2.5 72B, Llama 3.3 70B, QwQ-32B, DeepSeek V3, DeepSeek R1 Distill Llama 70B) chạy cục bộ qua vLLM, có nhiệm vụ phân tích log sự cố và tạo ra các báo cáo RCA độc lập.

2. **Judge (Tác nhân Giám khảo)**: Một LLM cao cấp (Claude 3.7 Sonnet - default, OpenAI o3-mini - fallback cho logic code/log cực khó, GPT-4o) đóng vai trò giám khảo, đánh giá và tổng hợp các báo cáo từ Proposers để đưa ra quyết định cuối cùng.

3. **Executor (Tác nhân Thực thi)**: Thực hiện các hành động khắc phục sự cố dựa trên quyết định của Judge.

Toàn bộ quy trình được điều phối bởi LangGraph, duy trì một trạng thái toàn cục dùng chung cho tất cả các tác nhân.

## Cấu trúc thư mục

```
.
├── agents/                 # Định nghĩa các tác nhân
│   ├── proposers.py        # Các proposer agent
│   ├── judge.py            # Judge agent
│   └── executor.py         # Executor agent
├── orchestrator/           # Điều phối viên
│   ├── state.py            # Định nghĩa trạng thái
│   ├── router.py           # Bộ định tuyến
│   └── graph.py            # Đồ thị quy trình (sử dụng router)
├── infrastructure/         # Cấu hình hạ tầng
│   ├── docker-compose.yml  # Cấu hình Docker Compose đầy đủ
│   ├── docker-compose.light.yml # Cấu hình nhẹ cho lab 1 GPU
│   └── nginx.conf          # Cấu hình Nginx
├── prompts/                # Các mẫu prompt
├── evals/                  # Bộ công cụ đánh giá
├── .cursor/
│   └── rules/              # Quy tắc cho Cursor IDE
├── AGENTS.md               # Tổng quan kiến trúc
├── requirements.txt        # Thư viện phụ thuộc (đầy đủ)
├── requirements-core.txt   # Thư viện cốt lõi để chạy hệ thống
├── requirements-eval.txt   # Thư viện cho các framework đánh giá (tùy chọn)
├── main.py                 # Tệp chạy chính
└── README.md               # Tài liệu hướng dẫn
```

## Yêu cầu hệ thống

- Python 3.8+
- Docker và Docker Compose
- NVIDIA GPU (để chạy các mô hình LLM cục bộ)

## Cài đặt

1. Cài đặt các thư viện Python cơ bản để chạy hệ thống:
   ```bash
   pip install -r requirements-core.txt
   ```

2. (Tuỳ chọn) Cài thêm các framework đánh giá nếu muốn chạy đánh giá nâng cao:
   ```bash
   pip install -r requirements-eval.txt
   ```

3. Cấu hình biến môi trường:
   - Copy tệp `config.py` và chỉnh sửa các thông số cần thiết
   - Đảm bảo đã cấu hình `OPENAI_API_KEY` cho Judge Agent

4. Khởi động các dịch vụ vLLM và hạ tầng:
   - **Đầy đủ** (4+ model, ELK, Milvus, Prometheus, Grafana):
     ```bash
     cd infrastructure
     docker-compose up -d
     ```
   - **Nhẹ cho lab 1 GPU** (1 model + Redis):
     ```bash
     cd infrastructure
     docker-compose -f docker-compose.light.yml up -d
     ```
   
   **Lưu ý:** Profile `docker-compose.light.yml` chỉ chạy 1 container vLLM (Qwen 2.5 72B hoặc Llama 3.3 70B) và Redis, phù hợp cho máy cá nhân hoặc lab với 1 GPU. Để đổi sang Llama 3.3, sửa `model_id` trong file `docker-compose.light.yml`.

## Sử dụng

Chạy hệ thống:
```bash
python main.py
```

## Cấu hình

Các thông số cấu hình có thể được chỉnh sửa trong tệp `config.py`.

### API Keys
- `OPENAI_API_KEY`: API key cho OpenAI (bắt buộc nếu sử dụng GPT-4o)
- `ANTHROPIC_API_KEY`: API key cho Anthropic (tùy chọn, nếu sử dụng Claude)
- `GOOGLE_API_KEY`: API key cho Google (tùy chọn, nếu sử dụng Gemini)

### LangSmith Tracing
- `LANGCHAIN_TRACING_V2`: Bật/tắt tracing với LangSmith
- `LANGCHAIN_API_KEY`: API key cho LangSmith (tùy chọn)
- `LANGCHAIN_PROJECT`: Tên dự án trong LangSmith

### vLLM Endpoints (2026)
- `VLLM_QWEN_URL`: URL cho dịch vụ vLLM Qwen 2.5 72B (mặc định: http://localhost:8000)
- `VLLM_LLAMA33_URL`: URL cho dịch vụ vLLM Llama 3.3 70B (mặc định: http://localhost:8001)
- `VLLM_QWQ_URL`: URL cho dịch vụ vLLM QwQ-32B (mặc định: http://localhost:8002)
- `VLLM_DEEPSEEK_URL`: URL cho dịch vụ vLLM DeepSeek V3 (mặc định: http://localhost:8003)
- `VLLM_R1_DISTILL_URL`: URL cho dịch vụ vLLM DeepSeek R1 Distill Llama 70B (mặc định: http://localhost:8004)

### Model Selection (2026)
- `JUDGE_MODEL`: Model cho Judge Agent (mặc định: claude-3-7-sonnet - hybrid reasoning tốt nhất)
- `JUDGE_ALTERNATIVE`: Model thay thế cho Judge (mặc định: o3-mini - cho logic code/log cực khó)
- `EXECUTOR_MODEL`: Model cho Executor Agent (mặc định: gpt-4o-mini)
- `O3_REASONING_EFFORT`: Cấu hình reasoning effort cho o3-mini (low, medium, high - mặc định: medium)

### Logging & Optimization
- `LOG_LEVEL`: Mức độ logging (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_CACHING`: Bật/tắt caching (mặc định: true)
- `ENABLE_STREAMING`: Bật/tắt streaming (mặc định: true)
- `MAX_RETRIES`: Số lần retry tối đa (mặc định: 3)
- `RETRY_DELAY`: Thời gian chờ giữa các retries (mặc định: 1.0 giây)

## Tùy chỉnh

- Để thay đổi các mô hình LLM được sử dụng, chỉnh sửa trong `agents/proposers.py` và `agents/judge.py`
- Để điều chỉnh cấu hình Docker, chỉnh sửa `infrastructure/docker-compose.yml` hoặc `infrastructure/docker-compose.light.yml`
- Để thay đổi quy tắc cho Cursor IDE, chỉnh sửa các tệp trong `.cursor/rules/`

## Cập nhật 2026 - Refactor Notes

### Thay đổi chính trong đợt refactor này:

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

### Model Router Updates:

- Cập nhật `ModelCapability` với chi phí và performance mới cho các model 2026
- Cập nhật `fallback_chain` để ưu tiên Claude 3.7 Sonnet và o3-mini cho tasks critical
- Thêm support cho reasoning_effort parameter cho o3-mini

### Migration Guide:

Nếu bạn đang sử dụng version cũ:
1. Cập nhật dependencies: `pip install -r requirements-core.txt`
2. Cập nhật biến môi trường trong `config.py` (đã được cập nhật)
3. Restart các services Docker: `docker-compose down && docker-compose up -d`
4. (Tùy chọn) Chuyển sang profile light: `docker-compose -f infrastructure/docker-compose.light.yml up -d`

## Đóng góp

Vui lòng tạo issue hoặc pull request để đóng góp cho dự án.
