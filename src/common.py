import hashlib
import json
import yaml

from datetime import date
from pathlib import Path

import pandas as pd


THU_MUC_DU_AN = Path(__file__).resolve().parents[1]   # Mọi đường dẫn mặc định tính từ gốc dự án
CAU_HINH_MAC_DINH = THU_MUC_DU_AN / "configs" / "london.yaml"

COT_ASPECT = ["positive_aspects", "negative_aspects"]
COT_NHAN = ["review_id", "sentiment", "positive_aspects", "negative_aspects", "language"]
CAM_XUC = ("positive", "mixed", "negative")
SO_LAN_BOOTSTRAP = 2000   # Số lần lấy mẫu lại theo listing, dùng chung cho đánh giá LLM và so sánh quận

COT_PHAN_CONG = {
    "listings": {"listing_id", "analysis_area"},
    "reviews": {"review_id", "listing_id", "llm_sample", "human_sample"},
    "areas": {"analysis_area", "lon_min", "lat_min", "lon_max", "lat_max"},
}


def doc_cau_hinh(duong_dan_cau_hinh: Path) -> dict:
    """Đọc file cấu hình YAML và kiểm tra các trường cần thiết"""
    with open(duong_dan_cau_hinh, "r", encoding="utf-8-sig") as f:  # utf-8-sig giúp lọc bỏ BOM nếu có trong file YAML
        cau_hinh = yaml.safe_load(f)

    if not isinstance(cau_hinh, dict):
        raise ValueError("Cấu hình phải là một dictionary YAML")

    for key in ("city", "data_root", "currency"):
        gia_tri = cau_hinh.get(key)

        if not isinstance(gia_tri, str) or not gia_tri.strip():
            raise ValueError(f"'{key}' phải là chuỗi không rỗng")

        cau_hinh[key] = gia_tri.strip()

    snapshots = cau_hinh.get("snapshots")

    if not isinstance(snapshots, list) or not snapshots:
        raise ValueError("'snapshots' phải là danh sách không rỗng")

    for index, snapshot in enumerate(snapshots):
        # type(...) is date để chặn cả str lẫn datetime (datetime là lớp con của date).
        if type(snapshot) is not date:
            raise ValueError(
                f"Snapshot '{snapshot}' phải ghi đúng định dạng datetime.date YYYY-MM-DD, "
                f"không phải {type(snapshot).__name__}"
            )

        cau_hinh["snapshots"][index] = snapshot.isoformat()

    if len(set(cau_hinh["snapshots"])) != len(cau_hinh["snapshots"]):
        raise ValueError("'snapshots' có mốc bị trùng")

    assignment = cau_hinh.get("assignment")

    if not isinstance(assignment, dict):
        raise ValueError("'assignment' phải là một dictionary")

    if "dataset_code" not in assignment:
        raise ValueError("YAML thiếu 'dataset_code' trong 'assignment'")

    if not isinstance(assignment["dataset_code"], str) or not assignment["dataset_code"].strip():
        raise ValueError("'dataset_code' trong 'assignment' phải là chuỗi không rỗng")

    assignment["dataset_code"] = assignment["dataset_code"].strip()


    qa = cau_hinh.get("qa")

    if not isinstance(qa, dict):
        raise ValueError("'qa' phải là một dictionary")

    for key in ("price_max_gbp", "min_nights_cap", "room_types",
                "calendar_days", "keys", "coord_shift_max_km"):
        if key not in qa:
            raise ValueError(f"YAML thiếu '{key}' trong 'qa'")

        if key in ("price_max_gbp", "coord_shift_max_km"):
            if type(qa[key]) not in (int, float) or qa[key] <= 0:
                raise ValueError(f"'{key}' trong 'qa' phải là số lớn hơn 0")

        if key in ("min_nights_cap", "calendar_days"):
            if type(qa[key]) is not int or qa[key] <= 0:
                raise ValueError(f"'{key}' trong 'qa' phải là số nguyên dương")

    room_types = qa["room_types"]

    if not isinstance(room_types, list) or not room_types:
        raise ValueError("'room_types' trong 'qa' phải là danh sách không rỗng")



    for index, room_type in enumerate(room_types):
        if not isinstance(room_type, str) or not room_type.strip():
            raise ValueError(f"'{room_type}' trong 'room_types' phải là chuỗi không rỗng")
        room_types[index] = room_type.strip()

    if len(room_types) != len(set(room_types)):
        raise ValueError("'room_types' trong 'qa' có giá trị trùng")
    
    keys = qa["keys"]

    if not isinstance(keys, dict):
        raise ValueError("'keys' trong 'qa' phải là một dictionary")

    for ten_bang in ("listings", "calendar", "reviews"):
        cac_cot_khoa = keys.get(ten_bang)

        if not isinstance(cac_cot_khoa, list) or not cac_cot_khoa:
            raise ValueError(f"'{ten_bang}' trong 'qa.keys' phải là danh sách không rỗng")

        for index, cot_khoa in enumerate(cac_cot_khoa):
            if not isinstance(cot_khoa, str) or not cot_khoa.strip():
                raise ValueError(f"'{cot_khoa}' trong '{ten_bang}' phải là chuỗi không rỗng")
            cac_cot_khoa[index] = cot_khoa.strip()

        cot_id = "review_id" if ten_bang == "reviews" else "listing_id"
        khoa_bat_buoc = {"snapshot_date", cot_id}
        if ten_bang == "calendar":
            khoa_bat_buoc.add("calendar_date")

        if not khoa_bat_buoc.issubset(cac_cot_khoa):
            raise ValueError(f"qa.keys.{ten_bang} cần đủ {sorted(khoa_bat_buoc)}")
        if len(cac_cot_khoa) != len(set(cac_cot_khoa)):
            raise ValueError(f"qa.keys.{ten_bang} không được lặp tên cột")

    kpi = cau_hinh.get("kpi")

    if not isinstance(kpi, dict):
        raise ValueError("'kpi' phải là một dictionary")

    for key in ("area_col", "area_col_assignment", "price_snapshot", "price_stat",
                "calendar_horizon_days", "min_n", "qa_compare"):
        if key not in kpi:
            raise ValueError(f"YAML thiếu '{key}' trong 'kpi'")

        if key in ("area_col", "area_col_assignment", "price_stat"):
            if not isinstance(kpi[key], str) or not kpi[key].strip():
                raise ValueError(f"'{key}' trong 'kpi' phải là chuỗi không rỗng")

            kpi[key] = kpi[key].strip()

        if key in ("calendar_horizon_days", "min_n"):
            if type(kpi[key]) is not int or kpi[key] <= 0:
                raise ValueError(f"'{key}' trong 'kpi' phải là số nguyên dương")

    if kpi["price_stat"] not in ("median", "mean"):
        raise ValueError("'price_stat' trong 'kpi' chỉ được là 'median' hoặc 'mean'")

    if kpi["calendar_horizon_days"] > qa["calendar_days"]:
        raise ValueError("'calendar_horizon_days' trong 'kpi' không được vượt 'calendar_days' trong 'qa'")

    if type(kpi["price_snapshot"]) is date:
        kpi["price_snapshot"] = kpi["price_snapshot"].isoformat()

    if kpi["price_snapshot"] != max(cau_hinh["snapshots"]):
        raise ValueError(
            f"'price_snapshot' trong 'kpi' phải là mốc cuối trong 'snapshots' ({max(cau_hinh['snapshots'])}); "
            "khi đổi mốc chụp hãy sửa cả price_snapshot"
        )

    qa_compare = kpi["qa_compare"]

    if not isinstance(qa_compare, list) or not qa_compare:
        raise ValueError("'qa_compare' trong 'kpi' phải là danh sách không rỗng")

    for index, ten_kpi in enumerate(qa_compare):
        if not isinstance(ten_kpi, str) or not ten_kpi.strip():
            raise ValueError(f"'{ten_kpi}' trong 'qa_compare' phải là chuỗi không rỗng")
        qa_compare[index] = ten_kpi.strip()

    if len(qa_compare) != len(set(qa_compare)):
        raise ValueError("'qa_compare' trong 'kpi' có tên KPI trùng")

    llm = cau_hinh.get("llm")

    if not isinstance(llm, dict):
        raise ValueError("'llm' phải là một dictionary")

    for key in ("provider", "model", "batch_size", "max_tokens", "timeout_giay",
                "so_lan_thu", "cho_giay", "sample_size", "cache"):
        if key not in llm:
            raise ValueError(f"YAML thiếu '{key}' trong 'llm'")

        if key in ("provider", "model", "cache"):
            if not isinstance(llm[key], str) or not llm[key].strip():
                raise ValueError(f"'{key}' trong 'llm' phải là chuỗi không rỗng")

            llm[key] = llm[key].strip()

        if key in ("sample_size", "batch_size", "max_tokens", "timeout_giay", "so_lan_thu"):
            if type(llm[key]) is not int or llm[key] <= 0:
                raise ValueError(f"'{key}' trong 'llm' phải là số nguyên dương")

        if key == "cho_giay" and (type(llm[key]) is not int or llm[key] < 0):
            raise ValueError(f"'{key}' trong 'llm' phải là số nguyên không âm")

    if llm["provider"] != "gemini":
        raise ValueError("'provider' trong 'llm' chỉ được là 'gemini'")

    aspects = llm.get("aspects")

    if not isinstance(aspects, list) or not aspects:
        raise ValueError("'aspects' trong 'llm' phải là danh sách không rỗng")

    for index, aspect in enumerate(aspects):
        if not isinstance(aspect, str) or not aspect.strip():
            raise ValueError(f"'{aspect}' trong 'aspects' phải là chuỗi không rỗng")
        aspects[index] = aspect.strip()

    if len(aspects) != len(set(aspects)):
        raise ValueError("'aspects' trong 'llm' có khía cạnh trùng")

    # type(...) is int để chặn True/False, vì bool là lớp con của int
    if type(cau_hinh.get("seed")) is not int or cau_hinh.get("seed") <= 0:
        raise ValueError("'seed' phải là số nguyên dương")

    download = cau_hinh.get("download")

    if not isinstance(download, dict):
        raise ValueError("'download' phải là một dictionary")

    if "tai_lai" in download and not isinstance(download["tai_lai"], bool):
        raise ValueError("'tai_lai' trong 'download' phải là true hoặc false")

    return cau_hinh


def chuyen_dung_sai(cot: pd.Series) -> pd.Series:
    """Đọc chữ true/false (không phân biệt hoa thường) thành boolean, ô khác để NA"""
    return cot.astype("string").str.strip().str.lower().map({"true": True, "false": False}).astype("boolean")


def la_dung(cot: pd.Series) -> pd.Series:
    """Cờ đọc từ CSV: chỉ true là True, mọi giá trị khác là False"""
    return chuyen_dung_sai(cot).fillna(False).astype(bool)


def chon_cac_moc(cau_hinh: dict, snapshot: str | None = None) -> list[str]:
    """Trả các mốc theo thứ tự thời gian, hoặc đúng một mốc được chọn trong cấu hình"""
    cac_moc = sorted(cau_hinh["snapshots"])
    if snapshot is None:
        return cac_moc
    if snapshot not in cac_moc:
        raise ValueError(f"Snapshot {snapshot} không có trong cấu hình")
    return [snapshot]


def duong_dan_reviews_qa(cau_hinh: dict) -> Path:
    """Bảng review sau QA ở mốc cuối, đầu vào chung của LLM, baseline và đánh giá"""
    return THU_MUC_DU_AN / "data" / "processed" / cau_hinh["city"] / max(cau_hinh["snapshots"]) / "reviews_qa.csv"


def kiem_tra_id_phan_cong(cac_id: pd.Series, ten_cot: str) -> None:
    """Dùng cùng quy tắc ID cho cả bộ phân công và CSV được đọc riêng"""
    if cac_id.empty or not cac_id.is_unique or cac_id.isna().any() or cac_id.str.strip().eq("").any():
        raise ValueError(f"Phân công có {ten_cot} rỗng hoặc trùng")


def kiem_tra_phan_cong_review(phan_cong: pd.DataFrame) -> tuple[int, int]:
    """Kiểm ID và cờ mẫu, trả số lượng mẫu mà không sửa bảng đầu vào"""
    kiem_tra_id_phan_cong(phan_cong["review_id"], "review_id")
    co_mau = {}
    for cot in ["llm_sample", "human_sample"]:
        co_mau[cot] = chuyen_dung_sai(phan_cong[cot])
        if co_mau[cot].isna().any():
            raise ValueError(f"{cot} chỉ được chứa True/False (không phân biệt hoa thường)")
    if (co_mau["human_sample"] & ~co_mau["llm_sample"]).any():
        raise ValueError("Có review nhãn tay nằm ngoài mẫu LLM")
    return int(co_mau["llm_sample"].sum()), int(co_mau["human_sample"].sum())


def doc_phan_cong(thu_muc_phan_cong: Path, cau_hinh: dict) -> tuple[dict[str, pd.DataFrame], dict]:
    """Đọc và kiểm phân công, giữ nguyên các cột ở dạng chuỗi nguồn"""
    with (thu_muc_phan_cong / "manifest.json").open("r", encoding="utf-8-sig") as f:
        thong_tin = json.load(f)
    if (thong_tin["class"], thong_tin["group"]) != ("UET.DSE2049 7", "15"):
        raise ValueError("Phân công không thuộc lớp và nhóm 15")
    if (thong_tin["scope"]["Thành phố"].lower() != cau_hinh["city"].lower()
            or thong_tin["scope"]["Tiền tệ"] != cau_hinh["currency"]
            or thong_tin["code"] != cau_hinh["assignment"]["dataset_code"]):
        raise ValueError("Cấu hình khác phạm vi phân công")

    phan_cong = {}
    for ten_bang, cot_can_co in COT_PHAN_CONG.items():
        duong_dan = thu_muc_phan_cong / f"{ten_bang}.csv"
        bang = pd.read_csv(duong_dan, dtype="string", keep_default_na=False)
        if not cot_can_co.issubset(bang.columns):
            raise ValueError(f"{duong_dan.name} thiếu cột: {sorted(cot_can_co - set(bang.columns))}")
        phan_cong[ten_bang] = bang
    listings, reviews, vung = phan_cong["listings"], phan_cong["reviews"], phan_cong["areas"]
    kiem_tra_id_phan_cong(listings["listing_id"], "listing_id")
    so_mau_llm, so_nhan_tay = kiem_tra_phan_cong_review(reviews)
    # Số lượng kỳ vọng đọc từ manifest đi kèm bộ phân công
    for bang, cot_id, so_id in [(listings, "listing_id", thong_tin["listings"]),
                                (reviews, "review_id", thong_tin["reviews"])]:
        if len(bang) != so_id:
            raise ValueError(f"Phân công cần {so_id} {cot_id} khác nhau, không rỗng")
    if so_mau_llm != thong_tin["llm_sample"] or so_nhan_tay != thong_tin["human_sample"]:
        raise ValueError(f"Cần đúng {thong_tin['llm_sample']} mẫu LLM và {thong_tin['human_sample']} nhãn tay")
    if not reviews["listing_id"].isin(listings["listing_id"]).all():
        raise ValueError("Review phân công trỏ tới listing ngoài nhóm")
    if (not vung["analysis_area"].is_unique or vung["analysis_area"].str.strip().eq("").any()
            or not listings["analysis_area"].isin(vung["analysis_area"]).all()):
        raise ValueError("Vùng phân công bị thiếu hoặc trùng")
    cot_bien = ["lon_min", "lat_min", "lon_max", "lat_max"]
    # Đọc số trên bản tạm để kiểm biên, bảng trả về vẫn giữ chuỗi nguồn
    bien_vung = vung[cot_bien].apply(pd.to_numeric, errors="raise")
    bien_dung = (
        bien_vung["lon_min"].between(-180, 180) & bien_vung["lon_max"].between(-180, 180)
        & bien_vung["lat_min"].between(-90, 90) & bien_vung["lat_max"].between(-90, 90)
        & bien_vung["lon_min"].lt(bien_vung["lon_max"]) & bien_vung["lat_min"].lt(bien_vung["lat_max"])
    )
    if not bien_dung.fillna(False).all():
        raise ValueError("Biên vùng phải hữu hạn, đúng miền và min < max")
    return phan_cong, thong_tin



def digest(gia_tri: object) -> str:
    """Tính mã băm SHA-256 của một giá trị JSON (dùng làm khóa cache)

    sort_keys=True để cùng một dict luôn cho cùng một mã, không phụ thuộc thứ tự khóa
    """
    noi_dung = json.dumps(gia_tri, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(noi_dung.encode("utf-8")).hexdigest()


def write_json(duong_dan_file: Path, gia_tri: object) -> None:
    """Ghi JSON UTF-8 qua tệp tạm rồi thay thế, để không bao giờ còn lại tệp ghi dở"""
    duong_dan_file = Path(duong_dan_file)
    duong_dan_file.parent.mkdir(parents=True, exist_ok=True)
    duong_dan_tam_thoi = duong_dan_file.with_suffix(duong_dan_file.suffix + ".tmp")

    # allow_nan=False: NaN không phải JSON hợp lệ nên báo lỗi thay vì ghi ra
    duong_dan_tam_thoi.write_text(
        json.dumps(gia_tri, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
        newline="\n",
    )
    duong_dan_tam_thoi.replace(duong_dan_file)


def write_csv(duong_dan_file: Path, du_lieu: pd.DataFrame) -> None:
    """Ghi CSV UTF-8, không ghi index, xuống dòng '\\n' để mã băm giống nhau trên Windows và Linux"""
    duong_dan_file = Path(duong_dan_file)
    duong_dan_file.parent.mkdir(parents=True, exist_ok=True)
    # Ghi qua tệp tạm rồi thay thế như write_json, không mở đè tệp đang được chương trình khác đọc
    duong_dan_tam_thoi = duong_dan_file.with_suffix(duong_dan_file.suffix + ".tmp")
    du_lieu.to_csv(duong_dan_tam_thoi, index=False, encoding="utf-8", lineterminator="\n")
    duong_dan_tam_thoi.replace(duong_dan_file)


def doc_mau_llm(duong_dan: Path, sample_size: int) -> pd.DataFrame:
    """Lấy mẫu đã chọn và dùng cờ đủ điều kiện nếu bảng đã qua QA"""
    if not duong_dan.is_file():
        raise FileNotFoundError(f"Chưa có {duong_dan}. Chạy prepare và QA trước")

    du_lieu = pd.read_csv(duong_dan, dtype=str, keep_default_na=False)
    cot_can_co = {"review_id", "comments", "llm_sample"}
    if not cot_can_co.issubset(du_lieu.columns):
        raise ValueError(f"{duong_dan.name} thiếu cột {sorted(cot_can_co - set(du_lieu.columns))}")

    co_mau = chuyen_dung_sai(du_lieu["llm_sample"])
    if co_mau.isna().any():
        raise ValueError("Cột llm_sample chỉ được chứa True hoặc False")

    mau = du_lieu.loc[co_mau.astype(bool)]
    cac_id = mau["review_id"]
    if mau.empty or len(mau) > sample_size or not cac_id.is_unique or cac_id.str.strip().eq("").any():
        raise ValueError(f"Mẫu LLM cần từ 1 đến {sample_size} review ID duy nhất và không rỗng")

    if "du_dieu_kien_llm" in mau:
        khong_dat = ~la_dung(mau["du_dieu_kien_llm"])
    else:
        khong_dat = mau["comments"].str.strip().eq("")
    mau = mau.loc[~khong_dat]

    # Mốc khác có thể mất một phần review được chọn, vẫn chạy trên phần còn lại và báo rõ
    if mau.empty:
        raise ValueError("Không còn review nào trong mẫu LLM đủ điều kiện")
    if len(mau) < sample_size:
        print(f"[CẢNH BÁO] Mẫu LLM còn {len(mau)}/{sample_size} review đủ điều kiện", flush=True)

    return mau[["review_id", "comments"]].reset_index(drop=True)


def ghi_nhan_csv(duong_dan: Path, ket_qua: pd.DataFrame) -> None:
    """Ghi hai cột aspect thành danh sách JSON trong CSV"""
    du_lieu = ket_qua[COT_NHAN].copy()
    for cot in COT_ASPECT:
        du_lieu[cot] = du_lieu[cot].map(lambda danh_sach: json.dumps(danh_sach, ensure_ascii=False))
    write_csv(duong_dan, du_lieu)
