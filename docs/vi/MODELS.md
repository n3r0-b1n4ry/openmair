# Các Mô hình LLM Tối ưu và Mới nhất (2026)

## Tổng quan

Hệ thống AIOps đa tác nhân sử dụng kiến trúc Mixture-of-Agents (MoA) kết hợp với cơ chế LLM-as-a-Judge để tối ưu hóa hiệu năng phân tích sự cố. Dưới đây là danh sách các mô hình LLM được tích hợp trong hệ thống, đồng bộ với cấu hình trong `config.py`.

## Mô hình Proposer (Mô hình Đề xuất)

### 1. Qwen 3.6 27B
- **Nhà phát triển**: Alibaba Cloud
- **Kích thước**: 27 tỷ tham số
- **Thế mạnh**: Khả năng suy luận vượt trội, tối ưu hóa riêng cho phân tích log kỹ thuật phức tạp.
- **Ứng dụng trong hệ thống**: Phân tích log sự cố, đưa ra khuyến nghị giải pháp.

### 2. GPT OSS 20B
- **Kích thước**: 20 tỷ tham số
- **Thế mạnh**: Tốc độ phản hồi cực nhanh, benchmark ổn định với log và dữ liệu traces.
- **Ứng dụng trong hệ thống**: Trích xuất dữ liệu log và suy luận nhanh.

### 3. DeepSeek-V4-Flash
- **Kích thước**: Mô hình Flash nhẹ tối ưu
- **Thế mạnh**: Tốc độ suy luận siêu tốc, tối ưu hóa cho các tác vụ phân tích văn bản nhanh và hiệu quả.
- **Ứng dụng trong hệ thống**: Phân tích log sự cố tức thời.

### 4. Gemma 4 26B A4B IT
- **Nhà phát triển**: Google
- **Kích thước**: 26 tỷ tham số
- **Thế mạnh**: Tối ưu hóa chỉ thị mạnh mẽ, trích xuất thông tin log chính xác.
- **Ứng dụng trong hệ thống**: Phân tích log hạ tầng phức tạp.

### 5. Qwen3-32B
- **Nhà phát triển**: Alibaba Cloud
- **Kích thước**: 32 tỷ tham số
- **Thế mạnh**: Kích thước lớn, có khả năng phân tích chi tiết sâu về mặt kỹ thuật.
- **Ứng dụng trong hệ thống**: Đưa ra phân tích nguyên nhân gốc rễ (RCA) chi tiết và giải pháp khắc phục.

## Mô hình Judge (Mô hình Đánh giá/Trọng tài)

### 1. gpt-5.4 (Mặc định)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Mô hình suy luận và đánh giá cao cấp nhất. Đóng vai trò làm Judge mặc định.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

### 2. gpt-5.4-mini (Dự phòng)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Tốc độ nhanh hơn, hiệu năng suy luận tốt cho vai trò dự phòng.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

### 3. Gemini 3.1 Pro (Thay thế)
- **Nhà phát triển**: Google
- **Thế mạnh**: Cửa sổ ngữ cảnh cực lớn, khả năng suy luận đa phương thức mạnh mẽ.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

## Mô hình Executor (Mô hình Thực thi)

### gpt-5.4-nano (Mặc định)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Siêu nhẹ, độ trễ thấp, tối ưu cho việc phân tích và chuyển đổi các đề xuất hành động dạng văn bản thành lệnh có cấu trúc.
- **Ứng dụng trong hệ thống**: Chuyển đổi các bước khắc phục của Judge thành tác vụ thực thi cụ thể.
- **Cấu hình**: Temperature=0.3, Max Tokens=2048
