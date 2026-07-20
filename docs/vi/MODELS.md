# Các Mô hình LLM Tối ưu và Mới nhất (2026)

## Tổng quan

Hệ thống AIOps đa tác nhân sử dụng kiến trúc Mixture-of-Agents (MoA) kết hợp với cơ chế LLM-as-a-Judge để tối ưu hóa hiệu năng phân tích sự cố. Dưới đây là danh sách các mô hình LLM được tích hợp trong hệ thống, đồng bộ với cấu hình trong `config.py`.

## Mô hình Proposer (Mô hình Đề xuất)

Tất cả 5 proposers đều sử dụng mô hình **tini-cybersec-8b-a1b** chạy trên máy chủ LLM cục bộ (LM Studio), được cấu hình với các tham số khác nhau (temperature, top_k, top_p, và repeat_penalty) nhằm tạo ra các đề xuất đa dạng:

### 1. tini-cybersec-8b-a1b (Proposer 1)
- **Tham số**: Temperature=0.2, Top K=40, Top P=0.85, Repeat Penalty=1.1
- **Vai trò**: Phân tích sự cố và bảo mật có tính xác thực cao.

### 2. tini-cybersec-8b-a1b (Proposer 2)
- **Tham số**: Temperature=0.3, Top K=42, Top P=0.90, Repeat Penalty=1.12
- **Vai trò**: Phân tích sự cố tiêu chuẩn và cân bằng.

### 3. tini-cybersec-8b-a1b (Proposer 3)
- **Tham số**: Temperature=0.4, Top K=45, Top P=0.92, Repeat Penalty=1.15
- **Vai trò**: Phân tích nguyên nhân gốc rễ (RCA) sáng tạo có định hướng.

### 4. tini-cybersec-8b-a1b (Proposer 4)
- **Tham số**: Temperature=0.5, Top K=48, Top P=0.95, Repeat Penalty=1.18
- **Vai trò**: Đề xuất các phương án khắc phục thay thế đa dạng.

### 5. tini-cybersec-8b-a1b (Proposer 5)
- **Tham số**: Temperature=0.6, Top K=50, Top P=0.98, Repeat Penalty=1.20
- **Vai trò**: Cấu hình khám phá tối đa cho các trường hợp đặc biệt.

## Mô hình Judge (Mô hình Đánh giá/Trọng tài)

### 1. DeepSeek-V4-Flash (Mặc định)
- **Nhà phát triển**: DeepSeek
- **Thế mạnh**: Tốc độ suy luận siêu tốc, tối ưu hóa cho các tác vụ phân tích văn bản nhanh và hiệu quả, phù hợp để đánh giá.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

### 2. gpt-5.4 (Thay thế)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Mô hình suy luận và đánh giá cao cấp nhất.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

### 3. gpt-5.4-mini (Dự phòng)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Tốc độ nhanh hơn, hiệu năng suy luận tốt cho vai trò dự phòng.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

### 4. Gemini 3.1 Pro (Thay thế)
- **Nhà phát triển**: Google
- **Thế mạnh**: Cửa sổ ngữ cảnh cực lớn, khả năng suy luận đa phương thức mạnh mẽ.
- **Cấu hình**: Temperature=0.0, Max Tokens=8192

## Mô hình Executor (Mô hình Thực thi)

### 1. DeepSeek-V4-Flash (Mặc định)
- **Nhà phát triển**: DeepSeek
- **Thế mạnh**: Siêu nhẹ, độ trễ thấp, tối ưu cho việc phân tích và thực thi.
- **Ứng dụng trong hệ thống**: Chuyển đổi các bước khắc phục của Judge thành tác vụ thực thi cụ thể.
- **Cấu hình**: Temperature=0.3, Max Tokens=2048

### 2. gpt-5.4-nano (Thay thế)
- **Nhà phát triển**: OpenAI
- **Thế mạnh**: Siêu nhẹ, độ trễ thấp, tối ưu cho việc phân tích và chuyển đổi các đề xuất hành động dạng văn bản thành lệnh có cấu trúc.
- **Ứng dụng trong hệ thống**: Chuyển đổi các bước khắc phục của Judge thành tác vụ thực thi cụ thể.
- **Cấu hình**: Temperature=0.3, Max Tokens=2048
