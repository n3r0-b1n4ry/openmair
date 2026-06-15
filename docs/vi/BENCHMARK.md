# Hướng dẫn Đo kiểm và Chấm điểm AIOps

Tài liệu này giải thích cách hệ thống đa tác nhân đánh giá và chấm điểm các báo cáo phân tích sự cố được tạo ra bởi các Proposer LLM khác nhau.

## 1. Quy trình Đánh giá (Evaluation Workflow)

Quá trình đánh giá được điều phối hoàn toàn bởi **Tác nhân Judge (Trọng tài)**. Khi một sự cố được xử lý và các mô hình Proposer tạo ra báo cáo phân tích nguyên nhân gốc rễ (RCA) và khuyến nghị giải pháp của họ, Judge sẽ tiếp nhận toàn bộ các đề xuất này để tiến hành chấm điểm:

1. **Ẩn danh & Xáo trộn**: Danh tính của các Proposer LLM được ẩn danh hóa (ví dụ: "Assistant A", "Assistant B") và các báo cáo được xáo trộn ngẫu nhiên để loại bỏ định kiến về thương hiệu hoặc vị trí hiển thị trong lúc chấm điểm.
2. **Đánh giá suy luận Chain-of-Thought**: Tác nhân Judge tự mình phân tích log sự cố trước, sau đó tiến hành phân tích và phản biện từng báo cáo đề xuất một cách khách quan.
3. **Chấm điểm**: Tác nhân Judge chấm điểm từ **0.0 đến 10.0** cho từng báo cáo dựa trên một tập hợp các tiêu chí chấm điểm nghiêm ngặt.
4. **Tổng hợp**: Judge chọn ra các phần phân tích và giải pháp xuất sắc nhất từ các đề xuất có điểm số cao để tổng hợp thành một báo cáo sự cố `IncidentReport` tối ưu nhất.

## 2. Các Tiêu chí Chấm điểm Cốt lõi (Oracle Judge)

Khi hoạt động ở chế độ tiêu chuẩn, Judge chấm điểm dựa trên các tiêu chí sau:

* **Độ chính xác của Phân tích nguyên nhân gốc rễ (RCA)**: Proposer xác định nguyên nhân cốt lõi từ log thô chính xác đến mức nào? Nguyên nhân đưa ra có khớp với bằng chứng log không?
* **Tính khả thi và Hiệu quả của Giải pháp**: Các bước xử lý khắc phục có hợp lý về mặt kỹ thuật không? Giải pháp đó có thực sự giải quyết được triệt để vấn đề không?
* **Độ chi tiết và Tính toàn diện**: Báo cáo có cấu trúc rõ ràng, dễ đọc, chi tiết nhưng súc tích, không bị dài dòng lan man không?
* **Sự phù hợp của Điểm tin cậy (Confidence Score)**: Điểm tin cậy do Proposer tự đánh giá có tương xứng với chất lượng thực tế của bài phân tích không?
* **Khả năng triển khai tức thời**: Các bước khắc phục nhanh có thể được áp dụng an toàn ngay lập tức bởi Executor để giảm thiểu thiệt hại hay không?

## 3. Các Thư viện Đánh giá Nâng cao

Hệ thống được tích hợp sẵn với các thư viện đánh giá LLM tiêu chuẩn trong ngành. Nếu được kích hoạt (`use_frameworks=True`), Judge sẽ tính toán thêm các chỉ số điểm số nâng cao:

### Điểm số từ DeepEval
* **Answer Relevancy**: Đo lường xem giải pháp đề xuất có giải quyết trực tiếp nguyên nhân gốc rễ được tìm thấy không.
* **Faithfulness**: Đảm bảo báo cáo không bị ảo giác (hallucination) và bám sát thông tin log thô được cung cấp.
* **Contextual Precision**: Đánh giá mức độ chính xác của Proposer khi trích xuất các dòng log quan trọng để đưa ra kết luận.

### Điểm số từ RAGAS
* **Faithfulness**: Xác thực tính nhất quán về mặt sự thật của giải pháp so với ngữ cảnh log sự cố.
* **Answer Relevancy**: Đánh giá mức độ liên quan của giải pháp đối với sự cố cần giải quyết.
* **Context Precision**: Đảm bảo tất cả thông tin quan trọng được ưu tiên xếp ở vị trí hàng đầu trong ngữ cảnh phân tích.

### Prometheus-Eval
Sử dụng tiêu chí chấm điểm chi tiết chuyên dụng:
1. Độ chính xác của nguyên nhân gốc rễ (0-30 điểm)
2. Tính khả thi của giải pháp (0-30 điểm)
3. Độ chi tiết và tính toàn diện (0-20 điểm)
4. Độ tương xứng của điểm tin cậy tự đánh giá (0-20 điểm)

---

## 4. Trực quan hóa Điểm số trên Dashboard

Khi các kịch bản chạy thử nghiệm, hệ thống sẽ sử dụng luồng chạy ngầm `ElasticsearchLogHandler` để đẩy log trực tiếp theo thời gian thực về index `aiops-logs-reports`. Đồng thời, điểm chấm của Judge (thang điểm từ 0 đến 10) sẽ được đính kèm vào metadata dưới dạng trường `"judge_score"` cho từng báo cáo của Proposer.

Điều này cho phép giám sát trực quan thông qua các Dashboard của Kibana và Grafana bao gồm các bảng panel:
* **Action History (Executor)**: Theo dõi trạng thái và kết quả đầu ra của các lệnh khắc phục sự cố do Executor thực hiện theo thời gian thực.
* **Average Proposer Scores**: Biểu đồ thanh ngang thể hiện điểm số trung bình của từng mô hình Proposer ứng viên để đánh giá khách quan năng lực của từng mô hình.

Bạn cũng có thể chạy lệnh `python visualize_benchmark.py` để tự động vẽ biểu đồ hiệu năng tĩnh của các proposers qua các kịch bản sự cố khác nhau.
