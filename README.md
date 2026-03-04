# Hệ Thống AIOps Đa Tác Nhân Kết Hợp Cơ Chế LLM-As-A-Judge

## Giới thiệu

Hệ thống này là một giải pháp AIOps (AI for IT Operations) tiên tiến sử dụng kiến trúc Đa Tác Nhân (Mixture-of-Agents) kết hợp với cơ chế LLM-as-a-Judge để tự động hóa quy trình phát hiện, phân tích và xử lý sự cố trong hạ tầng công nghệ thông tin hiện đại.

## Kiến trúc hệ thống

Hệ thống bao gồm ba loại tác nhân chính:

1. **Proposers (Tác nhân Đề xuất)**: Các LLM mã nguồn mở mới nhất (Qwen 2.5 72B, Llama 3.1 70B, Mistral Large 2, DeepSeek V3) chạy cục bộ qua vLLM, có nhiệm vụ phân tích log sự cố và tạo ra các báo cáo RCA độc lập.

2. **Judge (Tác nhân Giám khảo)**: Một LLM cao cấp (GPT-4o, Claude 3.5 Sonnet, hoặc Gemini 2.5 Pro) đóng vai trò giám khảo, đánh giá và tổng hợp các báo cáo từ Proposers để đưa ra quyết định cuối cùng.

3. **Executor (Tác nhân Thực thi)**: Thực hiện các hành động khắc phục sự cố dựa trên quyết định của Judge.

Toàn bộ quy trình được điều phối bởi LangGraph, duy trì một trạng thái toàn cục dùng chung cho tất cả các tác nhân.

## Các Model LLM được sử dụng

### Proposer Models (Candidate LLMs)
Hệ thống sử dụng các model mã nguồn mở mới nhất và hiệu quả nhất:

1. **Qwen 2.5 72B** - Model mã nguồn mở mạnh mẽ nhất hiện nay từ Alibaba
   - Hiệu suất vượt trội trong các tác vụ reasoning
   - Hỗ trợ context window lên đến 32K tokens
   - Tối ưu hóa cho các tác vụ phân tích log phức tạp

2. **Llama 3.1 70B** - Model mã nguồn mở phổ biến nhất từ Meta
   - Hiệu suất cân bằng giữa tốc độ và chất lượng
   - Hỗ trợ đa ngôn ngữ tốt
   - Tối ưu hóa cho các tác vụ phân tích sự cố

3. **Mistral Large 2** - Model mã nguồn mở hiệu quả cao từ Mistral AI
   - Hiệu suất vượt trội trong các tác vụ code generation
   - Hỗ trợ context window lớn
   - Tối ưu hóa cho các tác vụ kỹ thuật

4. **DeepSeek V3** - Model mã nguồn mở mới nhất từ DeepSeek AI
   - Hiệu suất cao trong các tác vụ reasoning
   - Hỗ trợ đa ngôn ngữ
   - Tối ưu hóa cho các tác vụ phân tích phức tạp

### Judge Model (Oracle LLM)
Hệ thống hỗ trợ các model cao cấp nhất cho vai trò Judge:

1. **GPT-4o** - Model mạnh mẽ nhất từ OpenAI
   - Hiệu suất vượt trội trong các tác vụ reasoning
   - Hỗ trợ Chain-of-Thought
   - Tối ưu hóa cho các tác vụ đánh giá phức tạp

2. **Claude 3.5 Sonnet** - Model tốt nhất cho reasoning từ Anthropic
   - Hiệu suất vượt trội trong các tác vụ suy luận
   - Hỗ trợ thinking capabilities
   - Tối ưu hóa cho các tác vụ đánh giá chi tiết

3. **Gemini 2.5 Pro** - Model mới nhất từ Google
   - Hiệu suất cao trong các tác vụ đa phương thức
   - Hỗ trợ context window lớn
   - Tối ưu hóa cho các tác vụ đánh giá tổng hợp

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
│   └── graph.py            # Đồ thị quy trình
├── infrastructure/         # Cấu hình hạ tầng
│   ├── docker-compose.yml  # Cấu hình Docker Compose
│   └── nginx.conf          # Cấu hình Nginx
├── prompts/                # Các mẫu prompt
├── evals/                  # Bộ công cụ đánh giá
├── .cursor/
│   └── rules/              # Quy tắc cho Cursor IDE
├── AGENTS.md               # Tổng quan kiến trúc
├── requirements.txt        # Thư viện phụ thuộc
├── main.py                 # Tệp chạy chính
└── README.md               # Tài liệu hướng dẫn
```

## Yêu cầu hệ thống

- Python 3.8+
- Docker và Docker Compose
- NVIDIA GPU (để chạy các mô hình LLM cục bộ)

## Cài đặt

1. Cài đặt các thư viện Python:
   ```bash
   pip install -r requirements.txt
   ```

2. Cấu hình biến môi trường:
   - Copy tệp `config.py` và chỉnh sửa các thông số cần thiết
   - Đảm bảo đã cấu hình `OPENAI_API_KEY` cho Judge Agent

3. Khởi động các dịch vụ vLLM:
   ```bash
   cd infrastructure
   docker-compose up -d
   ```

## Sử dụng

Chạy hệ thống:
```bash
python main.py
```

## Cấu hình

Các thông số cấu hình có thể được chỉnh sửa trong tệp `config.py`:

### API Keys
- `OPENAI_API_KEY`: API key cho OpenAI (bắt buộc nếu sử dụng GPT-4o)
- `ANTHROPIC_API_KEY`: API key cho Anthropic (tùy chọn, nếu sử dụng Claude)
- `GOOGLE_API_KEY`: API key cho Google (tùy chọn, nếu sử dụng Gemini)

### LangSmith Tracing
- `LANGCHAIN_TRACING_V2`: Bật/tắt tracing với LangSmith
- `LANGCHAIN_API_KEY`: API key cho LangSmith (tùy chọn)
- `LANGCHAIN_PROJECT`: Tên dự án trong LangSmith

### vLLM Endpoints
- `VLLM_QWEN_URL`: URL cho dịch vụ vLLM Qwen 2.5 (mặc định: http://localhost:8000)
- `VLLM_LLAMA3_URL`: URL cho dịch vụ vLLM Llama 3.1 (mặc định: http://localhost:8001)
- `VLLM_MISTRAL_URL`: URL cho dịch vụ vLLM Mistral Large 2 (mặc định: http://localhost:8002)
- `VLLM_DEEPSEEK_URL`: URL cho dịch vụ vLLM DeepSeek V3 (mặc định: http://localhost:8003)

### Model Selection
- `JUDGE_MODEL`: Model cho Judge Agent (mặc định: gpt-4o)
- `JUDGE_ALTERNATIVE`: Model thay thế cho Judge (mặc định: claude-3-5-sonnet)
- `EXECUTOR_MODEL`: Model cho Executor Agent (mặc định: gpt-4o-mini)

### Logging & Optimization
- `LOG_LEVEL`: Mức độ logging (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_CACHING`: Bật/tắt caching (mặc định: true)
- `ENABLE_STREAMING`: Bật/tắt streaming (mặc định: true)
- `MAX_RETRIES`: Số lần retry tối đa (mặc định: 3)
- `RETRY_DELAY`: Thời gian chờ giữa các retries (mặc định: 1.0 giây)

## Tùy chỉnh

- Để thay đổi các mô hình LLM được sử dụng, chỉnh sửa trong `agents/proposers.py` và `agents/judge.py`
- Để điều chỉnh cấu hình Docker, chỉnh sửa `infrastructure/docker-compose.yml`
- Để thay đổi quy tắc cho Cursor IDE, chỉnh sửa các tệp trong `.cursor/rules/`

## Đóng góp

Vui lòng tạo issue hoặc pull request để đóng góp cho dự án.