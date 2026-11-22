# Từ điển dữ liệu Airbnb London (Nhóm 15)

Để xem kết quả phân tích, mở các tệp `kpi_*.csv` trong `data/processed/`. Báo cáo `reports/qa_report.csv` ghi tác động của các quy tắc kiểm tra dữ liệu. Tệp `reports/evaluation_errors.csv` ghi chi tiết các review mà Gemini hoặc baseline dự đoán sai nhãn.

Tài liệu này mô tả các cột do nhóm bổ sung, đổi tên hoặc sử dụng để tính chỉ số. Các cột gốc được mô tả trong [tài liệu dữ liệu Inside Airbnb](https://insideairbnb.com/get-the-data/). Mọi đường dẫn đều tính từ thư mục gốc của repo.

Khi mở tệp CSV, nên đọc `listing_id` và `review_id` dưới dạng văn bản để giữ nguyên các chữ số. `snapshot_date` là ngày chụp dữ liệu, `calendar_date` là ngày lưu trú, còn `date` trong bảng review là ngày khách viết đánh giá. Các tỷ lệ lưu theo thang 0–1. Chẳng hạn, `0.515` tương đương **51,5%**.

## Dữ liệu theo từng mốc

Trong `data/processed/london/<mốc>/`, các tệp có hậu tố `_assigned.csv` chứa dữ liệu đã chuẩn bị theo phạm vi phân công của nhóm. Tệp `_qa.csv` tương ứng bổ sung các cờ kiểm tra chất lượng. Pipeline tạo lại các bảng này khi chạy, và Git bỏ qua chúng.

- **Chỗ ở:** Mỗi dòng trong `listings_assigned.csv` tương ứng với một chỗ ở tại mốc đang xét. `listing_id` lấy từ cột `id` của dữ liệu gốc. `analysis_area` ghi vùng được giao trong A01–A08. `price_raw` giữ giá gốc, còn `price_gbp` là giá đã chuyển sang dạng số tại mốc tính giá **19/06/2026**, đơn vị GBP/đêm. Trong `listings_qa.csv`, `price_gbp_kpi` chỉ giữ các mức giá đủ điều kiện tính KPI. Khi đủ dữ liệu, `khoang_cach_moc_truoc_km` ghi khoảng cách giữa vị trí của cùng một chỗ ở tại hai mốc liền kề.
- **Lịch:** Mỗi dòng trong `calendar_assigned.csv` là lịch của một chỗ ở cho một ngày lưu trú tại một mốc chụp. Prepare đổi tên `date` thành `calendar_date`, chuyển trạng thái `t`/`f` sang `True`/`False` và ghép thêm hai cột vùng `analysis_area` và `neighbourhood_cleansed`. Trong `calendar_qa.csv`, `du_dieu_kien_lich` cho biết dòng có đạt các quy tắc kiểm tra lịch hay không. Nếu đạt, `available_kpi` giữ trạng thái đã chuẩn hóa. Nếu dòng không đạt, ô này để trống. Ngày có trạng thái `False` vẫn được tính vào mẫu số khi đủ điều kiện và nằm trong cửa sổ KPI.
- **Review:** Mỗi dòng trong `reviews_assigned.csv` là một review tại một mốc chụp. `review_id` lấy từ cột `id` gốc. `llm_sample` và `human_sample` đánh dấu review thuộc mẫu chạy LLM và mẫu gán nhãn tay. `reviews_qa.csv` bổ sung cờ `du_dieu_kien_llm`. Gemini và baseline cùng đọc bảng QA ở mốc cuối và dùng các review có cả `llm_sample=True` và `du_dieu_kien_llm=True`.

Cờ `qa_*` nhận `True` khi dòng vi phạm quy tắc tương ứng. `qa_so_co` đếm số cờ được bật trên cùng một dòng. Các cột `du_dieu_kien_*` cho biết dòng có dùng được cho từng mục đích hay không, chẳng hạn phân tích chung, tổng hợp theo vùng hay vẽ bản đồ. Một dòng bị gắn cờ vẫn có thể dùng cho những phép tính mà lỗi đó không ảnh hưởng.

Ngoài các thư mục theo mốc, `data/processed/london/` có ba bảng gộp. `listings_all_snapshots.csv` nối các bảng listings để theo dõi thay đổi của từng chỗ ở qua thời gian. `reviews_unique.csv` giữ một dòng cho mỗi `review_id`, lấy bản ghi ở mốc mới nhất có review đó. `review_appearances.csv` ghi từng cặp `review_id` và `snapshot_date` để tra cứu một review đã xuất hiện ở những mốc nào.

## Đọc báo cáo QA

`reports/qa_report.csv` tổng hợp kết quả kiểm tra chất lượng dữ liệu qua các mốc. Mỗi dòng tóm tắt một quy tắc kiểm tra trên một bảng, một phép đối chiếu giữa hai mốc hoặc một phép so sánh KPI.

- Lọc theo `snapshot_date` và `bang` để chọn đúng bảng cần xem. `snapshot_truoc` có giá trị khi đối chiếu với mốc trước. `pham_vi` cho biết đây là phép kiểm trong mốc, phép đối chiếu giữa hai mốc, phép đo tác động lên KPI hay một kịch bản xử lý.
- Đọc `quy_tac`, `dieu_kien`, `ly_do` và `hanh_dong` để hiểu cơ sở kiểm tra và hướng xử lý. Sau đó đối chiếu `so_anh_huong` với `mau_so` và xem `ty_le` nếu tính được. Xem cột `don_vi` để biết quy tắc đang đếm dòng, ID, review hay cặp chỗ ở–ngày.
- `trang_thai` cho biết kết quả đạt, cần xem lại, chỉ ghi nhận hoặc chưa đủ dữ liệu để kiểm tra. Khi cần đối chiếu từng bản ghi, tra danh sách ID trong `id_anh_huong`. Một số quy tắc có thêm `nguong` và `don_vi_nguong`. Dòng kiểm tra số cặp chỗ ở–ngày trong cửa sổ KPI ghi thêm `do_phu`.
- Với dòng so sánh KPI, đọc `kpi_ten`, `kpi_truoc`, `kpi_sau` và `don_vi_kpi`, kèm số quan sát tương ứng ở `n_truoc` và `n_sau`. Chẳng hạn, ở mốc tính giá, kịch bản bỏ bốn mức giá trên 5.000 GBP làm giá trung vị giảm từ 232 xuống 231 GBP/đêm. Số mức giá dùng để tính giảm từ 980 xuống 976.

## Đọc các chỉ số KPI

Ba tệp `kpi_listings.csv`, `kpi_calendar.csv` và `kpi_llm.csv` nằm trong `data/processed/`. Mỗi dòng ghi một chỉ số tại một mốc và một phạm vi cụ thể. Đọc `snapshot_date`, `city`, `pham_vi` và `khu_vuc` để xác định phạm vi của chỉ số trước khi xem giá trị.

`pham_vi=city` là toàn bộ mẫu nhóm được giao ở London. `neighbourhood` chia theo quận trong `neighbourhood_cleansed`, còn `analysis_area` chia theo vùng A01–A08. Sau khi lọc đúng phạm vi, đọc `kpi_ten`, `gia_tri` và `don_vi`. Với tỷ lệ, có thể xem lại phép tính qua `tu_so` và `mau_so`. Với giá trung vị, `mau_so` là số giá hợp lệ đã dùng.

Khi so sánh hai nhóm, xem thêm `so_listing` để biết số chỗ ở đóng góp vào chỉ số và `du_mau` để biết số đó có đạt ngưỡng `kpi.min_n` hay không. Ngưỡng hiện tại là 10 chỗ ở. Nếu `gia_tri` để trống, đọc `trang_thai` để biết nguyên nhân, chẳng hạn thiếu dữ liệu hoặc thiếu nhãn LLM.

### Chỗ ở và giá

Trong `kpi_listings.csv`, `so_listing` đếm các chỗ ở đủ điều kiện phân tích. `ty_le_nguyen_can` lấy số chỗ có loại `Entire home/apt` chia cho số chỗ có loại phòng hợp lệ. Hai chỉ số này có ở mỗi snapshot.

Hai chỉ số về giá chỉ được tính tại mốc 19/06/2026. `gia_trung_vi_gbp` lấy trung vị các mức giá hợp lệ trong phạm vi đang xét. `gia_trung_vi_gbp_nguyen_can` dùng cùng cách tính và chỉ xét chỗ thuê trọn nhà hoặc căn hộ, giúp so sánh mặt bằng giá giữa các quận trên cùng loại hình thuê.

### Lịch sẵn có

Hai chỉ số trong `kpi_calendar.csv` đều dùng cửa sổ 90 ngày bắt đầu từ ngày chụp dữ liệu, tính cả ngày đó. Mỗi quan sát là một cặp chỗ ở–ngày.

- `ty_le_ngay_san_co` lấy số cặp có `available=True` chia cho số cặp hợp lệ quan sát được.
- `do_phu_lich` là tỷ lệ số cặp hợp lệ quan sát được trên tổng số cặp kỳ vọng. Số cặp kỳ vọng bằng số chỗ ở trong phạm vi đang xét nhân với 90. Với toàn mẫu và các vùng A01–A08, chương trình dùng số chỗ ở được giao. Với từng quận, chương trình dùng số chỗ ở thuộc quận đó và đủ điều kiện phân tích trong bảng listings cùng mốc.

Ví dụ, tại mốc 19/06/2026, nhóm quan sát được **83.853 trên 90.000 cặp kỳ vọng**, đạt độ phủ **93,17%**. Trong số các cặp đã quan sát, có **43.206 cặp sẵn có**, tương ứng tỷ lệ **51,53%**.

Ở dòng tỷ lệ sẵn có, `mau_ky_vong` cho phép tính hai kịch bản biên cho phần lịch chưa quan sát được. Nếu coi mọi cặp thiếu đều không sẵn có, dùng `tu_so / mau_ky_vong`. Nếu coi chúng đều sẵn có, dùng `(tu_so + mau_ky_vong − mau_so) / mau_ky_vong`.

### Trải nghiệm khách và khác biệt giữa các quận

Trong `kpi_llm.csv`, `ty_le_review_tich_cuc` lấy số review gán nhãn `positive` chia cho số review đạt QA và có nhãn cảm xúc hợp lệ. `mau_ky_vong` là số review được chọn vào mẫu trong phạm vi đang xét, trước khi lọc lấy các nhãn dùng được. Lọc `ky_review=tat_ca` để xem kết quả gộp qua các năm, hoặc chọn một năm cụ thể. `snapshot_date` xác định mốc dùng để lấy thông tin khu vực của chỗ ở. `ky_review` ghi năm khách viết đánh giá hoặc `tat_ca`.

`kpi_bat_thuong.csv` giúp nhận diện các quận có giá hoặc lịch khác biệt so với nhóm quận đủ mẫu. Cột `chi_so` phân biệt giá trung vị trên thang log (`log10_gia`), tỷ lệ sẵn có ở mốc cuối (`ty_le_san_co`) và mức thay đổi tỷ lệ sẵn có từ `moc_dau` đến `moc_cuoi` (`thay_doi_san_co`). `gia_tri` là giá trị của chỉ số. `z` là độ lệch chuẩn hóa so với nhóm quận đủ mẫu, còn `z_ben_vung` tính theo trung vị và độ lệch tuyệt đối trung vị (MAD), để trống khi MAD bằng 0. Ba cờ `bat_thuong`, `bat_thuong_z25` và `bat_thuong_ben_vung` lần lượt áp dụng ngưỡng tuyệt đối 2, 2,5 và 3,5. Hai cờ cuối giúp xem kết quả có thay đổi khi tăng ngưỡng hoặc chuyển sang cách tính theo trung vị hay không.

`kpi_so_sanh_quan.csv` có ba dạng dòng. Dùng `phep_so_sanh` để chọn cách đọc `gia_tri`:

- `ty_le_tich_cuc` là tỷ lệ review tích cực của quận tại `khu_vuc_a`.
- `chenh_ty_le_tich_cuc` lấy tỷ lệ review tích cực của quận A trừ tỷ lệ của quận B. Ví dụ, `0.14` là chênh 14 điểm phần trăm. Mỗi quận cần ít nhất `kpi.min_n` chỗ ở có nhãn. Ở dòng chênh lệch, `so_listing` và `so_review` là số chỗ ở và số review tính gộp của hai quận.
- `spearman_gia_va_ty_le_tich_cuc` là tương quan hạng Spearman giữa giá hợp lệ và tỷ lệ review tích cực **của từng chỗ ở** tại mốc tính giá. Dòng này ghi số chỗ ở tham gia, còn hai tên quận và khoảng tin cậy để trống.

Ở các dòng tỷ lệ và chênh lệch, `ci95_lower` và `ci95_upper` là hai cận lấy từ phân vị 2,5% và 97,5% của kết quả lấy mẫu lại. Chương trình dùng bootstrap theo cụm chỗ ở để các review của cùng một chỗ ở luôn đi cùng nhau. `so_lan_bootstrap` và `seed` ghi thiết lập của phép tính.

## Nhãn Gemini, baseline và kết quả chấm

`llm_results.csv` và `baseline_results.csv` trong `data/processed/` có cùng năm cột để ghép theo `review_id`. `sentiment` nhận `positive`, `mixed` hoặc `negative`. `positive_aspects` và `negative_aspects` lưu danh sách khía cạnh khen và chê dưới dạng chuỗi JSON, ví dụ `["sạch sẽ", "vị trí"]`. Gemini ghi mã ngôn ngữ trong `language`, hoặc `und` khi chưa xác định được. Baseline dùng từ khóa tiếng Anh và điền `en` theo quy ước. Bước chấm mặc định chỉ xét cảm xúc và khía cạnh.

Ba tệp còn lại giúp chạy lại và theo dõi quá trình gọi Gemini:

- `llm_cache.jsonl` lưu mỗi kết quả đã kiểm tra trên một dòng. `khoa` được tính từ model, prompt và giới hạn token để tra đúng nhãn đã lưu. Khi cache có đủ nhãn cho mẫu, pipeline dùng lại các nhãn này mà không cần khóa API.
- `llm_results.json` chứa danh sách nhãn trong `results`, kèm tên model, cỡ mẫu thực tế `sample_size` và trạng thái `status`. Nếu còn thiếu kết quả, `failed_review_ids` liệt kê các ID cần kiểm tra lại.
- `llm_usage.csv` ghi các lần gọi Gemini, gồm trạng thái, thời gian tính bằng giây và số token. Dùng tệp này để ước tính chi phí và theo dõi thời gian gọi API.

Bảng `data/samples/nhan_tay.csv` chứa 100 review do nhóm gán nhãn tay làm đáp án. Cờ `human_sample` đánh dấu các review cần chấm, còn bảng nhãn tay cung cấp đáp án theo từng `review_id`. Thư mục `data/samples/mau_nho/` chứa bộ dữ liệu thu gọn của 24 chỗ ở để chạy thử nhanh bước chuẩn bị.

Sau khi chấm, mở `reports/evaluation_metrics.csv` để xem accuracy, macro-F1, F1 theo từng lớp cảm xúc, micro-F1 cho khía cạnh khen/chê và khoảng tin cậy của chênh lệch accuracy giữa Gemini và baseline. Trong ma trận nhầm lẫn `evaluation_confusion.csv`, hàng là nhãn tay và cột là nhãn dự đoán. `evaluation_errors.csv` lưu nội dung từng review kèm các nhãn bị đoán sai, thừa hoặc thiếu để rà soát chi tiết.

## Tìm bảng đứng sau một hình

Các hình trong `figures/` lấy dữ liệu từ những bảng sau:

- **Chỗ ở và giá:** `01_cho_o_theo_quan.png` ghép `kpi_listings.csv` với GeoJSON quận. `04_gia_theo_quan.png` cũng đọc bảng listings KPI. `05_do_nhay_gia_qa.png` lấy các kịch bản giá từ `qa_report.csv`.
- **Lịch:** `02_lich_theo_moc.png` và `03_lich_theo_vung.png` đọc `kpi_calendar.csv`.
- **Review:** `06_review_tich_cuc_llm.png` và `09_review_tich_cuc_theo_nam.png` đọc `kpi_llm.csv`. `07_khia_canh_llm.png` đếm các khía cạnh trong `llm_results.csv`. `08_llm_so_voi_baseline.png` đọc `evaluation_metrics.csv`.
- **Quận bất thường:** `10_bat_thuong_theo_quan.png` đọc các chỉ số và cờ từ `kpi_bat_thuong.csv`.

Để tạo lại các bảng và hình, làm theo hướng dẫn trong README. Với cấu hình London của nhóm, chạy `python run_pipeline.py --config configs/london.yaml`.
