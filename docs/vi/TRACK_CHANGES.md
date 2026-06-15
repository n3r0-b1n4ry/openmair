# Nhật ký Theo dõi Thay đổi — Multi-Agent AIOps MoA

---

## [2026-06-14] Tích hợp Executor Agent, Log Real-time và Nâng cấp Dashboard
- **Executor Agent**: Xây dựng thành phần `ExecutorAgent` để dịch các khuyến nghị hành động của Judge thành các lệnh có cấu trúc thực tế, tích hợp cơ chế phê duyệt thủ công qua CLI (Human-in-the-Loop) trước khi chạy lệnh.
- **Log Real-time lên Elasticsearch**: Thêm handler `ElasticsearchLogHandler` chạy bất đồng bộ dựa trên queue để truyền phát trực tiếp log suy luận của agent và log thực thi của executor lên Elasticsearch.
- **Tích hợp Điểm chấm của Judge**: Ghi nhận và đồng bộ điểm chấm đánh giá sự cố của Judge thành trường `"judge_score"` trong metadata của các báo cáo đề xuất lưu trên Elasticsearch.
- **Nâng cấp Dashboard**: Bổ sung bảng panel **Action History** xem log thực thi của Executor và panel **Average Proposer Scores** dạng bar gauge hiển thị điểm trung bình của các Proposers trên cả Grafana và Kibana.
- **Nâng cấp Mô hình**: Thay đổi `"SaoLa4-small"` thành `"DeepSeek-V4-Flash"` đối với Proposer, cài đặt mặc định mô hình Judge là `"gpt-5.4"`, và mặc định Executor là `"gpt-5.4-nano"`.

---

## [2026-05-15] Cập nhật Tài liệu cho các Mô hình mới & Hạ tầng
- Đồng bộ hóa toàn bộ tài liệu hướng dẫn khớp với các biến cấu hình mô hình trong `config.py` (Qwen 3.6 27B, GPT OSS 20B, SaoLa4-medium, Gemma 4 26B A4B IT, Qwen3-32B, GPT-5.5, GPT-5.4-mini).
- Cập nhật tài liệu kỹ thuật về log ingestion của Elasticsearch trong benchmark.

---

## [2026-03-19] Rà soát Kho Mã nguồn & Sửa lỗi

### 🔴 Các lỗi Nghiêm trọng đã sửa (5)

| # | Tệp ảnh hưởng | Mô tả chi tiết |
|---|--------------|----------------|
| 1 | `agents/proposers.py` | Chuyển đổi import `ChatOllama` từ `langchain_community` (đã bị deprecated) → sang gói mới `langchain_ollama` |
| 2 | `agents/model_router.py` | Sửa lỗi gán thuộc tính động `balanced_score` trên lớp `@dataclass` → chuyển sang dùng hàm helper bên ngoài |
| 3 | `orchestrator/state.py` | Sửa `AIOpsState` sử dụng cú pháp chuẩn `Annotated[list, operator.add]` của LangGraph thay vì khai báo trường Pydantic `Field()` trực tiếp trong TypedDict |
| 4 | `infrastructure/vector_db.py` | Gỡ bỏ `AnthropicEmbeddings` (vì Anthropic không cung cấp API Embedding độc lập) |
| 5 | `infrastructure/vector_db.py` | Cập nhật kết nối `PineconeVectorDB` từ SDK v1 (`pinecone.init()`) → sang SDK v3+ mới nhất (`Pinecone()`) |

### 🟡 Các lỗi Ưu tiên cao đã sửa (4)

| # | Tệp ảnh hưởng | Mô tả chi tiết |
|---|--------------|----------------|
| 6 | `main.py` | Đơn giản hóa trạng thái `initial_state` khởi tạo ban đầu, loại bỏ các khóa dư thừa (LangGraph tự động khởi tạo từ reducer) |
| 7 | `AGENTS.md` | Đồng bộ danh sách mô hình thực tế trong code (Llama 3.3, QwQ-32B, DeepSeek R1 Distill) |
| 8 | `requirements-core.txt` | Loại bỏ gói lỗi `deepseek-openai` (không có trên PyPI); cài bổ sung `langchain-ollama`, `langchain-community` |
| 9 | `prompts/` | Khởi tạo gói `prompts/templates.py` chứa các template prompt được tách lọc ra từ `proposers.py` và `judge.py` để dễ bảo trì |

---

## [2026-03] Bản phát hành 2026 — Ghi chú Tái cấu trúc

### Các Thay đổi Chính

1. **Nâng cấp danh sách Mô hình LLM (2026):**
   * **Proposers**: Thay thế Llama 3.1 70B → Llama 3.3 70B (nhẹ hơn, điểm đánh giá tương đương bản 400B)
   * **Proposers**: Thay thế Mistral Large 2 → QwQ-32B (tối ưu hóa suy luận chuỗi tư duy CoT)
   * **Proposers**: Bổ sung DeepSeek R1 Distill Llama 70B (mô hình suy luận cực kỳ mạnh mẽ)
   * **Judge**: Oracle mặc định → Claude 3.7 Sonnet (suy luận kết hợp tốt nhất hiện tại)
   * **Judge**: Dự phòng → OpenAI o3-mini (suy luận logic kỹ thuật phức tạp với tham số `reasoning_effort`)

2. **Cải tiến Đồ thị LangGraph:**
   * Tối ưu hóa điều hướng định tuyến tại `orchestrator/router.py` hỗ trợ cơ chế suy giảm có điều kiện (graceful degradation).
   * Thêm hàm định tuyến `route_after_evaluation` để kiểm tra kết quả trước khi đưa sang Executor.
   * Toàn bộ các node đều kiểm tra kỹ lưỡng đầu vào để tránh crash đồ thị.

3. **Cơ cấu lại thư viện phụ thuộc:**
   * Tách `requirements.txt` thành 2 tệp riêng biệt:
     * `requirements-core.txt`: Các thư viện tối thiểu để khởi chạy hệ thống.
     * `requirements-eval.txt`: Các thư viện đánh giá chuyên sâu (chỉ sử dụng cho môi trường kiểm thử offline).

4. **Docker Compose Rút gọn (Light):**
   * Bổ sung tệp `infrastructure/docker-compose.light.yml` phục vụ chạy thử nghiệm trên máy cá nhân/phòng lab chỉ có 1 GPU.
   * Chỉ chạy duy nhất 1 container vLLM + Redis để tiết kiệm dung lượng RAM/VRAM.
