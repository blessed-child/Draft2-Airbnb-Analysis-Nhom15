# Inside Airbnb London (Nhóm 15)

**Môn học:** Lập trình xử lý dữ liệu (UET.DSE2049), học kỳ 1, năm học 2026–2027.

**Đề bài chính thức:** [Bài tập lớn Inside Airbnb](https://courses.iaidev.com/programming-for-data-processing/2627-1/projects/project_airbnb.html).

Nhóm phân tích giá niêm yết, mức độ sẵn có và trải nghiệm khách tại London cho một hiệp hội du lịch giả định. Xem [báo cáo PDF](reports/report.pdf), [từ điển dữ liệu](reports/tu_dien_du_lieu.md) và [khai báo sử dụng AI](AI_USAGE.md).

## Thông tin nhóm

- **Mã lớp:** UET.DSE2049 7
- **Tên/mã nhóm:** Nhóm 15
- **Thành phố được phân công:** London, United Kingdom
- **Tiền tệ:** GBP
- **Mã dữ liệu:** DSE2049-C07-G15-london
- **Bên đặt hàng phân tích:** Hiệp hội du lịch quan tâm đến thị trường lưu trú Airbnb tại London; đây là vai trò đặt hàng giả định trong bài tập, được nhóm chọn ngày 15/10/2026.
- **Hướng phân tích:** giá niêm yết, mức độ sẵn có của chỗ ở và trải nghiệm khách, so sánh theo khu vực và bốn snapshot. Bốn câu hỏi phân tích và bảy KPI được trình bày trong `reports/report.pdf` và `reports/tu_dien_du_lieu.md`.
- **Bốn mốc dữ liệu:** 2025-09-14, 2025-12-13, 2026-03-21, 2026-06-19.

| Họ tên | MSSV | GitHub username | Công việc phụ trách |
|---|---|---|---|
| Nguyễn Xuân Phú | 25022978 | Xuan-Phu-2410 | Nhóm trưởng; lập repo, `.gitignore`, môi trường Python và `requirements.txt`; chuẩn bị listings và calendar (`prepare.py`), tích hợp chuẩn bị dữ liệu với QA |
| Vũ Trung Hiếu | 25024107 | Vuhieu2011uet | Hoàn thiện luồng chuẩn bị listings, calendar, reviews trong `prepare.py`; chỉnh `qa.py` |
| Đỗ Minh Trí | 25023059 | KazinMintori | Tải dữ liệu và cấu hình (`download.py`, YAML, `common.py`); notebook khảo sát; QA, KPI, LLM, baseline, đánh giá, hình, `run_pipeline.py`; báo cáo |
| Trần Ngọc Tâm | 25023022 | blessed-child | Chuẩn bị dữ liệu trong `prepare.py` |
| Vương Anh Đức | 25022838 | lil-vad | Xử lý listings trong `prepare.py` |

Phân công trên tổng hợp từ lịch sử commit. Ngoài phần chính, mỗi thành viên gán 20 trong 100
nhãn tay (cột "Người phụ trách" trong `data/samples/nhan_tay.csv`) và chịu trách nhiệm giải
thích được toàn bộ sản phẩm của nhóm.

### Phạm vi dữ liệu được giao

Lọc danh sách phân công theo đúng lớp UET.DSE2049 7 và nhóm 15:

- 1.000 listing được chỉ định trong sheet Listing.
- Calendar được lọc theo listing_id của các listing được giao.
- 5.000 review được chỉ định trong sheet Review.
- Mẫu LLM gồm 1.000 review được đánh dấu trong cột Mẫu LLM.
- Bộ gán nhãn tay gồm 100 review được đánh dấu trong cột Nhãn tay,
  nằm trong mẫu LLM. Các thành viên phải tự quyết định nhãn.
- Tám vùng phân tích A01–A08 theo sheet Vùng; đây là các vùng
  hình chữ nhật, không phải ranh giới hành chính.

Theo hướng dẫn phân công, cùng danh sách listing và review được
sử dụng qua bốn snapshot. Review xuất hiện lại ở nhiều snapshot
không được coi là các ý kiến độc lập mới.

Theo lưu ý và tin nhắn giảng viên nhóm cung cấp ngày 15/10/2026,
chỉ dùng `price` của listings ở mốc cuối `2026-06-19` để phân tích.
Không so sánh giá qua bốn mốc, không dùng giá calendar và không xin
cấp lại dữ liệu chỉ vì giá ở các mốc trước bị rỗng. Mốc cuối có đúng
20 listing thiếu giá theo số tham chiếu của phân công.

Kết quả phân tích cần ghi rõ phạm vi là tập dữ liệu được giao
của London; không mặc nhiên đại diện cho toàn bộ thành phố.

### Các lựa chọn đã chốt

- Giữ cả `analysis_area` (vùng A01–A08 của bài tập) và `neighbourhood_cleansed` (quận nguồn);
  KPI tính cho cả hai hệ vùng, không ánh xạ hệ này sang hệ kia.
- Giá chỉ phân tích ở mốc cuối 2026-06-19 theo hướng dẫn giảng viên.
- Để thử dữ liệu ở mốc khác, cập nhật `snapshots` và `kpi.price_snapshot` trong YAML rồi chạy riêng
  các bước tải, Prepare và QA. Prepare cảnh báo nếu mốc mới có ít ID hơn phân công. QA ghi danh sách ID
  thiếu trong quy tắc `thieu_id_phan_cong`. Nếu một bảng ở mốc đó không có ID nào thuộc phân công,
  Prepare báo lỗi.

## Cài đặt và chạy

- **Phiên bản Python:** 3.13.16, ghi trong `.python-version`.
- **Môi trường:** mỗi thành viên tự tạo `.venv` bằng Python 3.13.16 và cài đúng `requirements.txt` (ghim `==` đủ để chạy quy trình). `requirements-dev.txt` chỉ thêm Jupyter và seaborn để mở notebook khảo sát, quy trình chính không cần.
- **Cấu hình thành phố, snapshot và tham số:** `configs/london.yaml`. Mã nguồn không ghi cứng thành phố hay mốc chụp.
- **Biến môi trường chứa API key:** `GEMINI_API_KEY` (xem `.env.example`). Chỉ cần khi muốn gọi lại Gemini; tệp `.env` không tự được nạp.
- **Một lệnh chạy toàn bộ quy trình** sau khi cài môi trường theo hướng dẫn bên dưới.

  ```powershell
  .\.venv\Scripts\python.exe -X utf8 run_pipeline.py --config configs/london.yaml
  ```

  Lần đầu tải khoảng 1,47 GB vào `data/raw/`, gồm listings, calendar, reviews và GeoJSON ở mỗi mốc.
  Khi `download.tai_lai` là `false`, chương trình kiểm tra và dùng lại các tệp đã có.
  Với dữ liệu London hiện tại, `data/processed/llm_cache.jsonl` đã có nhãn cho đủ 1.000 review,
  nên lệnh chạy được **không cần khóa API**. Thêm `--skip-llm` để chạy ở chế độ chỉ đọc cache.
  Chế độ này vẫn tạo kết quả LLM từ cache và trả mã lỗi 1 nếu thiếu nhãn.
  `-X utf8` giúp PowerShell hiển thị tiếng Việt đúng mã hóa.
- **Các tệp kết quả để đối chiếu** (mô tả cột trong `reports/tu_dien_du_lieu.md`):

  | Bước | Tệp |
  |---|---|
  | Prepare | `listings_assigned.csv`, `calendar_assigned.csv`, `reviews_assigned.csv` trong từng mốc dưới `data/processed/london/` |
  | QA | `reports/qa_report.csv` và các bảng `listings_qa.csv`, `calendar_qa.csv`, `reviews_qa.csv` ở từng mốc |
  | KPI | `data/processed/kpi_listings.csv`, `kpi_calendar.csv`, `kpi_llm.csv`; quận bất thường `kpi_bat_thuong.csv`; khoảng tin cậy bootstrap theo listing và Spearman giá với tỷ lệ tích cực `kpi_so_sanh_quan.csv` (2.000 lần, seed trong YAML) |
  | LLM | `data/processed/llm_cache.jsonl`, `llm_results.csv`, `llm_results.json`, `llm_usage.csv` |
  | Baseline và đánh giá | `data/processed/baseline_results.csv`; `reports/evaluation_metrics.csv`, `evaluation_confusion.csv`, `evaluation_errors.csv` |
  | Hình | `figures/01_…` đến `figures/10_…` |
  | Tài liệu đi kèm bản nộp | `reports/report.pdf`, `reports/tu_dien_du_lieu.md`, `AI_USAGE.md` |

  Các bảng trung gian trong `data/processed/london/` (lịch khoảng 47 MB mỗi mốc) bị `.gitignore` chặn để
  phần commit của `data/processed/` dưới 50 MB.

- **Mẫu nhỏ để thử Prepare.** `data/samples/mau_nho/` chứa dữ liệu chỗ ở, lịch và review của cùng
  24 listing ở cả bốn mốc. Mỗi vùng A01–A08 có ba listing. Tệp review đã bỏ ID và tên người viết.
  Dùng bộ mẫu này để thử Prepare mà không cần tải dữ liệu gốc.

  ```powershell
  .\.venv\Scripts\python.exe -X utf8 -m src.prepare --raw-dir data/samples/mau_nho --output-dir "$env:TEMP\airbnb-mau-nho"
  ```

  Prepare ghi các bảng vào thư mục tạm và báo thiếu 976 listing so với phân công 1.000 listing.
  `data/samples/nhan_tay.csv` là bộ 100 nhãn tay dùng riêng ở bước đánh giá trên dữ liệu đầy đủ.

### Chuẩn bị môi trường trên Windows

Mở PowerShell tại thư mục gốc của bản clone.

1. Kiểm tra Python dùng để tạo môi trường:

   ```powershell
   python --version
   ```

   Chỉ tiếp tục khi kết quả là Python 3.13.16. Nếu lệnh không tồn tại hoặc
   trỏ tới phiên bản khác, xác định đường dẫn Python 3.13.16 trên máy rồi
   dùng đường dẫn đó thay cho `python`.

2. Nếu chưa có `.venv`, tạo môi trường:

   ```powershell
   python -m venv .venv
   ```

3. Kiểm tra môi trường vừa tạo:

   ```powershell
   .\.venv\Scripts\python.exe --version
   .\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
   .\.venv\Scripts\python.exe -m pip --version
   ```

   Python cần là 3.13.16; đường dẫn Python và pip cần nằm trong `.venv`
   của bản clone trên máy mình.

4. Cài các thư viện đã ghim cho toàn bộ quy trình:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

Mỗi người tự tạo môi trường; không sao chép `.venv` giữa các máy và
không commit thư mục này. `.python-version` chỉ ghi phiên bản,
không tự cài Python.

Trong lần kiểm tra ngày 21/11/2026, `pip check` xác nhận các gói trong
`requirements.txt` tương thích trên môi trường mới dùng Python 3.13.16.
Quy trình chạy hết khi không đặt `GEMINI_API_KEY`.

## Nộp bài

Hạn nộp bản cuối là **23:59 Chủ nhật, 22/11/2026**. Kiểm tra bản nộp từ một clone mới
theo hướng dẫn cài đặt, chạy một lệnh và đối chiếu các bảng, hình với báo cáo.
Sau khi cập nhật báo cáo và đẩy commit cuối, tạo tag theo đề bài.

```bash
git tag final
git push origin final
```

Ghi commit SHA được nộp vào báo cáo. Thời hạn, cách đăng ký và lịch vấn đáp xem tại đề bài và Canvas.

## Chạy riêng từng bước

`run_pipeline.py` gọi lần lượt download → prepare → qa → llm → baseline → kpi → evaluate → viz.
Mỗi mô-đun cũng chạy riêng được từ thư mục gốc. Các lệnh dưới đây dùng `python` của `.venv`.
Nếu chưa kích hoạt môi trường, thay `python` bằng `./.venv/Scripts/python.exe` trên Windows.
Bộ ID và cờ chọn mẫu nằm trong `data/assignment/`. Nếu chưa có dữ liệu thô,
chạy `python -X utf8 -m src.download`.

```powershell
python -X utf8 -m src.prepare --table listings
python -X utf8 -m src.prepare --table calendar
python -X utf8 -m src.prepare --table reviews
python -X utf8 -m src.qa --config configs/london.yaml
python -X utf8 -m src.kpi --config configs/london.yaml
```

- `--table listings` xuất `listings_assigned.csv` theo mốc và gộp các mốc trong YAML thành `listings_all_snapshots.csv`.
- `--table calendar` lọc lịch theo listing ID, chuẩn hóa ngày và trạng thái, rồi ghép hai cột vùng.
  Mỗi mốc chỉ có một đầu ra lịch từ Prepare là `calendar_assigned.csv`. Đây là tệp QA đọc.
- `--table reviews` lọc và ghép cờ review, xuất `reviews_assigned.csv` theo mốc,
  cùng `reviews_unique.csv` và `review_appearances.csv`.
- Với tọa độ, số đêm tối thiểu và số lượt review của listings, Prepare giữ dòng và để trống ô
  không đọc được thành số. Giá trị số lẻ vẫn được giữ để QA kiểm tra điều kiện số nguyên.
  Tọa độ thiếu, sai kiểu hoặc ngoài miền nhận cờ `qa_toa_do_sai` và `du_dieu_kien_ban_do=False`.
  Với giá, `price_raw` giữ chuỗi nguồn để QA phân biệt giá sai kiểu với giá thiếu.
  Prepare vẫn báo lỗi khi khóa ghép hoặc cấu trúc lịch không hợp lệ.
- QA thêm cờ vào `listings_qa.csv`, `calendar_qa.csv`, `reviews_qa.csv` và ghi
  `reports/qa_report.csv`. Quy tắc ghi điều kiện, lý do, hành động và số ảnh hưởng.
  `--snapshot` ghi báo cáo riêng `qa_report_<snapshot>.csv`.
- Công thức và so sánh KPI trước/sau nằm trong `src/kpi.py`. Cùng công thức
  được dùng trước và sau QA, kèm số quan sát thực tế. Các giá dương hữu hạn
  bị cờ ngoại lai vẫn vào KPI chính. Hai kịch bản bỏ giá theo ngưỡng hoặc IQR
  đo mức thay đổi của trung vị và số quan sát.

Ba bảng `data/processed/kpi_listings.csv`, `kpi_calendar.csv` và `kpi_llm.csv`
ghi `snapshot_date`, phạm vi, giá trị, đơn vị và cỡ mẫu. Phạm vi `city` là
toàn bộ mẫu phân công của London. `neighbourhood` dùng `neighbourhood_cleansed`
và `analysis_area` dùng vùng A01–A08. Cột `du_mau` áp dụng ngưỡng `kpi.min_n`
cho số listing đóng góp vào từng giá trị.

| KPI | Hiệp hội du lịch dùng để | Công thức và đơn vị |
|---|---|---|
| Số listing | Xem quy mô mẫu theo khu và mốc | Đếm listing đủ điều kiện phân tích, đơn vị listing |
| Tỷ lệ nguyên căn | Xem cơ cấu chỗ ở | Listing `Entire home/apt` chia số listing có loại phòng hợp lệ, tỷ lệ 0–1 |
| Giá trung vị | So sánh mức giá điển hình | Trung vị `price_gbp_kpi` ở mốc cuối, GBP/đêm, kèm số giá hợp lệ |
| Giá trung vị nguyên căn | So giá giữa các khu khi cùng loại chỗ ở | Như giá trung vị, chỉ listing `Entire home/apt`, GBP/đêm |
| Tỷ lệ ngày sẵn có | So sánh mức sẵn có của chỗ ở | Cặp listing–ngày `True` chia số cặp hợp lệ quan sát được trong 90 ngày từ snapshot, tỷ lệ 0–1 |
| Độ phủ lịch | Kiểm mức đầy đủ của tỷ lệ sẵn có | Cặp hợp lệ trong cửa sổ chia số listing kỳ vọng nhân số ngày cửa sổ, tỷ lệ 0–1. Kỳ vọng dùng danh sách giao cho toàn mẫu và vùng A, dùng listings có quận tại mốc cho từng quận |
| Tỷ lệ review tích cực | Xem trải nghiệm khách theo khu và năm viết | Review nhãn `positive` chia số review có nhãn hợp lệ trên mẫu được giao, tỷ lệ 0–1. Ghi số mẫu kỳ vọng và số đã gán nhãn |

KPI lịch dùng cửa sổ `[snapshot, snapshot + calendar_horizon_days)`.
`available=False` vẫn được tính vào mẫu số và chỉ cho biết ngày không sẵn có.
KPI LLM đếm mỗi review một lần, nhóm thời gian theo năm viết (`ky_review`).
`snapshot_date` của KPI LLM chỉ mốc tham chiếu vùng. Nếu chưa có `llm_results.csv`,
giá trị được để trống và ghi trạng thái thiếu nhãn. Sau khi chạy LLM, chạy lại KPI
để cập nhật bảng này.

Dòng `ty_le_ngay_san_co` ghi thêm `mau_ky_vong` (số listing kỳ vọng × 90 ngày) để tính khoảng
độ nhạy khi coi toàn bộ cặp listing–ngày thiếu là bận hoặc là trống.

Notebook khảo sát của nhóm nằm trong `notebooks/khao_sat_du_lieu/`; đây là phần khám phá,
không thuộc quy trình chính.

## Chạy phần LLM bằng Gemini

`src/llm.py` chỉ gọi Gemini, dùng `model` trong `configs/london.yaml`.
Không gửi tham số điều khiển thinking. API có thể trả token suy nghĩ theo mặc định của model;
chương trình ghi riêng số này trong usage.

Gemini và baseline cùng đọc `reviews_qa.csv` của mốc cuối trong YAML. Với cấu hình hiện tại,
tệp nằm tại `data/processed/london/2026-06-19/reviews_qa.csv`. Hai phương pháp dùng các review có
cả `llm_sample=True` và `du_dieu_kien_llm=True`, mỗi ID được xử lý một lần.
`llm.sample_size` là cỡ mẫu dự kiến và giới hạn số review được chọn. Nếu chỉ còn 998 trong
1.000 review đạt QA, chương trình cảnh báo và xử lý 998 review.
Nếu không còn review nào đủ điều kiện, chương trình báo lỗi. Khi chạy bằng cache, mỗi review
được giữ lại vẫn cần có nhãn tương ứng trong cache.

Sau khi chạy QA, dùng hai lệnh dưới đây để tạo lại kết quả Gemini từ cache và chạy baseline.
Cả hai chạy được khi không đặt khóa API.

```powershell
python -X utf8 -m src.llm --config configs/london.yaml --skip-llm
python -X utf8 -m src.baseline --config configs/london.yaml
```

Khi cần gọi Gemini để thử hoặc bổ sung nhãn còn thiếu, đặt khóa API trong phiên PowerShell.

```powershell
$env:GEMINI_API_KEY = '<your-key>'
python -X utf8 -m src.llm --gioi-han 2 --output-dir "$env:TEMP\airbnb-llm-thu"
python -X utf8 -m src.llm --config configs/london.yaml
```

- `--gioi-han N` chạy thử N review đầu. Kết quả mang tên `llm_results_thu`, không đè bản đầy đủ.
- `--input <path>` dùng bảng review ở đường dẫn khác thay cho `reviews_qa.csv` mặc định.
- `--output-dir <path>` chuyển cả kết quả, cache và usage sang thư mục đó.
  Khi không dùng tùy chọn này, cache theo đường dẫn trong YAML, kết quả nằm trong `data/processed/`.
- `--skip-llm` chỉ dùng cache, không cần key và không gọi API. Thiếu cache thì báo lỗi và trả mã thoát 1.
- Chạy lại bình thường sẽ dùng cache và chỉ gọi phần còn thiếu. Đổi model, prompt, aspect,
  nội dung review hoặc giới hạn token sẽ làm khóa cache thay đổi.

Các tệp đầu ra:

| Tệp | Nội dung |
|---|---|
| `llm_cache.jsonl` | Mỗi dòng là một kết quả đã kiểm tra, kèm khóa cache và model thực tế. Ghi qua tệp tạm sau mỗi phản hồi hợp lệ. |
| `llm_results.csv` | Một dòng mỗi review, gồm năm trường nhãn; hai cột aspect là chuỗi JSON. Model được ghi trong JSON và cache. |
| `llm_results.json` | Nhãn dạng list, `status`, số mẫu và `failed_review_ids`. |
| `llm_usage.csv` | Ghi từng lần gọi SDK, gồm cả lần lỗi. Ô token để trống nếu API không trả số liệu. Lượt chỉ đọc cache không thêm dòng. |

`batch_size`, `max_tokens`, `timeout_giay`, `so_lan_thu`, `cho_giay` được đọc từ YAML.
Gemini SDK tự thử lại lỗi dịch vụ tạm thời. Khi JSON lỗi hoặc bị cắt, chương trình
chia batch. Phần hợp lệ được lưu vào cache ngay, phần thiếu được gửi tiếp trong tối đa
bảy lượt gọi SDK kể cả lượt đầu của mỗi batch. Nếu vẫn thiếu ID, chương trình ghi
`incomplete`, liệt kê ID thiếu và thoát với mã lỗi 1.

Baseline xuất `data/processed/baseline_results.csv` cùng năm cột với Gemini.
Đối chứng dùng từ khóa tiếng Anh theo vế và xử lý phủ định trong ba từ liền trước.
Toàn bộ thao tác chạy trên cả cột bằng `str.split`, `explode`, `groupby` và `np.select`,
không duyệt từng review.
Baseline mặc định điền `en`; đây là quy ước của đối chứng từ khóa.

### Đánh giá trên nhãn tay

Xuất tab **Gán nhãn** ra CSV, giữ nguyên `review_id` dạng văn bản. Lưu tại
`data/samples/nhan_tay.csv` hoặc truyền đường dẫn qua `--human-labels`.
Giữ các cột `sentiment`, `positive_aspects`, `negative_aspects`, `language`.
Ô aspect có thể chứa danh sách JSON hoặc các mục ngăn cách bằng dấu phẩy.
Để trống ô aspect nếu người gán đã xác nhận không có khía cạnh tương ứng.

```powershell
python -X utf8 -m src.evaluate --config configs/london.yaml
python -X utf8 -m src.kpi --config configs/london.yaml
```

`evaluate.py` chấm những review có cả `human_sample=True` và `du_dieu_kien_llm=True`.
Mỗi ID trong tập chấm cần có nhãn tay và dự đoán của cả hai phương pháp.
`reports/evaluation_metrics.csv` lưu accuracy và macro-F1 cảm xúc, micro-F1 khía cạnh
khen/chê và khoảng bootstrap 95% cho chênh lệch accuracy. Bootstrap lấy lại các
listing, giữ cùng nhau hai dự đoán trên mỗi review và các review cùng chỗ ở.
Thực hiện 2.000 lượt theo `seed` trong YAML. Khoảng này mô tả phép so sánh trên
mẫu nhãn tay được phân công.
`evaluation_confusion.csv` lưu số lượng theo cặp nhãn, còn `evaluation_errors.csv`
ghi các review sai cảm xúc hoặc thừa/thiếu aspect để đọc lại. Chỉ bật
`--danh-gia-ngon-ngu` khi cột ngôn ngữ đã được xác minh từ nội dung review.

### Ước tính chi phí Gemini

Lấy `llm_usage.csv` của một lượt chạy mẫu đầy đủ từ cache trống. Cộng `prompt_tokens`
cho đầu vào và `output_tokens + thinking_tokens` cho phần sinh ra. Nhân từng tổng
với [đơn giá Standard của Gemini](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite)
theo triệu token rồi chia số review đã xử lý. Nhân chi phí bình quân với tổng review
toàn London trong **một** snapshot. Notebook `04_reviews` ghi 2.241.353 review ở
2026-06-19. Cách tính giả định mức token trên mỗi review tương tự mẫu, chưa trừ
giảm giá cache và không cộng bốn snapshot có review xuất hiện lại.

Kết quả với `llm_usage.csv` đã commit: 10 lượt gọi thành công cho 1.000 review dùng 88.645 token vào
và 86.539 token ra (không có token suy nghĩ). Với đơn giá 0,30 USD/triệu token vào và 2,50 USD/triệu
token ra, mẫu tốn khoảng 0,243 USD, tức khoảng 544,5 USD cho 2.241.353 review của London.
