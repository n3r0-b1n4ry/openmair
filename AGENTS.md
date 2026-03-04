# Tổng Quan Dự Án: Hệ Thống AIOps Ứng Dụng Mixture-of-Agents (MoA)

## 1. Định Hướng Hệ Thống

Dự án này xây dựng một hệ thống Tự động hóa Phản ứng Sự cố (AIOps). Hệ thống thực hiện việc tiếp nhận log và cảnh báo thời gian thực từ hạ tầng Microservices, sử dụng cấu trúc hội đồng Đa tác nhân (Multi-Agent) để phân tích nguyên nhân gốc rễ (Root Cause Analysis), sau đó dùng cơ chế LLM-as-a-Judge để ra quyết định cuối cùng.

## 2. Kiến Trúc Tác Nhân (Agent Architecture)

* **Tác nhân Đề xuất (Candidate Proposers):** Là các LLM mã nguồn mở mới nhất (Qwen 2.5 72B, Llama 3.1 70B, Mistral Large 2, DeepSeek V3) triển khai cục bộ qua vLLM. Các tác nhân này hoạt động song song để phân tích log và sinh ra nhiều báo cáo RCA độc lập.
* **Tác nhân Giám khảo (Oracle Aggregator):** Là mô hình cao cấp (GPT-4o, Claude 3.5 Sonnet, hoặc Gemini 2.5 Pro). Nhiệm vụ của nó không phải là tự phân tích từ đầu, mà là tổng hợp, so sánh và đánh giá các báo cáo của Proposers, từ đó loại bỏ các đề xuất sai lệch (hallucination) và xuất ra hành động khôi phục tối ưu.
* **Điều phối viên (Orchestrator):** Toàn bộ quy trình được quản lý bởi LangGraph, duy trì một trạng thái toàn cục (State) dùng chung cho tất cả các tác nhân thao tác.

## 3. Cấu Trúc Mã Nguồn (Monorepo)

* `/agents`: Định nghĩa luồng làm việc của các Candidate LLM và Oracle LLM.
* `/orchestrator`: Cấu trúc Graph, Router và các State của LangGraph.
* `/prompts`: Tập hợp các mẫu câu lệnh (Prompt templates) chuyên dụng để chống bias.
* `/infrastructure`: Cấu hình Docker Compose để triển khai vLLM, ELK Stack và API Gateway.
* `/evals`: Bộ công cụ để chạy kiểm thử offline và chấm điểm hệ thống.

## 4. Các Model LLM Được Sử Dụng

### Proposer Models (Candidate LLMs)
1. **Qwen 2.5 72B** - Model mã nguồn mở mạnh mẽ nhất hiện nay
2. **Llama 3.1 70B** - Model mã nguồn mở phổ biến nhất
3. **Mistral Large 2** - Model mã nguồn mở hiệu quả cao
4. **DeepSeek V3** - Model mã nguồn mở mới nhất

### Judge Model (Oracle LLM)
1. **GPT-4o** - Model mạnh mẽ nhất từ OpenAI
2. **Claude 3.5 Sonnet** - Model tốt nhất cho reasoning
3. **Gemini 2.5 Pro** - Model mới nhất từ Google

Xem thêm chi tiết trong tệp `MODELS.md`.

## 5. Nguyên Tắc Lập Trình (Core Rules)

* Mọi tương tác LLM phải sử dụng cú pháp LCEL của thư viện LangChain.
* Mọi thông báo lỗi cần được log lại bằng thư viện `logging` tiêu chuẩn. Không bao giờ sử dụng `print()`.
* Tuyệt đối tuân thủ đặc quyền tối thiểu: Mọi mã lệnh tác động đến hệ thống do AI tạo ra đều phải trải qua cơ chế phê duyệt Human-in-the-Loop.