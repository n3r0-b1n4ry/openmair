# Kế Hoạch Thực Hiện Và Tài Liệu Hướng Dẫn Cursor: Xây Dựng Hệ Thống AIOps Đa Tác Nhân Kết Hợp Cơ Chế LLM-As-A-Judge

## 1. Bối Cảnh Hệ Thống Và Thách Thức Trong Quản Lý Sự Cố Hiện Đại

Trong kỷ nguyên chuyển đổi số, hạ tầng công nghệ thông tin của các doanh nghiệp đang trải qua một sự thay đổi mô hình mang tính bước ngoặt, chuyển dịch từ các hệ thống nguyên khối (monolithic) sang các kiến trúc phân tán như Microservices, Cloud Native và Hybrid Cloud. Mặc dù sự chuyển dịch này mang lại khả năng mở rộng linh hoạt và tốc độ triển khai vượt trội, nó đồng thời tạo ra một môi trường vận hành với độ phức tạp khổng lồ. Hệ quả tất yếu của sự phức tạp này là sự bùng nổ của dữ liệu viễn trắc (telemetry data), trong đó khối lượng nhật ký hệ thống (logs), cảnh báo (alerts) và số liệu giám sát (metrics) tăng lên theo cấp số nhân.

Quy trình quản lý sự cố phần mềm thông thường được chia thành bốn giai đoạn riêng biệt nhưng có tính liên kết chặt chẽ. Giai đoạn đầu tiên là Phát hiện Bất thường (Anomaly Detection), nơi các hệ thống giám sát tạo ra cảnh báo khi nhận thấy hành vi hệ thống lệch khỏi đường cơ sở chuẩn. Tiếp theo là Phân loại Lỗi (Failure Triage), nhằm phân loại sự cố dựa trên đặc tính và chuyển tiếp đến đội ngũ chuyên trách. Giai đoạn thứ ba, và cũng là giai đoạn đòi hỏi nhiều chất xám nhất, là Phân tích Nguyên nhân Gốc rễ (Root Cause Localization), đòi hỏi các kỹ sư phải phân tích toàn diện mọi khía cạnh của sự cố. Cuối cùng là Giảm thiểu Sự cố (Incident Mitigation), nơi các kỹ sư thực hiện các biện pháp khôi phục chức năng hệ thống.

Trong số các giai đoạn này, ba giai đoạn đầu tiên mang tính lặp lại, phụ thuộc nhiều vào dữ liệu và hoàn toàn có thể tự động hóa, biến chúng thành mục tiêu hàng đầu cho các giải pháp Trí tuệ Nhân tạo ứng dụng trong Vận hành (AIOps). Khi đối mặt với hàng nghìn microservices giao tiếp liên tục, các phương pháp giám sát truyền thống dựa trên quy tắc (rule-based) hoặc tìm kiếm từ khóa tỏ ra kém hiệu quả và dễ dàng bị quá tải. Điều này dẫn đến hiện tượng "mệt mỏi cảnh báo" (alert fatigue), nơi các đội ngũ công nghệ thông tin phải đối mặt với một lượng lớn thông báo, nhiều trong số đó là dư thừa hoặc ít ưu tiên, làm tăng nguy cơ bỏ lỡ các sự cố nghiêm trọng. Đồng thời, các quy trình quản lý sự cố bị phân mảnh khiến việc tương quan các cảnh báo và theo dõi sự cố trên nhiều nền tảng trở nên vô cùng khó khăn, kéo dài thời gian khôi phục dịch vụ (MTTR - Mean Time To Recovery) và gây thiệt hại lớn về kinh tế.

Sự ra đời của các Mô hình Ngôn ngữ Lớn (LLM) đã mở ra một hướng đi mang tính cách mạng nhằm chuyển đổi quy trình quản lý sự cố từ trạng thái phản ứng thụ động sang trạng thái tự trị (autonomous). Khả năng hiểu ngôn ngữ tự nhiên, phân tích mã nguồn và suy luận logic của các LLM như GPT-4, Qwen hay Claude mang lại tiềm năng to lớn trong việc tự động hóa toàn bộ quy trình từ phân tích log, truy vết lỗi đến đề xuất giải pháp. Quá trình này hình thành một "Vòng lặp Tự trị" (Autonomous Loop), trong đó khi một dịch vụ giám sát phát hiện lỗi, một công cụ truy vấn tự động sẽ trích xuất log thời gian thực và gửi cho LLM. LLM sau đó đối chiếu thông tin này với Cơ sở Tri thức (Knowledge Base) để tìm ra nguyên nhân và chỉ định các công cụ khác thực hiện cảnh báo hoặc chạy lệnh sửa lỗi. Tuy nhiên, việc ứng dụng đơn lẻ một mô hình LLM để phân tích hệ thống phức tạp thường gặp phải rủi ro liên quan đến "ảo giác" (hallucination) hoặc các phán đoán thiếu chính xác, đặc biệt nguy hiểm khi hệ thống được cấp quyền tự động thực thi các thay đổi hạ tầng. Để giải quyết triệt để bài toán này, kiến trúc hệ thống hiện đại bắt buộc phải tiến tới mô hình Đa tác nhân (Mixture-of-Agents) kết hợp cùng cơ chế Đánh giá chéo (LLM-as-a-Judge).[1, 1]

## 2. Nền Tảng Lý Thuyết Về Hệ Thống Đa Tác Nhân (Mixture-of-Agents)

Mặc dù các Mô hình Ngôn ngữ Lớn đã đạt được những bước tiến vĩ đại, chúng vẫn phải đối mặt với những giới hạn vật lý và kinh tế liên quan đến quy mô mô hình và dữ liệu huấn luyện. Việc tiếp tục mở rộng quy mô (scaling up) các mô hình này đòi hỏi chi phí khổng lồ và quá trình huấn luyện lại trên hàng nghìn tỷ token. Thay vì phụ thuộc vào một siêu mô hình duy nhất, phương pháp Mixture-of-Agents (MoA) tận dụng sức mạnh tập thể của nhiều LLM khác nhau, tận dụng thế mạnh chuyên biệt của từng mô hình.[1, 1] Một số mô hình tỏ ra xuất sắc trong việc tuân thủ các chỉ thị phức tạp, trong khi số khác lại vượt trội ở khả năng tạo mã nguồn hoặc phân tích cú pháp.

Động lực cốt lõi đằng sau kiến trúc MoA là hiện tượng "Tính cộng tác" (Collaborativeness) của các Mô hình Ngôn ngữ Lớn. Nghiên cứu chỉ ra rằng một LLM có xu hướng tạo ra các phản hồi chất lượng cao hơn đáng kể khi nó được cung cấp đầu ra từ các mô hình khác làm thông tin bổ trợ, ngay cả khi các mô hình bổ trợ đó có năng lực nội tại thấp hơn bản thân nó. Trong hệ sinh thái cộng tác này, các mô hình được chia thành hai vai trò chuyên biệt. Thứ nhất là các mô hình Đề xuất (Proposers), có nhiệm vụ tạo ra các phản hồi tham chiếu đa dạng và cung cấp nhiều góc nhìn khác nhau cho một vấn đề. Mặc dù một mô hình Proposer có thể không tạo ra câu trả lời hoàn hảo nhất, sự đa dạng trong bối cảnh mà nó cung cấp là nguyên liệu thô vô giá. Thứ hai là các mô hình Tổng hợp (Aggregators), sở hữu khả năng dung hợp các phản hồi từ nhiều mô hình khác thành một kết quả đầu ra duy nhất với chất lượng vượt trội, duy trì độ chính xác ngay cả khi phải xử lý các dữ liệu đầu vào có chất lượng không đồng đều.

Cấu trúc của MoA được lấy cảm hứng sâu sắc từ kỹ thuật Mixture-of-Experts (MoE) nổi tiếng trong học máy, nơi nhiều mạng nơ-ron chuyên gia tập trung vào các bộ kỹ năng khác nhau. Tuy nhiên, thay vì hoạt động ở cấp độ kích hoạt trọng số (activation level) bên trong một mô hình như MoE, MoA hoạt động ở cấp độ mô hình hoàn chỉnh thông qua giao diện gợi ý (prompting interface). Trong kiến trúc MoA, hệ thống được xếp thành nhiều lớp. Ở lớp đầu tiên, các tác nhân LLM độc lập (ví dụ: $A_{1,1}, A_{1,2},..., A_{1,n}$) nhận cùng một dữ liệu đầu vào (chẳng hạn như dữ liệu log sự cố) và sinh ra các phản hồi độc lập. Đầu ra của toàn bộ lớp này sau đó được ghép nối và chuyển đến các tác nhân ở lớp tiếp theo để tinh chỉnh. Về mặt toán học, nếu $x_1$ là câu lệnh đầu vào ban đầu, đầu ra của lớp MoA thứ $i$, ký hiệu là $y_i$, được biểu diễn dưới dạng $y_i = \oplus_{j=1}^n [A_{i,j}(x_i)] + x_1$, trong đó $\oplus$ đại diện cho phép nối văn bản và việc áp dụng câu lệnh tổng hợp. Tại lớp cuối cùng, một mô hình Aggregator mạnh nhất (được gọi là Oracle Judge) sẽ tổng hợp toàn bộ thông tin để ra quyết định.[1, 1]

Hiệu quả của kiến trúc này được thể hiện rõ qua biểu đồ hiệu suất so với chi phí. Phân tích ngân sách cho thấy các cấu hình MoA tạo ra một đường ranh giới tối ưu (Pareto frontier), cho phép lựa chọn các cấu hình mang lại chất lượng tương đương hoặc vượt trội so với các siêu mô hình đắt đỏ nhất (như GPT-4 Turbo hay GPT-4o) nhưng với chi phí vận hành chỉ bằng một nửa, đặc biệt khi hệ thống sử dụng các mô hình Proposer là mã nguồn mở triển khai cục bộ.

| Đặc điểm So sánh | Mô hình Đơn lẻ (Single LLM) | Hệ thống Đa tác nhân (MoA) |
| --- | --- | --- |
| **Cơ chế hoạt động** | Phụ thuộc hoàn toàn vào cơ sở tri thức và năng lực suy luận của một mô hình duy nhất.

 | Chia lớp xử lý, kết hợp nhiều mô hình song song (Proposers) và mô hình tổng hợp (Aggregators).

 |
| **Khả năng giảm ảo giác** | Thấp, dễ bị lệch hướng nếu bối cảnh sự cố phức tạp hoặc vượt quá dữ liệu huấn luyện.

 | Rất cao, nhờ sự đa dạng hóa (model diversity) và cơ chế bù trừ khi tổng hợp thông tin.

 |
| **Chi phí vận hành** | Cao nếu sử dụng mô hình độc quyền lớn cho toàn bộ lượng log khổng lồ.

 | Tối ưu hóa trên đường Pareto, kết hợp LLM nguồn mở chi phí thấp với một LLM nguồn đóng cao cấp.

 |
| **Ứng dụng trong AIOps** | Thường tạo ra điểm nghẽn hoặc phán đoán sai lầm khi cần tự động hóa sửa lỗi.

 | Lý tưởng cho việc truy vết lỗi, tận dụng tính cộng tác để tổng hợp nguyên nhân chính xác từ nhiều hệ thống.[1, 1] |

## 3. Cơ Chế Đánh Giá Chéo LLM-As-A-Judge Trong Hệ Thống AIOps

Khi triển khai hệ thống MoA, việc lựa chọn giải pháp cuối cùng từ vô số các đề xuất của Candidate LLMs đòi hỏi một cơ chế đánh giá mạnh mẽ và tự động. Các hệ thống đánh giá truyền thống dựa trên độ tương đồng văn bản như ROUGE hay BLEU hoàn toàn bất lực trước các câu trả lời mở (open-ended) và phức tạp như báo cáo phân tích nguyên nhân gốc rễ (RCA). Để vượt qua rào cản này, việc sử dụng các LLM sở hữu khả năng suy luận logic vượt trội đóng vai trò như một vị giám khảo (Oracle LLM) đã trở thành giải pháp ưu việt nhất, được gọi là LLM-as-a-Judge.[1, 1] Kỹ thuật này không chỉ mang lại khả năng mở rộng (scalability) bằng cách loại bỏ sự phụ thuộc vào con người trong khâu chấm điểm, mà còn cung cấp tính minh bạch (explainability) vì mô hình giám khảo có khả năng giải thích chi tiết lý do đằng sau điểm số của nó. Mức độ đồng thuận giữa một giám khảo LLM mạnh mẽ và chuyên gia con người trong các bài kiểm tra thực tế có thể vượt quá 80%, ngang bằng với mức độ đồng thuận giữa chính các chuyên gia con người với nhau.

Việc triển khai LLM-as-a-Judge bao gồm nhiều chiến lược khác nhau. Hệ thống có thể so sánh theo cặp (Pairwise comparison), nơi giám khảo đọc hai giải pháp và quyết định giải pháp nào tốt hơn, hoặc chấm điểm đơn lẻ (Single answer grading), nơi giám khảo trực tiếp gán một điểm số tuyệt đối cho một giải pháp dựa trên một thang điểm có sẵn. Trong môi trường LangChain và LangSmith, quá trình này được cấu hình thông qua tính năng Feedback Configuration, nơi hệ thống định nghĩa các tiêu chí đánh giá (như Correctness, Helpfulness, Safety) thành các cấu trúc đầu ra (structured output) bắt buộc mà LLM phải tuân thủ.

Tuy nhiên, việc sử dụng LLM làm giám khảo tiềm ẩn những độ lệch (biases) nội tại sâu sắc cần được xử lý thông qua kỹ thuật thiết kế câu lệnh (Prompt Engineering) và kiến trúc hệ thống tinh vi.

| Loại Độ Lệch (Bias) | Cơ Chế Phát Sinh | Tác Động Trong AIOps | Chiến Lược Giảm Thiểu (Mitigation) |
| --- | --- | --- | --- |
| **Độ lệch vị trí (Position Bias)** | LLM có thiên hướng ưu ái thông tin xuất hiện đầu tiên do bản chất của kiến trúc transformer xử lý từ trái sang phải.

 | Giám khảo luôn chọn đề xuất của Proposer A thay vì Proposer B dù B cung cấp giải pháp sửa lỗi chính xác hơn.

 | Tráo đổi vị trí ngẫu nhiên (swapping) các câu trả lời, đánh giá đơn lẻ (single grading), hoặc sử dụng Few-shot prompting.

 |
| **Độ lệch độ dài (Verbosity Bias)** | Mô hình đánh giá thường nhầm lẫn giữa độ dài văn bản và chất lượng thông tin, ưu tiên các câu trả lời dài dòng.

 | Hệ thống chọn các báo cáo lỗi dài dòng chứa thông tin rác thay vì một dòng lệnh bash ngắn gọn giải quyết triệt để vấn đề.

 | Đưa vào System Prompt chỉ thị rõ ràng cấm việc thiên vị độ dài, yêu cầu đánh giá trực tiếp vào tính hiệu quả của giải pháp.

 |
| **Độ lệch tự tôn (Self-Enhancement Bias)** | LLM có khuynh hướng thiên vị các câu trả lời do chính nó hoặc các phiên bản tương tự tạo ra.

 | Oracle Judge (ví dụ GPT-4) bỏ qua giải pháp tối ưu của Qwen để chọn giải pháp kém hơn do chính dòng họ GPT tạo ra.

 | Xóa bỏ mọi dấu vết định danh của mô hình (anonymization) trước khi đưa vào prompt đánh giá.

 |
| **Giới hạn Suy luận Kỹ thuật** | Giám khảo bị đánh lừa bởi dữ liệu đầu vào sai lệch từ Candidate LLMs dù bản thân nó có khả năng giải quyết.

 | Giám khảo phê duyệt một chuỗi cấu hình mạng sai lệch do Proposer tựa ra (hallucination).

 | Sử dụng kỹ thuật Reference-guided (cung cấp tài liệu chuẩn làm mỏ neo) hoặc yêu cầu giám khảo tự giải bài toán trước (Chain-of-Thought).

 |

Trong đó, phương pháp Chain-of-Thought (CoT) mang tính bước ngoặt. Thay vì yêu cầu Oracle chấm điểm ngay, prompt buộc Oracle phải tự phân tích log sự kiện và xây dựng giải pháp độc lập. Chỉ sau khi có kết luận riêng, Oracle mới được phép so sánh nó với các đề xuất của Candidate LLMs để tìm ra sai sót. Điều này ngăn chặn hiện tượng Oracle sao chép một cách mù quáng lỗi sai của các mô hình con. Đồng thời, trong các doanh nghiệp có hệ thống tài liệu vận hành chuẩn (Runbooks), việc nhúng các trích đoạn Runbook vào prompt để tạo thành "Reference-guided judge" (Giám khảo có đáp án tham chiếu) giúp giảm tỷ lệ đánh giá sai từ 70% xuống chỉ còn 15% trong các tác vụ đòi hỏi suy luận logic phức tạp.

## 4. Kiến Trúc Hạ Tầng Và Quản Lý Dữ Liệu Phân Tán

Việc hiện thực hóa một hệ thống AIOps đa tác nhân đòi hỏi một cơ sở hạ tầng bền bỉ, kết hợp giữa môi trường thực thi mô hình hiệu năng cao và một công cụ điều phối đồ thị trạng thái phức tạp.

Tại tầng thực thi, hệ thống triển khai các mô hình mã nguồn mở bằng vLLM, một engine phục vụ suy luận LLM được tối ưu hóa cao độ. Công nghệ cốt lõi của vLLM là thuật toán PagedAttention, lấy cảm hứng từ quản lý bộ nhớ ảo trong hệ điều hành. Các engine truyền thống thường cấp phát các khối bộ nhớ liền kề cho Key-Value (KV) cache, dẫn đến việc lãng phí từ 60% đến 80% bộ nhớ do phân mảnh. PagedAttention phân chia KV cache thành các khối không liền kề, giảm thiểu tỷ lệ lãng phí xuống dưới 4%, cho phép hệ thống tăng thông lượng (throughput) lên tới 24 lần, điều này cực kỳ quan trọng khi hệ thống phải xử lý đồng thời hàng nghìn dòng log hệ thống.

Quá trình triển khai vLLM được đóng gói hoàn toàn trong Docker Compose để đảm bảo tính khả lặp và cách ly tài nguyên. Khi cấu hình Docker cho vLLM, việc kiểm soát VRAM GPU là yếu tố sống còn. Biến `--gpu-memory-utilization 0.90` được thiết lập để giới hạn KV cache ở mức 90%, tạo bộ đệm an toàn chống lại các lỗi tràn bộ nhớ (OOM - Out of Memory) khi tải lượng truy cập đạt đỉnh. Đối với các mô hình tham số khổng lồ không thể chứa vừa trên một GPU (như mô hình 70B), hệ thống áp dụng kỹ thuật song song hóa tensor (Tensor Parallelism) thông qua cờ `--tensor-parallel-size`, phân tách tính toán qua nhiều card đồ họa vật lý. Các mô hình này được cấu hình với độ chính xác `bfloat16` để tối ưu VRAM mà không làm giảm đáng kể khả năng suy luận ngữ nghĩa. Trong trường hợp chạy nhiều phiên bản mô hình khác nhau để tạo thành các Candidate LLMs, một hệ thống cân bằng tải (Load Balancer) như Nginx được cấu hình với các khối `upstream` để định tuyến các yêu cầu API tương thích OpenAI từ LangChain đến đúng các container vLLM đang hoạt động.

Tầng điều phối (Orchestration Layer) được xây dựng dựa trên LangGraph, một framework chuyên dụng cho các luồng công việc đa tác nhân đòi hỏi duy trì trạng thái. Sự khác biệt giữa LangGraph và chuỗi xử lý truyền thống của LangChain nằm ở khả năng tạo ra các quy trình vòng lặp (cyclic graphs) và quản lý bộ nhớ dài hạn, phù hợp hoàn hảo với quá trình tranh luận và tổng hợp của MoA. Hệ thống lưu trữ một trạng thái toàn cục (Global State), đóng vai trò như một bảng nháp chia sẻ (Shared Scratchpad) nơi tất cả các tác nhân có thể ghi nhận và theo dõi các bước suy luận của nhau.

Khi một sự cố xảy ra, dữ liệu được truyền vào hệ thống LangGraph, đi qua một tác nhân định tuyến (Router Agent) có chức năng phân tích ban đầu và chuyển hướng yêu cầu đến các nhóm tác nhân chuyên gia (Subagents) hoặc tải thêm các kỹ năng (Skills) cần thiết theo yêu cầu. Các Subagents này sẽ gọi trực tiếp vào API của vLLM để sinh ra các đề xuất phân tích log. Cuối cùng, dữ liệu từ Shared Scratchpad được đóng gói và gửi cho Oracle Judge thông qua luồng LangChain Expression Language (LCEL). LCEL cung cấp cấu trúc đường ống nối tiếp (pipelining) hiện đại, thay thế cho cấu trúc `LLMChain` đã lỗi thời, hỗ trợ luồng dữ liệu bất đồng bộ và trả về kết quả dưới dạng JSON (Structured Output) một cách chặt chẽ. Toàn bộ quá trình từ lúc nhận cảnh báo đến lúc ra quyết định được giám sát chặt chẽ bởi LangSmith, cung cấp khả năng gỡ lỗi (debugging) từng bước suy luận, đảm bảo tính an toàn của hệ thống trước khi các lệnh thực thi cấu hình máy chủ được chuyển đến môi trường sản xuất thông qua cơ chế Human-in-the-Loop.

## 5. Kế Hoạch Triển Khai Thực Tiễn Trong 18 Tuần

Quá trình hiện thực hóa hệ thống AIOps Đa tác nhân được chia thành một lộ trình phát triển kéo dài 18 tuần (khoảng 4,5 tháng), tuân thủ nghiêm ngặt các mục tiêu từ nghiên cứu lý thuyết đến triển khai tích hợp. Kế hoạch này không chỉ vạch ra các mốc thời gian kỹ thuật mà còn định hướng cho quá trình làm việc tương tác với các hệ thống hỗ trợ lập trình bằng trí tuệ nhân tạo.

| Giai Đoạn Dự Án | Thời Gian Phân Bổ | Trọng Tâm Kỹ Thuật và Hoạt Động Cốt Lõi | Mục Tiêu Đầu Ra Đạt Được |
| --- | --- | --- | --- |
| **1. Khởi tạo & Chốt Đề Cương** | 1 Tuần (Tuần 1) | Giai đoạn thiết lập nền tảng dự án. Các kỹ sư và chuyên gia vận hành thống nhất cấu trúc thư mục dự án, xây dựng các tập tin thiết lập ban đầu và cấu hình môi trường phát triển cục bộ. Xác định các chỉ số đo lường hiệu quả (KPIs) cho hệ thống AIOps như tỷ lệ giảm MTTR. | Đề cương chi tiết của hệ thống được phê duyệt. Môi trường phát triển sẵn sàng tích hợp.

 |
| **2. Nghiên Cứu Lý Thuyết & Thu Thập Dữ Liệu** | 4 Tuần (Tuần 2 - 5) | Nghiên cứu sâu về kiến trúc Multi-Agent, lý thuyết LLM-as-a-Judge và các phương pháp phòng chống Bias. Tiến hành thu xuất dữ liệu log mẫu từ các hệ thống SIEM, QRadar hoặc ELK Stack, bao gồm cả log mạng và log hệ điều hành. Phân loại các mẫu tấn công và sự cố vận hành điển hình để làm dữ liệu nền tảng. | Hoàn thành nền tảng lý thuyết (Chương 1). Bộ dữ liệu log mẫu được làm sạch và chuẩn hóa hoàn chỉnh.

 |
| **3. Thiết Kế Kiến Trúc "Hội Đồng AI"** | 4 Tuần (Tuần 6 - 9) | Chuyển hóa lý thuyết thành thiết kế hệ thống. Phác thảo kiến trúc luồng dữ liệu trong LangGraph, định nghĩa các State và Router. Tập trung phát triển các mẫu System Prompt cho vị trí Judge, áp dụng kỹ thuật CoT và Reference-guided để đảm bảo tính khách quan. Cấu trúc hóa các tham số vLLM triển khai. | Thiết kế chi tiết hệ thống và Prompt (Chương 2). Bản thiết kế kiến trúc phân quyền rõ ràng giữa Proposers và Aggregators.[1, 1, 13] |
| **4. Lập Trình Hệ Thống & Tích Hợp** | 4 Tuần (Tuần 10 - 13) | Tiến hành viết mã nguồn (coding) sử dụng LangChain LCEL. Cấu hình Docker Compose cho các mô hình mã nguồn mở bằng vLLM. Xây dựng module kết nối API từ LangGraph tới mô hình Oracle. Lập trình module trích xuất Structured Output để hệ thống có thể đọc hiểu điểm số do Judge trả về. | Source code hệ thống hoàn thiện. Các Agent hoạt động ổn định song song, giao tiếp mượt mà không gặp lỗi nghẽn cổ chai.

 |
| **5. Thử Nghiệm, Mô Phỏng Sự Cố & Đánh Giá** | 4 Tuần (Tuần 14 - 17) | Triển khai Red Teaming, tấn công giả lập trên môi trường Kubernetes để tạo ra dữ liệu sự cố trực tiếp. Hệ thống thu thập log thời gian thực, đưa qua MoA. Đánh giá, đo lường độ chính xác (Accuracy), độ trễ (Latency) và so sánh trực tiếp hiệu năng của hệ thống MoA với phương pháp Single Model truyền thống. | Hoàn thành Chương 3, 4. Bảng đánh giá hiệu năng toàn diện chứng minh sự vượt trội của hệ thống Đa tác nhân.[1, 1] |
| **6. Hoàn Chỉnh Tài Liệu & Đóng Gói** | 1 Tuần (Tuần 18) | Tinh chỉnh mã nguồn lần cuối, loại bỏ các đoạn code dư thừa (refactoring). Tổng hợp các báo cáo đánh giá, hoàn chỉnh tài liệu luận văn/báo cáo kỹ thuật. Chuẩn bị slide và các môi trường trình diễn thực tế (demo). | Báo cáo hoàn chỉnh. Hệ thống sẵn sàng trình diễn và triển khai thử nghiệm trên môi trường Staging.

 |

Giai đoạn Lập trình (Tuần 10 - 13) là khâu mang tính thách thức cao nhất, đòi hỏi sự kiểm soát nghiêm ngặt về chất lượng mã nguồn. Để đẩy nhanh tiến độ mà không đánh đổi bằng các khoản nợ kỹ thuật (technical debt), dự án tận dụng khả năng lập trình hỗ trợ bởi AI thông qua môi trường phát triển tích hợp (IDE) Cursor, yêu cầu một hệ thống quy định chặt chẽ để hướng dẫn AI sinh mã chính xác.

## 6. Chiến Lược Triển Khai Môi Trường Lập Trình Tự Động Với Cursor IDE

Sự ra đời của Cursor IDE, một công cụ biên tập mã nguồn được tích hợp sâu Trí tuệ Nhân tạo, đã thay đổi hoàn toàn cách thức các kỹ sư tương tác với cơ sở mã (codebase) quy mô lớn. Khi xây dựng các hệ thống có độ rẽ nhánh phức tạp như kiến trúc LangGraph và MoA, việc thả nổi AI tự do sinh mã thường dẫn đến hiện tượng "ảo giác mã nguồn" (code hallucination), nơi AI sử dụng các thư viện đã bị loại bỏ (deprecated) hoặc phá vỡ các mẫu thiết kế kiến trúc đã thống nhất. Do đó, việc thiết lập một khung quy tắc nghiêm ngặt thông qua hệ thống tệp tin `.cursorrules` là yếu tố quyết định để duy trì sự nhất quán và chất lượng.

Khung quản lý quy tắc của Cursor được thiết kế theo cấu trúc phân tầng phức hợp, đảm bảo rằng tác nhân AI luôn được định hướng bởi các thông tin ngữ cảnh chính xác nhất tại mọi thời điểm. Tầng đầu tiên là Quy tắc Dự án Toàn cục (Global Project Rules), thường được thể hiện thông qua tệp tin `AGENTS.md` đặt tại thư mục gốc. Tệp tin này hoạt động như một bản tuyên ngôn kiến trúc cấp cao, cung cấp cho AI bức tranh toàn cảnh về mục tiêu kinh doanh, các quyết định kiến trúc quan trọng, và sơ đồ tư duy của hệ thống. Bằng cách bắt đầu mọi phiên làm việc với sự thấu hiểu từ `AGENTS.md`, AI có thể đưa ra các đề xuất phù hợp với định hướng hệ thống, thay vì sinh ra các đoạn mã rời rạc.

Tầng thứ hai là các Quy tắc Cụ thể Theo Tệp/Thư Mục (.cursor/rules/*.mdc). Các hệ thống mã nguồn lớn không thể được quản trị bằng một bộ quy tắc khổng lồ dài hàng vạn dòng, vì điều này sẽ làm cạn kiệt bộ nhớ ngữ cảnh (context window) của AI và làm chậm quá trình phản hồi. Thay vào đó, các quy tắc được phân mảnh (modularized) thành các tệp nhỏ, mỗi tệp nhắm mục tiêu vào một mô-đun cụ thể dựa trên biểu thức chính quy (glob patterns). Ví dụ, các quy tắc liên quan đến việc viết câu lệnh Prompt sẽ chỉ được kích hoạt khi kỹ sư làm việc trong thư mục `prompts/`, trong khi các quy định cấu hình phần cứng sẽ được ưu tiên khi thao tác với tệp `docker-compose.yml`. Phương pháp chia nhỏ này đảm bảo AI luôn tập trung vào các hành động có thể thực thi (actionable) và có phạm vi giới hạn.

Bên cạnh việc thiết lập quy tắc tĩnh, việc kiểm soát Luồng Ngữ cảnh Động (Dynamic Context Management) là kỹ năng cốt lõi của kỹ sư khi sử dụng Cursor. Để tăng tốc độ xử lý, các thư mục chứa dữ liệu không mang tính cấu trúc như `logs`, môi trường ảo `venv`, hay tài liệu không cần thiết phải được loại bỏ khỏi hệ thống lập chỉ mục (indexing) thông qua `.cursorignore`. Khi viết câu lệnh (prompting) cho AI, kỹ sư phải tuân thủ nguyên tắc "thiết lập giới hạn" (set constraints). Thay vì đưa ra yêu cầu mơ hồ như "Cải thiện mã nguồn này", một câu lệnh hiệu quả phải chỉ định rõ định dạng đầu ra, các ràng buộc thư viện và tham chiếu trực tiếp đến các thành phần hiện có trong codebase. Ví dụ: "Chuyển đổi luồng xử lý `LLMChain` trong tệp này sang định dạng LCEL, sử dụng đối tượng `ChatOpenAI` đã cấu hình trong `llm_config.py` và trả về kết quả qua `StrOutputParser`". Sự kết hợp giữa quy tắc dự án tĩnh và các câu lệnh ngữ cảnh động này tạo ra một vòng lặp phát triển phần mềm vừa nhanh chóng vừa tuân thủ tuyệt đối các chuẩn mực kỹ thuật khắt khe. Trong những dự án đòi hỏi kiến thức vận hành hạ tầng chuyên sâu, việc tích hợp các giao thức Model Context Protocol (MCP) server có thể cung cấp cho AI khả năng truy vấn trực tiếp vào tài liệu nội bộ, đưa năng lực hỗ trợ lập trình lên một tầm cao mới.

## 7. Tài Liệu Hướng Dẫn Kỹ Thuật (Artifacts) Dành Cho Cursor IDE

Các tệp cấu hình dưới đây được thiết kế chuyên biệt để đáp ứng các yêu cầu kiến trúc của hệ thống AIOps đa tác nhân. Kỹ sư hệ thống phải tích hợp các tệp này trực tiếp vào hệ thống quản lý mã nguồn của dự án để Cursor AI có thể tự động tiếp nhận các ràng buộc kỹ thuật trong quá trình hỗ trợ sinh mã.

### 7.1. Tệp Tổng Quan Kiến Trúc Dự Án: `AGENTS.md`

Tệp này đóng vai trò như bản thiết kế gốc, định nghĩa các quyết định cấp cao, giúp AI hiểu được luồng dữ liệu trước khi đi vào chi tiết mã nguồn.markdown

# Tổng Quan Dự Án: Hệ Thống AIOps Ứng Dụng Mixture-of-Agents (MoA)

## 1. Định Hướng Hệ Thống

Dự án này xây dựng một hệ thống Tự động hóa Phản ứng Sự cố (AIOps). Hệ thống thực hiện việc tiếp nhận log và cảnh báo thời gian thực từ hạ tầng Microservices, sử dụng cấu trúc hội đồng Đa tác nhân (Multi-Agent) để phân tích nguyên nhân gốc rễ (Root Cause Analysis), sau đó dùng cơ chế LLM-as-a-Judge để ra quyết định cuối cùng.

## 2. Kiến Trúc Tác Nhân (Agent Architecture)

* **Tác nhân Đề xuất (Candidate Proposers):** Là các LLM mã nguồn mở (ví dụ: Qwen, Llama 3) triển khai cục bộ qua vLLM. Các tác nhân này hoạt động song song để phân tích log và sinh ra nhiều báo cáo RCA độc lập.
* **Tác nhân Giám khảo (Oracle Aggregator):** Là mô hình cao cấp (ví dụ: GPT-4o). Nhiệm vụ của nó không phải là tự phân tích từ đầu, mà là tổng hợp, so sánh và đánh giá các báo cáo của Proposers, từ đó loại bỏ các đề xuất sai lệch (hallucination) và xuất ra hành động khôi phục tối ưu.
* **Điều phối viên (Orchestrator):** Toàn bộ quy trình được quản lý bởi LangGraph, duy trì một trạng thái toàn cục (State) dùng chung cho tất cả các tác nhân thao tác.

## 3. Cấu Trúc Mã Nguồn (Monorepo)

* `/agents`: Định nghĩa luồng làm việc của các Candidate LLM và Oracle LLM.
* `/orchestrator`: Cấu trúc Graph, Router và các State của LangGraph.
* `/prompts`: Tập hợp các mẫu câu lệnh (Prompt templates) chuyên dụng để chống bias.
* `/infrastructure`: Cấu hình Docker Compose để triển khai vLLM, ELK Stack và API Gateway.
* `/evals`: Bộ công cụ để chạy kiểm thử offline và chấm điểm hệ thống.

## 4. Nguyên Tắc Lập Trình (Core Rules)

* Mọi tương tác LLM phải sử dụng cú pháp LCEL của thư viện LangChain.
* Mọi thông báo lỗi cần được log lại bằng thư viện `logging` tiêu chuẩn. Không bao giờ sử dụng `print()`.
* Tuyệt đối tuân thủ đặc quyền tối thiểu: Mọi mã lệnh tác động đến hệ thống do AI tạo ra đều phải trải qua cơ chế phê duyệt Human-in-the-Loop.

```

### 7.2. Quy Tắc Lập Trình LangChain & LangGraph: `.cursor/rules/langchain.mdc`
Cấu hình này ép buộc AI sử dụng các chuẩn mực hiện đại nhất của hệ sinh thái LangChain, tránh việc sinh ra các đoạn mã dựa trên tài liệu lỗi thời.[15, 25]

```yaml
---
description: Hướng dẫn kỹ thuật và thực hành tốt nhất cho việc phát triển ứng dụng dựa trên LangChain và LangGraph.
globs: **/*.py
---

# Quy Tắc Phát Triển LangChain & LangGraph

## 1. Sử Dụng LangChain Expression Language (LCEL)
- **Bắt buộc:** Bạn phải luôn sử dụng LCEL với toán tử pipe (`|`) để nối các thành phần.
- **Nghiêm cấm:** Tuyệt đối không sử dụng `LLMChain` hoặc các lớp thiết kế kiểu cũ, vì chúng đã bị deprecated và không hỗ trợ streaming tốt.

*Mẫu thiết kế chuẩn:*
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser

prompt = ChatPromptTemplate.from_messages()
llm = ChatOpenAI(model="gpt-4o", temperature=0)
parser = PydanticOutputParser(pydantic_object=IncidentReport)

chain = prompt | llm | parser

## 2. Quản Lý Trạng Thái LangGraph (Stateful Graph)
- Mọi đồ thị LangGraph phải bắt đầu bằng việc định nghĩa một `TypedDict` cho State.
- State này phải chia sẻ bối cảnh của sự cố, chứa mảng danh sách các thông điệp (`messages`), danh sách các bản nháp từ Proposer (`proposals`), và phán quyết cuối cùng.
- Khi xây dựng các hàm Node, luôn thiết kế để chúng nhận tham số đầu vào là `state` và trả về một phần của state cần cập nhật (partial state update).

## 3. Định Dạng Đầu Ra Có Cấu Trúc (Structured Outputs)
- Khi gọi mô hình Giám khảo (Oracle), luôn yêu cầu mô hình xuất ra dữ liệu có cấu trúc bằng cách sử dụng `with_structured_output()` tích hợp sẵn Pydantic schema. Điều này đảm bảo việc trích xuất điểm số (Score) và nguyên nhân (Root Cause) không bị lỗi cú pháp JSON.

## 4. Giám Sát Và Truy Vết (Tracing)
- Đảm bảo việc khởi tạo môi trường có cấu hình đầy đủ biến môi trường của LangSmith (`LANGSMITH_TRACING=true`). Mã nguồn không cần phải gọi API trực tiếp, chỉ cần cấu hình đúng biến môi trường để LangChain tự động hook vào LangSmith.

```

### 7.3. Quy Tắc Triển Khai vLLM & Docker: `.cursor/rules/vllm-infrastructure.mdc`

Tệp cấu hình này hướng dẫn Cursor cách thiết lập môi trường chứa (container) tối ưu về phần cứng, đặc biệt quan trọng để chống tràn bộ nhớ GPU khi xử lý ngữ cảnh dài.

```yaml
---
description: Các quy định cấu hình hệ thống triển khai suy luận LLM thông qua Docker Compose và engine vLLM.
globs: docker-compose*.yml, infrastructure/**/*.sh
---

# Quy Tắc Triển Khai Hạ Tầng vLLM & Docker

## 1. Cấu Hình Hình Ảnh & Cổng Giao Tiếp
- Sử dụng hình ảnh Docker chính thức: `vllm/vllm-openai:latest`. Đây là bắt buộc để duy trì tính tương thích với API của OpenAI.
- Quản lý bộ nhớ đệm: Luôn cấu hình Volume mount thư mục `/root/.cache/huggingface` để hệ thống không phải tải lại các checkpoint mô hình nặng hàng chục Gigabyte khi khởi động lại.

## 2. Tối Ưu Hóa Tham Số Dòng Lệnh vLLM (Command Arguments)
Khi viết thuộc tính `command` trong tệp `docker-compose.yml`, hệ thống AI phải tích hợp các cờ (flags) sau:
- `--gpu-memory-utilization 0.90`: Thiết lập này là bắt buộc để dành 90% VRAM cho mô hình và KV Cache, giữ 10% an toàn chống lỗi Out-Of-Memory (OOM).
- `--dtype bfloat16`: Tối ưu hóa tính toán trên các GPU thế hệ mới, tiết kiệm bộ nhớ mà không suy giảm chất lượng.
- `--max-model-len`: Giới hạn kích thước cửa sổ ngữ cảnh để phù hợp với tài nguyên VRAM khả dụng (Ví dụ: 4096 hoặc 8192).

## 3. Quản Lý Đa GPU và Tải Phân Tán
- **Đơn mô hình, Đa GPU:** Nếu cần triển khai một mô hình lớn (VD: Llama-3-70B), phải cấu hình cờ `--tensor-parallel-size <N>` (với N là số lượng GPU vật lý).
- **Đa mô hình (Multi-Proposer):** Khi chạy song song nhiều mô hình (VD: Llama 3 và Qwen) trên các container khác nhau, hãy phân định thiết bị GPU rõ ràng qua thẻ `device_ids` trong Docker Compose và thiết lập proxy Nginx để định tuyến request tới các cổng `8000`, `8001`.

```

### 7.4. Quy Tắc Thiết Kế Prompt Cho LLM-as-a-Judge: `.cursor/rules/llm-judge.mdc`

Cấu hình này đặc biệt quan trọng để loại bỏ các xu hướng thiên lệch (biases) của LLM trong vai trò là giám khảo, đảm bảo kết quả đánh giá là chính xác và khách quan.

```yaml
---
description: Hướng dẫn thiết kế kỹ thuật câu lệnh (Prompt Engineering) chuyên sâu cho module LLM-as-a-Judge nhằm giảm thiểu sai lệch (biases).
globs: prompts/*.py, prompts/*.md
---

# Kỹ Thuật Viết Prompt Dành Cho Module LLM-as-a-Judge

## 1. Phòng Chống Độ Lệch Vị Trí (Position Bias)
- LLM có xu hướng thiên vị văn bản xuất hiện đầu tiên. 
- Mẫu câu lệnh (System Prompt) phải có chỉ thị nhấn mạnh: "Bạn phải giữ sự trung lập tuyệt đối. Không được để thứ tự xuất hiện của các báo cáo ảnh hưởng đến quyết định chấm điểm."
- Khi viết mã Python để sinh Prompt, yêu cầu AI tích hợp hàm `random.shuffle()` để tráo đổi ngẫu nhiên thứ tự của các giải pháp Proposer A và B trước khi chèn vào chuỗi văn bản.

## 2. Phòng Chống Độ Lệch Độ Dài (Verbosity Bias)
- Mô hình giám khảo thường cho điểm cao các giải pháp dài dòng.
- Prompt phải tích hợp chỉ thị: "Bỏ qua độ dài của câu trả lời. Một giải pháp ngắn gọn, cung cấp chính xác dòng lệnh khắc phục sự cố cần được ưu tiên hơn một bản báo cáo dài dòng nhưng thiếu tính thực thi."

## 3. Khử Danh Tính (Anonymization) Chống Self-Enhancement
- Trước khi đưa giải pháp của các Candidate LLMs vào Prompt, mã nguồn phải loại bỏ mọi định danh liên quan đến tên mô hình (Ví dụ: thay thế "Đây là phản hồi từ Qwen" bằng "Phản hồi từ Trợ lý A").

## 4. Bắt Buộc Sử Dụng Suy Luận Chuỗi Tư Duy (Chain-of-Thought)
- Tuyệt đối không yêu cầu mô hình giám khảo đưa ra điểm số ngay lập tức.
- Prompt phải cấu trúc rõ quy trình yêu cầu giám khảo tự phân tích:
  1. Tự phân tích tập log hệ thống được cung cấp.
  2. Chỉ ra các lỗi sai trong suy luận của Trợ lý A.
  3. Chỉ ra các lỗi sai trong suy luận của Trợ lý B.
  4. Viết ra giải pháp tối ưu được dung hợp từ các điểm mạnh.
  5. Đưa ra phán quyết cuối cùng (Điểm số cho từng mô hình).
- Việc bắt buộc giám khảo tự tư duy sẽ ngăn chặn việc nó bị đánh lừa bởi dữ liệu sai lệch (hallucination) từ các mô hình cấp dưới.

```

Bằng việc kết hợp nhuần nhuyễn nền tảng lý thuyết vững chắc về kiến trúc Mixture-of-Agents và sự am hiểu sâu sắc về kiểm soát thiên lệch trong mô hình LLM-as-a-Judge, dự án này không chỉ giải quyết triệt để bài toán tự động hóa phản ứng sự cố công nghệ thông tin mà còn thiết lập một tiêu chuẩn mới về vận hành hệ thống thông minh. Đồng thời, bộ nguyên tắc hướng dẫn tích hợp sâu vào môi trường Cursor IDE sẽ biến trí tuệ nhân tạo từ một công cụ sinh mã thụ động thành một người đồng hành đắc lực, tuân thủ tuyệt đối các ràng buộc kiến trúc và bảo vệ dự án khỏi các khoản nợ kỹ thuật phức tạp trong tương lai. Kế hoạch triển khai toàn diện này là kim chỉ nam để chuyển hóa những ý tưởng học thuật tiên tiến nhất thành một sản phẩm thực tiễn, định hình lại tương lai của quy trình quản trị hạ tầng phần mềm.

```

```