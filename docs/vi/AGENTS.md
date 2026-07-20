# Tổng quan Dự án: Hệ thống AIOps Sử dụng Mixture-of-Agents (MoA)

## 1. Tầm nhìn Hệ thống

Dự án này xây dựng một hệ thống Tự động phản hồi Sự cố (AIOps). Hệ thống thu nhận log và cảnh báo thời gian thực từ hạ tầng Microservices, sử dụng hội đồng Đa tác nhân (Multi-Agent) để phân tích nguyên nhân gốc rễ (RCA), và sau đó áp dụng cơ chế LLM-as-a-Judge để đưa ra quyết định cuối cùng.

## 2. Kiến trúc Tác nhân (Agent Architecture)

* **Candidate Proposers**: 5 phiên bản mô hình tini-cybersec-8b-a1b chạy trên máy chủ LM Studio cục bộ (tương thích OpenAI). Các tác nhân này hoạt động song song với các siêu tham số khác nhau (temperature, top_k, top_p, repeat_penalty) để phân tích log và tạo ra nhiều báo cáo RCA độc lập.
* **Oracle Aggregator**: Một mô hình cao cấp (DeepSeek-V4-Flash, gpt-5.4, gpt-5.4-mini, hoặc Gemini 3.1 Pro). Nhiệm vụ của nó không phải là phân tích từ đầu mà là đánh giá và tổng hợp các báo cáo của Proposer để tạo ra kế hoạch khắc phục sự cố tối ưu nhất.
* **Executor Agent**: Chuyển đổi các hành động khắc phục do Judge đề xuất thành các tác vụ lệnh có cấu trúc cụ thể, áp dụng cổng phê duyệt thủ công qua CLI (Human-in-the-Loop) và thực thi chúng.
* **Orchestrator**: Toàn bộ quy trình làm việc được quản lý bởi LangGraph, duy trì một trạng thái State chung chia sẻ giữa toàn bộ tác nhân.

## 3. Cấu trúc Mã nguồn

* `/agents`: Định nghĩa luồng xử lý cho Candidate LLMs, Oracle LLM, và Executor Agent.
* `/orchestrator`: Cấu trúc đồ thị LangGraph, Router điều hướng và định nghĩa States.
* `/prompts`: Tập hợp các mẫu template prompt chuyên biệt được thiết kế để chống định kiến.
* `/infrastructure`: Cấu hình Docker Compose để triển khai vLLM, ELK Stack, và API Gateway.
* `/evals`: Bộ công cụ để chạy các bài test ngoại tuyến và tính điểm hệ thống.

## 4. Các mô hình LLM được sử dụng

### Mô hình Proposer (Candidate LLMs)
1. **tini-cybersec-8b-a1b (5 phiên bản với cấu hình tham số khác nhau)**

### Mô hình Judge (Oracle LLM)
1. **DeepSeek-V4-Flash** - Oracle Judge Mặc định
2. **gpt-5.4** - Judge Thay thế
3. **gpt-5.4-mini** - Judge Dự phòng
4. **Gemini 3.1 Pro** - Judge Thay thế

### Mô hình Executor
1. **DeepSeek-V4-Flash** - Executor Mặc định
2. **gpt-5.4-nano** - Executor Thay thế

Xem thêm `MODELS.md` để biết thêm chi tiết.

## 5. Quy tắc Lập trình Cốt lõi

* Mọi tương tác LLM phải sử dụng cú pháp LCEL của LangChain.
* Mọi thông báo lỗi phải được ghi lại bằng thư viện `logging` tiêu chuẩn. Không bao giờ sử dụng `print()`.
* Tuân thủ nghiêm ngặt nguyên tắc đặc quyền tối thiểu: Tất cả mã do AI tạo ra có ảnh hưởng đến hệ thống phải đi qua cơ chế phê duyệt thủ công (Human-in-the-Loop).
