**Dự án Inside Airbnb London (Nhóm 15, lớp UET.DSE2049 7)**

## Công cụ đã dùng

- Nhóm sử dụng Claude và Codex trong quá trình tìm hiểu đề, khảo sát dữ liệu, phát triển mã và hoàn thiện tài liệu. Nhóm đưa yêu cầu, đề xuất cách tổ chức, lựa chọn cấu hình và phản biện các phương án. AI hỗ trợ giải thích, tạo khung, viết hoặc sửa các phần mã được giao và thực hiện các phép kiểm theo yêu cầu.

- **Codex** hỗ trợ nhóm đọc dữ liệu nguồn, rà YAML, xây dựng bộ tải và viết mã trích bộ phân công của nhóm 15 từ bảng Excel của môn học. Mã trích xuất ghi `listings.csv`, `reviews.csv`, `areas.csv` và `manifest.json` vào `data/assignment/` để pipeline đọc lại ở những lần chạy sau. Từ các đầu vào đó, Codex hỗ trợ tích hợp mã thực hành và hoàn thiện các bước Prepare, QA, LLM, baseline, KPI, đánh giá và xuất hình. Nhóm nhờ Codex dựng các trường hợp dữ liệu lỗi để kiểm tra chỗ nối giữa các bước. Codex cũng giải đáp các thao tác Python/pandas, rà notebook, xử lý lỗi môi trường và Git, đối chiếu số liệu và biên tập bản khai báo này.

- **Claude** tạo các notebook trong `notebooks/khao_sat_du_lieu/` để nhóm khảo sát listings, calendar, reviews và dữ liệu không gian qua bốn mốc. Nhóm nhờ Codex đọc lại mã trong notebook, đối chiếu số liệu với dữ liệu nguồn và rà cách diễn giải. Nhóm cũng dùng Claude để tham khảo khung QA và cấu trúc phần LLM, rồi đối chiếu các đề xuất với mã đang viết.

- **Claude Code** tham gia hoàn thiện dự án theo yêu cầu của nhóm, công cụ gom phần dùng chung, chuyển baseline sang thao tác theo cột và bổ sung phép so sánh theo quận trong `src/kpi.py`. Claude Code cũng soạn bản nháp báo cáo, cập nhật README và từ điển dữ liệu, biên dịch PDF và chạy thử pipeline. Nhóm chọn tình huống cần thử và yêu cầu sửa các kết luận vượt quá bằng chứng.

- **Claude Code tạo bộ dữ liệu mẫu nhỏ.** Claude Code viết và chạy script chọn ba listing đầu tiên của mỗi vùng A01–A08 theo thứ tự trong bảng phân công. Script trích dữ liệu chỗ ở, lịch và review của cùng 24 listing từ bốn snapshot và lưu vào `data/samples/mau_nho/` để chạy thử quy trình xử lý.

- **Gemini API** được chương trình dùng để gán cảm xúc, khía cạnh khen/chê và ngôn ngữ cho mẫu 1.000 review. Model đã được dùng là `gemini-3.5-flash-lite`. Nhóm cung cấp bộ nhãn tay để đánh giá kết quả và lựa chọn lưu cache để phục vụ chạy lại.

- Phần nhóm trực tiếp tham gia gồm viết và chỉnh bộ tải, cấu hình và mã thực hành, tổ chức bảng nhãn tay, gửi kết quả chạy và yêu cầu kiểm lại những điểm chưa rõ. Nhóm thống nhất hướng phân tích cho hiệp hội du lịch, mốc phân tích giá, quy ước ngày và trách nhiệm của từng module qua quá trình trao đổi với AI. Khi hoàn thiện từng phần, nhóm nhờ AI đề xuất khung, giải thích các lựa chọn rồi phản hồi để chỉnh theo yêu cầu của dự án.

## Prompt then chốt (5–10):

Các prompt dưới đây được diễn đạt lại từ những yêu cầu nhóm đã trao đổi trong quá trình làm dự án.

- **1. Khảo sát dữ liệu với Claude.** "Tôi muốn xem dữ liệu London có gì trước khi viết code xử lý. Dùng bốn mốc đã tải để làm notebook riêng cho listings, calendar, reviews và GeoJSON. Mỗi notebook ghi rõ đang đọc file nào, kiểm những cột nào và giải thích cách đọc các bảng, hình. Thêm một phần chỉ cách nối các bảng và một phần tổng hợp những vấn đề nhóm cần xử lý."

  Áp dụng vào sáu notebook trong `notebooks/khao_sat_du_lieu/`, từ `01_tong_quan.ipynb` đến `06_tong_hop.ipynb`.

- **2. Rà lại các notebook với Codex.** "Đọc lại từng notebook và chỉ cho tôi mỗi bảng, hình đang lấy từ file nào và đã lọc những ID nào. Đếm lại listing và review ở từng mốc theo bảng phân công. Với giá, kiểm xem thiếu cả cột hay cột vẫn có mà ô bị trống. Ở phần lịch, tính lại số ngày `available=t` trong 30, 90 và 365 ngày rồi so với listings. Giải thích dòng `khớp 1000/1000` đang đếm gì. Kiểm thêm nội dung của cùng một `review_id` qua các mốc, 100 review nhãn tay có nằm trong mẫu LLM không và tên quận trên bản đồ có khớp GeoJSON không. Nếu thấy sai, chỉ rõ notebook, ô cần xem và cách tính lại."

  Áp dụng vào sáu notebook khảo sát, đối chiếu với `data/raw/` và `data/assignment/`. Nhóm xem lại cách lọc, ghép và đếm, rồi hỏi thêm những chỗ dễ hiểu sai trước khi dùng kết quả khảo sát.

- **3. Rà cấu hình, bộ tải và môi trường.** "Đọc `london.yaml` rồi xem `download.py` và các file khác đang dùng khóa nào. Tôi muốn giữ ngày trong `snapshots` ở dạng `YYYY-MM-DD` không có dấu nháy và dùng chung hàm `doc_cau_hinh()` trong `common.py`. Xem còn khóa nào thiếu, thừa hoặc có giá trị chưa có căn cứ, nhất là các ngưỡng QA. Kiểm thêm phiên bản Python và xem `requirements.txt` đã đủ để chạy pipeline chưa. Gói nào chỉ dùng cho notebook thì để riêng."

  Áp dụng vào `configs/london.yaml`, `src/common.py`, `src/download.py`, `.python-version`, `requirements.txt` và `requirements-dev.txt`.

- **4. Chuẩn bị dữ liệu theo danh sách ID.** "Bảng phân công đã có trong `data/assignment/` rồi. Dùng lại đoạn lọc ID nhóm viết. Với listings, đối chiếu cột `id` của file gốc với `listing_id` trong phân công. Dùng cùng danh sách chỗ ở để lọc lịch, còn review dùng danh sách `review_id` riêng. Phần lịch làm rõ từng bước giúp tôi, từ lọc ID, đổi `t`/`f` sang boolean đến ghép tên quận và vùng A01–A08 từ listings cùng mốc. Nếu có dòng lịch không tìm thấy listing để ghép, báo rõ chỗ đó. Xem cách tôi đặt tên hàm và biến trong `download.py` rồi viết `prepare.py` theo cùng cách."

  Áp dụng vào `src/prepare.py` và phần đọc phân công trong `src/common.py`.

- **5. Kiểm tra dữ liệu và đo tác động lên KPI.** "Đọc `prepare.py` và phần QA Claude gợi ý. Chỗ nào Prepare đã kiểm rồi thì chỉ ra giúp tôi. Tôi muốn QA gắn cờ, còn công thức tính chỉ số để trong `kpi.py`. Thử xem giá trung vị và số mức giá dùng để tính thay đổi bao nhiêu khi bỏ giá vượt ngưỡng hoặc ngoài rào IQR. Với lịch, giải thích vì sao mỗi listing có 365 ngày mà cửa sổ 90 ngày vẫn có thể thiếu dữ liệu. Tính riêng tỷ lệ ngày sẵn có và độ phủ lịch, rồi ghi rõ mẫu số của từng tỷ lệ."

  Áp dụng vào `src/qa.py`, `src/kpi.py` và hai phần `qa`, `kpi` trong `configs/london.yaml`. Nhóm trao đổi về vị trí của công thức và yêu cầu đối chiếu tác động của các ngưỡng trước khi chốt cách dùng.

- **6. Thử gửi 100 review một lượt cho Gemini.** "Tôi định chạy trên 1.000 review. Thử gửi 100 review một lượt cho Gemini rồi đối chiếu `review_id` trả về với danh sách đã gửi, xem có ID nào thiếu, trùng hoặc bị sai không. Nếu chỉ 10 review trả về hợp lệ thì code giữ lại 10 kết quả đó và gửi lại 90 review còn thiếu thế nào? Chỉ tôi đoạn xử lý trường hợp này. Ghi lại số token của lượt thử để nhóm ước tính chi phí."

  Áp dụng vào `src/llm.py`, phần LLM trong `configs/london.yaml` và `data/processed/llm_cache.jsonl`. Nhóm dùng Gemini trong bản chạy chính. Các nhãn hợp lệ được lưu để chạy lại và các lượt gọi được ghi trong `data/processed/llm_usage.csv`.

- **7. Chấm Gemini và baseline trên cùng 100 review.** "Nhóm đã có 100 review gán nhãn tay. Ghép nhãn tay với kết quả Gemini và baseline từ khóa theo `review_id` để hai cách được chấm trên cùng tập. Tính accuracy và macro-F1 cho cảm xúc, micro-F1 cho phần khen và phần chê. Cho tôi một bảng đọc lại từng review bị đoán sai để xem phương pháp nào hay nhầm cảm xúc, bỏ sót hoặc gán thừa khía cạnh."

  Áp dụng vào `src/baseline.py`, `src/evaluate.py` và `reports/evaluation_*.csv`. Nhóm cung cấp `data/samples/nhan_tay.csv` làm dữ liệu tham chiếu.

- **8. Chạy thử với mẫu nhỏ và cấu hình đổi mốc.** "Chạy thử trên bản sao tạm với mẫu 24 chỗ ở, dùng cache có sẵn và bỏ khóa API khỏi môi trường. Tôi muốn xem thiếu ID, còn ít nhãn tay hoặc không có quận đủ mẫu thì chương trình đi tới bước nào. Thử thêm trường hợp bỏ mốc cuối trong `snapshots` nhưng quên sửa `price_snapshot`. Nếu dừng, ghi đúng bước và thông báo lỗi."

  Áp dụng vào `run_pipeline.py`, `configs/london.yaml`, `src/kpi.py` và `data/samples/mau_nho/`. Claude Code thực hiện các lượt thử trên bản sao tạm theo tình huống nhóm yêu cầu.

- **9. Đối chiếu hình và kết luận trong báo cáo.** "Đọc bản PDF cùng các bảng KPI và chỉ ra từng hình đang lấy số liệu ở đâu. Kiểm lại đơn vị, mốc và cỡ mẫu. Phần nói về giá và trải nghiệm khách đang dựa vào số liệu so giữa các quận. Xem giúp tôi số liệu đó đủ để nhận xét về từng chỗ ở chưa. Nếu cần tính thêm, ghi rõ phải ghép bảng nào và dùng cột nào để lần sau chạy lại được."

  Áp dụng vào `src/viz.py`, `src/kpi.py`, `data/processed/kpi_so_sanh_quan.csv` và `reports/report.pdf`. Sau khi Claude Code chỉ ra tám chỗ cần xem lại, nhóm yêu cầu sửa cả tám.

## AI sai ở đâu và nhóm xử lý thế nào

- **KPI: Chương trình dừng khi không quận nào đủ mẫu**

  Khi chạy trên mẫu nhỏ, không quận nào đạt ngưỡng `kpi.min_n` là 10 chỗ ở có dữ liệu lịch hợp lệ. Bảng tỷ lệ sẵn có theo quận vì thế không còn cột mốc nào. Bản cũ trong `src/kpi.py` vẫn dùng `san_co.columns.max()` để tìm mốc cuối. Phép tìm trả về `NaN`, nên khi chương trình dùng giá trị đó làm tên cột, nó báo `KeyError: nan` và dừng.

  Nhóm yêu cầu chạy lại trên cùng mẫu nhỏ. Claude Code thêm kiểm tra `san_co.empty` trước bước tìm cột mốc cuối và thử lại cả hai bản. Với bảng rỗng, bản sửa ghi lý do bỏ qua phép tìm quận bất thường và xuất `kpi_bat_thuong.csv` chỉ có tiêu đề cột. Các bảng KPI cơ bản vẫn được xuất và pipeline chạy tiếp.

- **Chuẩn bị dữ liệu: Đổi kiểu cờ mẫu ngay khi đọc bảng phân công**

  Khi gom mã đọc phân công vào `src/common.py`, Codex chuyển `llm_sample` và `human_sample` sang boolean ngay trong hàm đọc. Nhóm thấy bảng trả về đã khác kiểu dữ liệu trong CSV và hỏi vì sao việc chuẩn hóa lại nằm ở bước đọc.

  Theo yêu cầu của nhóm, bản sửa để `doc_phan_cong()` đọc và kiểm tra các cột, rồi trả bảng ở dạng chuỗi như lúc đọc CSV. Hàm `chuan_hoa_phan_cong_review()` trong `src/prepare.py` chuyển hai cờ sang boolean trên một bản sao trước khi ghép vào bảng review.

- **KPI: Đề xuất cách xử lý giá sai phạm vi**

  Codex ban đầu đề xuất điền giá thiếu ở mốc tháng 12 hoặc tính giá cho các mốc còn dữ liệu. Nhóm yêu cầu đối chiếu lại hướng dẫn xử lý dữ liệu thiếu và xác nhận phạm vi phân tích giá chỉ gồm mốc cuối.

  Nhóm chốt dùng giá quan sát được tại mốc 19/06/2026. `src/kpi.py` chỉ tính KPI giá tại mốc này. Số chỗ ở, cơ cấu loại phòng và lịch sẵn có được phân tích qua cả bốn mốc.

- **LLM: Giải thích cỡ mẫu 1.000 review thiếu căn cứ**

  Codex ban đầu chỉ giải thích rằng nhóm dùng 1.000 review vì đó là số lượng được giao. Nhóm yêu cầu xem dữ liệu thực tế để biết mẫu bao phủ bao nhiêu chỗ ở và vùng, đồng thời xem khối lượng gọi API.

  Codex đối chiếu được 1.000 review thuộc 375 chỗ ở, có mặt ở cả tám vùng A01–A08. Nhóm dùng độ bao phủ này và khối lượng xử lý qua Gemini để giải thích vì sao giữ cỡ mẫu. Các nhận định về trải nghiệm khách được giới hạn trong mẫu đã khảo sát.

- **LLM: Thêm `httpx` trực tiếp vào mã gọi Gemini**

  Khi rà `src/llm.py`, một thành viên thấy Codex thêm `import httpx` và hỏi mô-đun cần dùng thư viện này ở đâu. Sau khi xem lại cơ chế thử lại sẵn có của Gemini SDK, nhóm yêu cầu rút gọn phần gọi API.

  Bản sửa bỏ lệnh import trực tiếp và dùng `retry_options` của Gemini SDK. Số lần thử và thời gian chờ ban đầu đọc từ cấu hình của nhóm.

- **Báo cáo: Diễn giải sai vùng của Ealing**

  Bản nháp do Claude Code soạn ghi rằng các chỗ ở của quận Ealing trong mẫu đều thuộc A01. Theo yêu cầu rà báo cáo của nhóm, Claude Code lọc `neighbourhood_cleansed=Ealing` rồi đếm lại theo `analysis_area`. Kết quả là 13 chỗ ở thuộc A01 và 18 chỗ ở thuộc A03.

  Claude Code sửa bản thảo theo số đếm đã đối chiếu. Khi mô tả kết quả, nhóm dùng tên quận và mã vùng phân công theo hai cột riêng.

- **Gemini: Bỏ sót hoặc gán thừa khía cạnh được khen**

  Trên cùng 100 review có nhãn tay, Gemini bỏ sót 25 lượt khía cạnh được khen có trong nhãn tay và gán thêm 74 lượt ngoài nhãn tay. Mỗi lượt tính theo một cặp review và khía cạnh, nên một review có thể có nhiều lượt sai.

  Nhóm dùng cùng bộ nhãn tay để chấm Gemini và baseline. `reports/evaluation_metrics.csv` ghi số lượt đúng, thừa, thiếu và điểm micro-F1. `reports/evaluation_errors.csv` ghi từng review và các khía cạnh bị gán thừa hoặc bỏ sót để nhóm đọc lại nội dung cụ thể.

## Nhóm kiểm chứng thế nào

- **Đối chiếu bộ phân công với Excel gốc.** Codex lọc đúng lớp UET.DSE2049 7 và nhóm 15 trong bản Excel lưu trong lịch sử dự án. Kết quả khớp 1.000 ID chỗ ở và vùng được giao, 5.000 ID review kèm ID chỗ ở và hai cờ chọn mẫu, cùng tám vùng và các tọa độ biên. Khi chạy pipeline, `doc_phan_cong()` kiểm lớp, nhóm, đối chiếu số dòng và cỡ mẫu trong các CSV với `manifest.json`, đồng thời kiểm thành phố, tiền tệ và mã bộ dữ liệu với YAML.

- **Kiểm cách notebook đếm ngày sẵn có.** Nhóm hỏi dòng `availability_30 khớp 1000/1000` đang đếm gì. Codex rà ô tính kết quả và đối chiếu số ngày có `available=t` trong lịch với `availability_30` của từng chỗ ở. Kết quả `1000/1000` cho biết cả 1.000 chỗ ở đều có số ngày đếm từ lịch khớp với số ghi trong listings.

- **Kiểm dòng lịch có ghép được vùng hay không.** Nhóm hỏi liệu so số dòng trước và sau có phát hiện được lỗi khi đã dùng `how="left"` và `validate="many_to_one"`. Qua ví dụ một dòng lịch thiếu listing tương ứng ở cùng mốc, nhóm thấy phép ghép vẫn giữ dòng đó. Trong `prepare.py`, cột `_merge` cho biết dòng này chưa ghép được tên quận và vùng phân công trước khi chuyển sang QA.

- **Thử dữ liệu sai kiểu và dữ liệu lịch thiếu.** Theo yêu cầu của nhóm, Codex thử một listing có tọa độ `abc`, `minimum_nights=2.5` và số lượt review sai kiểu. Sau khi sửa Prepare và QA, lượt thử qua bước ghi rồi đọc lại CSV xác nhận dòng được giữ, QA gắn đủ ba cờ và đặt `du_dieu_kien_ban_do=False`. Trong lượt thử khác, Codex xóa một ngày lịch và để trống một ô `available`. QA ghi đúng listing thiếu ngày, gắn cờ dòng có trạng thái trống và KPI lịch chỉ tính những ngày có trạng thái hợp lệ.

- **Đo tác động của ngưỡng giá.** Nhóm yêu cầu dùng cùng một công thức để tính KPI giá trước và sau khi loại các mức giá bị gắn cờ. Codex đối chiếu kết quả trong `reports/qa_report.csv`. Tại mốc giá, bỏ bốn giá vượt 5.000 GBP làm số quan sát giảm từ 980 xuống 976 và trung vị giảm từ 232 xuống 231 GBP/đêm. Nhóm dùng phép thử này để trình bày độ nhạy của KPI đối với ngưỡng giá.

- **Kiểm hai mẫu số của KPI lịch.** Nhóm hỏi vì sao lịch có 365 ngày cho mỗi chỗ ở mà vẫn thiếu dữ liệu trong cửa sổ 90 ngày. Codex đối chiếu ngày thực tế trong lịch với cửa sổ bắt đầu từ `snapshot_date` và kiểm hai phép tính trong `kpi_calendar.csv` ở mốc 19/06/2026. Tỷ lệ ngày sẵn có lấy 43.206 cặp sẵn có chia cho 83.853 cặp hợp lệ quan sát được. Độ phủ lấy 83.853 chia cho 90.000 cặp kỳ vọng.

- **Đối chiếu bộ nhãn tay trước khi chấm.** Codex so `review_id` trong `data/samples/nhan_tay.csv` với `human_sample` và `llm_sample` trong bảng phân công. Bộ nhãn tay có 100 ID duy nhất và tất cả đều nằm trong mẫu LLM. Hai bảng kết quả Gemini và baseline có cùng 1.000 ID, chứa đủ 100 ID cần chấm. Nhóm dùng cảm xúc và khía cạnh để chấm điểm mặc định. Bộ nhãn tay và baseline cùng điền `en` theo quy ước, còn Gemini tự trả mã ngôn ngữ của từng review.

- **Thử xử lý khi Gemini trả thiếu ID.** Khi nhóm hỏi một lượt gửi chỉ trả về một phần review thì sao, Codex dùng phản hồi giả lập để kiểm luồng trong `src/llm.py`. Lượt đầu gửi hai ID và nhận một nhãn hợp lệ. Chương trình lưu nhãn đó vào cache, lượt tiếp theo chỉ gửi lại ID còn thiếu. Khi phản hồi thứ hai hợp lệ, cache có đủ hai nhãn.

- **Kiểm kết luận về giá và trải nghiệm khách.** Nhóm yêu cầu xem dữ liệu có đủ để nhận xét về mối liên hệ giữa giá và tỷ lệ review tích cực ở từng chỗ ở hay không. Claude Code ghép hai đại lượng theo `listing_id` rồi tính tương quan hạng Spearman. `kpi_so_sanh_quan.csv` ghi hệ số khoảng 0,061 trên 369 chỗ ở có đủ dữ liệu. Nhóm dùng kết quả này để điều chỉnh cách diễn đạt trong báo cáo.

- **Chạy lại quy trình với mẫu nhỏ và với đủ dữ liệu.** Theo yêu cầu của nhóm, Claude Code chạy pipeline trên bản sao dùng mẫu 24 chỗ ở, bổ sung GeoJSON từ dữ liệu nguồn và đọc nhãn từ cache. Lượt thử chạy hết với những hình đủ dữ liệu để vẽ. Claude Code cũng thử bỏ mốc cuối khỏi `snapshots` mà giữ `price_snapshot` cũ và xác nhận chương trình chỉ rõ lỗi ngay khi đọc cấu hình. Sau các chỉnh sửa cuối, Codex chạy lại lệnh mặc định trên cả bốn snapshot trong thư mục tạm, dùng dữ liệu thô và môi trường Python sẵn có. Lượt chạy dùng đủ 1.000 nhãn từ cache khi không đặt khóa API, sinh 10 hình và 11 tệp CSV khớp với bản đã lưu.
