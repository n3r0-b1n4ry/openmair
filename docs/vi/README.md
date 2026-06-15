# Hệ thống AIOps Đa Tác Nhân với Cơ chế LLM-As-A-Judge

Giải pháp AIOps (AI cho IT Operations) tiên tiến sử dụng kiến trúc **Mixture-of-Agents (MoA)** kết hợp với cơ chế **LLM-as-a-Judge** để tự động hóa quá trình phát hiện, phân tích nguyên nhân gốc rễ (RCA) và khắc phục sự cố trong hạ tầng IT hiện đại.

## Bắt đầu nhanh

```bash
# Cài đặt các thư viện cốt lõi
pip install -r requirements-core.txt

# Cấu hình biến môi trường
cp infrastructure/env.example .env
# Chỉnh sửa file .env với API key của bạn

# Chạy hệ thống
python main.py
```

## Kiến trúc hệ thống

Hệ thống sử dụng ba loại tác nhân (agent):

| Tác nhân | Vai trò | Mô hình |
|----------|---------|---------|
| **Proposers** | Phân tích log sự cố, đề xuất báo cáo phân tích nguyên nhân gốc rễ (RCA) | Qwen 3.6 27B, GPT OSS 20B, DeepSeek-V4-Flash, Gemma 4 26B A4B IT, Qwen3-32B |
| **Judge** | Đánh giá và tổng hợp các đề xuất | gpt-5.4, gpt-5.4-mini, Gemini 3.1 Pro |
| **Executor** | Thực hiện hành động khắc phục sự cố | gpt-5.4-nano |

Tất cả các proposers chạy song song thông qua **vLLM**, được điều phối bởi **LangGraph**.

## Tài liệu hướng dẫn

| Tài liệu | Mô tả |
|----------|-------|
| [README](README.md) | Hướng dẫn cài đặt, cấu hình và sử dụng đầy đủ |
| [AGENTS](AGENTS.md) | Kiến trúc agent và tổng quan hệ thống |
| [MODELS](MODELS.md) | Các mô hình LLM, so sánh hiệu năng và khuyến nghị |
| [ARCHITECTURE](ARCHITECTURE.md) | Sơ đồ luồng hệ thống (Mermaid) |
| [TRACK_CHANGES](TRACK_CHANGES.md) | Nhật ký thay đổi và hướng dẫn cập nhật |

## Cấu trúc thư mục dự án

```
.
├── agents/                 # Định nghĩa các Agent (Proposers, Judge, Executor)
├── orchestrator/           # Luồng công việc LangGraph (State, Router, Graph)
├── prompts/                # Các mẫu Prompt mẫu chuyên biệt
├── infrastructure/         # Cấu hình Docker Compose, Nginx, Prometheus/Grafana
├── evals/                  # Bộ công cụ đánh giá (Evaluation toolkit)
├── docs/                   # Tài liệu hướng dẫn (tiếng Anh và tiếng Việt)
├── config.py               # Cấu hình hệ thống toàn cục
├── main.py                 # Điểm khởi chạy chính của ứng dụng
└── requirements-core.txt   # Các thư viện phụ thuộc cốt lõi
```

## Đóng góp và Phát triển

Vui lòng tạo issue hoặc pull request để đóng góp vào dự án này.
