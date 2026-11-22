import json
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from .common import CAU_HINH_MAC_DINH, THU_MUC_DU_AN, chon_cac_moc, chuyen_dung_sai, doc_cau_hinh, doc_phan_cong
from .common import write_csv as ghi_csv
from .kpi import so_sanh_kpi_truoc_sau


COT_CAN_KIEM = {
    "listings": {"room_type", "latitude", "longitude", "price_raw", "price_gbp",
                 "minimum_nights", "number_of_reviews", "analysis_area", "neighbourhood_cleansed"},
    "calendar": {"calendar_date", "available", "analysis_area", "neighbourhood_cleansed"},
    "reviews": {"listing_id", "date", "comments", "llm_sample", "human_sample"},
}

TEN_TEP_DAU_VAO = {
    "listings": "listings_assigned.csv",
    "calendar": "calendar_assigned.csv",
    "reviews": "reviews_assigned.csv",
}


def dong_bao_cao(moc, bang, ten, dieu_kien, ly_do, hanh_dong, so_dong, mau_so,
                *, don_vi="dong", trang_thai=None, pham_vi="trong_moc", snapshot_truoc="", **bo_sung):
    return {
        "snapshot_date": moc, "snapshot_truoc": snapshot_truoc, "bang": bang, "pham_vi": pham_vi,
        "quy_tac": ten, "dieu_kien": dieu_kien, "ly_do": ly_do, "hanh_dong": hanh_dong,
        "so_anh_huong": so_dong, "mau_so": mau_so, "don_vi": don_vi,
        "ty_le": so_dong / mau_so if mau_so and so_dong is not None else None,
        "trang_thai": trang_thai or ("can_xem_lai" if so_dong else "dat"),
        "kpi_ten": "", "kpi_truoc": None, "kpi_sau": None, "n_truoc": None, "n_sau": None,
        "don_vi_kpi": "", **bo_sung,
    }


def la_gia_tri_thieu(cot: pd.Series) -> pd.Series:
    return cot.astype("string").fillna("").str.strip().str.lower().isin({"", "none", "nan", "<na>", "null", "n/a"})


def kiem_tra_cau_truc(du_lieu: pd.DataFrame, ten_bang: str, khoa: list[str]) -> None:
    if du_lieu.columns.duplicated().any():
        raise ValueError(f"Bảng {ten_bang} có tên cột trùng")

    cot_thieu = (set(khoa) | COT_CAN_KIEM[ten_bang]) - set(du_lieu.columns)
    if cot_thieu:
        raise ValueError(f"Bảng {ten_bang} thiếu cột {sorted(cot_thieu)}. Kiểm tra đầu ra của prepare.py")


# Mỗi quy tắc dùng cùng cờ cho bảng dữ liệu và số đếm trong báo cáo
def ghi_cac_co(du_lieu, bao_cao, moc, bang, quy_tac, **pham_vi):
    cot_id = "review_id" if bang == "reviews" else "listing_id"
    for ten, co, dieu_kien, ly_do, hanh_dong, *tuy_chon in quy_tac:
        co = co.fillna(False).astype(bool)
        du_lieu[f"qa_{ten}"] = co
        them = tuy_chon[0].copy() if tuy_chon else {}
        mau_so = them.pop("mau_so", len(du_lieu))
        so_dong = int(co.sum()) if them.get("trang_thai") != "khong_du_mau" else None
        id_anh_huong = du_lieu.loc[co, cot_id].dropna().unique().tolist()
        bao_cao.append(dong_bao_cao(
            moc, bang, ten, dieu_kien, ly_do, hanh_dong, so_dong, mau_so,
            id_anh_huong=json.dumps(id_anh_huong), **pham_vi, **them,
        ))



def kiem_tra_gia(du_lieu, moc, moc_gia, nguong, tien_te, bao_cao):
    du_lieu["price_gbp_kpi"] = pd.Series(pd.NA, index=du_lieu.index, dtype="Float64")

    if moc != moc_gia:
        return

    # Prepare đã bỏ ký hiệu tiền và dấu phân cách, QA đọc giá số từ CSV
    gia = pd.to_numeric(du_lieu["price_gbp"], errors="coerce")
    co_thieu = la_gia_tri_thieu(du_lieu["price_raw"])
    co_sai_kieu = ~co_thieu & gia.isna()
    co_sai_mien = gia.notna() & (~np.isfinite(gia) | gia.le(0))
    dung_gia = du_lieu["du_dieu_kien_phan_tich"] & ~(co_thieu | co_sai_kieu | co_sai_mien)
    du_lieu["price_gbp_kpi"] = gia.where(dung_gia).astype("Float64")
    co_vuot = dung_gia & gia.gt(nguong)

    # Tính rào IQR trên log vì giá lệch phải, giữ giá cao trong KPI chính
    gia_log = np.log10(du_lieu["price_gbp_kpi"].astype("float64"))
    q1, q3 = gia_log.quantile([0.25, 0.75])
    iqr = q3 - q1
    du_lieu.attrs["iqr_da_kiem"] = gia_log.count() >= 4 and iqr > 0
    co_iqr = pd.Series(False, index=du_lieu.index)
    bao_cao_iqr = {"trang_thai": "khong_du_mau"}
    if du_lieu.attrs["iqr_da_kiem"]:
        can_duoi = q1 - 1.5 * iqr
        can_tren = q3 + 1.5 * iqr
        co_iqr = gia_log.notna() & ~gia_log.between(can_duoi, can_tren)
        bao_cao_iqr = {"nguong": f"[{10**can_duoi:.2f}, {10**can_tren:.2f}]", "don_vi_nguong": tien_te}

    ghi_cac_co(du_lieu, bao_cao, moc, "listings", [
        ("gia_thieu", co_thieu, "price_raw trống", "Thiếu giá làm giảm mẫu số", "Để trống giá KPI"),
        ("gia_sai_kieu", co_sai_kieu, "Có giá nguồn nhưng price_gbp không đọc được",
         "Giá cần là số", "Để trống giá KPI và rà bước chuẩn hóa"),
        ("gia_sai_mien", co_sai_mien, "price_gbp không hữu hạn hoặc không dương",
         "Giá đêm phải dương hữu hạn", "Để trống giá KPI"),
        ("gia_vuot_nguong", co_vuot, "Giá vượt qa.price_max_gbp", "Giá cao cần xem xét",
         "Giữ giá, so KPI khi bỏ các dòng có cờ", {"nguong": nguong, "don_vi_nguong": tien_te}),
        ("gia_ngoai_rao_iqr", co_iqr, "log10 giá nằm ngoài rào 1,5 × IQR",
         "Phát hiện giá khác biệt trong phân bố", "Giữ giá và báo độ nhạy của KPI", bao_cao_iqr),
    ])


def kiem_tra_bang(
    du_lieu, ten_bang, moc_chup, moc_gia, phan_cong, nguong_qa, tien_te, *,
    listings_cung_moc=None,
):
    """Kiểm CSV do prepare tạo và thêm cột QA"""
    du_lieu = du_lieu.copy()
    if ten_bang == "reviews" and "review_id" not in du_lieu and "id" in du_lieu:
        du_lieu = du_lieu.rename(columns={"id": "review_id"})
    khoa = nguong_qa["keys"][ten_bang]
    kiem_tra_cau_truc(du_lieu, ten_bang, khoa)

    cot_id = "review_id" if ten_bang == "reviews" else "listing_id"
    bang_phan_cong = phan_cong["reviews" if ten_bang == "reviews" else "listings"]
    id_du_kien = set(bang_phan_cong[cot_id])
    id_thuc_te = du_lieu[cot_id]
    moc = pd.Timestamp(moc_chup)
    khoa_kiem = du_lieu[khoa].copy()
    khoa_kiem["snapshot_date"] = pd.to_datetime(du_lieu["snapshot_date"], format="%Y-%m-%d", errors="coerce")
    if ten_bang == "calendar":
        khoa_kiem["calendar_date"] = pd.to_datetime(du_lieu["calendar_date"], format="%Y-%m-%d", errors="coerce")

    co_moc_sai = khoa_kiem["snapshot_date"].ne(moc)
    co_thieu_khoa = khoa_kiem.isna().any(axis=1) | du_lieu[khoa].apply(la_gia_tri_thieu).astype(bool).any(axis=1)
    co_trung = ~co_thieu_khoa & khoa_kiem.duplicated(keep=False)
    co_ngoai = ~id_thuc_te.isin(id_du_kien)
    dung_pham_vi = ~(co_moc_sai | co_thieu_khoa | co_trung | co_ngoai)
    du_lieu["du_dieu_kien_phan_tich"] = dung_pham_vi
    bao_cao = []

    ghi_cac_co(du_lieu, bao_cao, moc_chup, ten_bang, [
        ("moc_chup", co_moc_sai, "Sai snapshot_date", "Cần giữ đúng lần thu thập", "Tạm bỏ dòng khỏi KPI"),
        ("khoa_thieu", co_thieu_khoa, "Thành phần khóa trống hoặc ngày khóa sai kiểu",
         "Không nhận diện được dòng", "Tạm bỏ dòng khỏi KPI"),
        ("khoa_trung", co_trung, "Khóa hoàn chỉnh xuất hiện nhiều lần trong mốc",
         "Dòng trùng làm tăng số đếm", "Giữ để rà và tạm bỏ các dòng cùng khóa khỏi KPI"),
        ("id_ngoai_phan_cong", co_ngoai, "ID ngoài phân công", "Cần đúng mẫu nhóm", "Tạm bỏ dòng khỏi KPI"),
    ])
    id_thieu = id_du_kien - set(id_thuc_te.loc[~co_moc_sai])
    bao_cao.append(dong_bao_cao(
        moc_chup, ten_bang, "thieu_id_phan_cong", "Thiếu ID được giao", "Mẫu phân tích bị thu hẹp",
        "Rà dữ liệu nguồn", len(id_thieu), len(id_du_kien), don_vi="id",
        id_anh_huong=json.dumps(sorted(id_thieu)),
    ))

    if ten_bang in ["listings", "calendar"]:
        co_vung_thieu = la_gia_tri_thieu(du_lieu["analysis_area"])
        co_quan_thieu = la_gia_tri_thieu(du_lieu["neighbourhood_cleansed"])
        du_lieu["du_dieu_kien_theo_vung"] = dung_pham_vi & ~co_vung_thieu
        ghi_cac_co(du_lieu, bao_cao, moc_chup, ten_bang, [
            ("vung_thieu", co_vung_thieu, "Thiếu analysis_area", "KPI cần vùng A01–A08", "Giữ dòng cho toàn mẫu"),
            ("quan_thieu", co_quan_thieu, "Thiếu neighbourhood_cleansed", "KPI cần tên quận", "Giữ dòng cho toàn mẫu"),
        ])

    if ten_bang == "listings":
        loai_phong = du_lieu["room_type"].astype("string").str.strip()
        if not loai_phong.equals(du_lieu["room_type"]):
            du_lieu["room_type_raw"] = du_lieu["room_type"]
        du_lieu["room_type"] = loai_phong
        co_loai_phong_lech = ~du_lieu["room_type"].isin(nguong_qa["room_types"])
        vi_do = pd.to_numeric(du_lieu["latitude"], errors="coerce")
        kinh_do = pd.to_numeric(du_lieu["longitude"], errors="coerce")
        toa_do_dung = (vi_do.between(-90, 90) & kinh_do.between(-180, 180)).fillna(False)

        # Dùng hình chữ nhật từ phân công để kiểm từng điểm, giữ nguyên vùng đã giao
        vung = phan_cong["areas"].set_index("analysis_area").apply(pd.to_numeric, errors="raise")
        can = du_lieu["analysis_area"].map
        trong_vung = (vi_do.between(can(vung["lat_min"]), can(vung["lat_max"]))
                      & kinh_do.between(can(vung["lon_min"]), can(vung["lon_max"])))
        co_ngoai_vung = toa_do_dung & du_lieu["analysis_area"].isin(vung.index) & ~trong_vung
        du_lieu["du_dieu_kien_ban_do"] = dung_pham_vi & toa_do_dung

        so_dem = pd.to_numeric(du_lieu["minimum_nights"], errors="coerce")
        nguong_dem = nguong_qa["min_nights_cap"]
        co_so_dem_sai = ~(so_dem.between(1, nguong_dem) & so_dem.mod(1).eq(0)).fillna(False)
        so_review = pd.to_numeric(du_lieu["number_of_reviews"], errors="coerce")
        dem_review_dung = so_review.ge(0) & np.isfinite(so_review) & so_review.mod(1).eq(0)
        ghi_cac_co(du_lieu, bao_cao, moc_chup, "listings", [
            ("loai_phong_lech", co_loai_phong_lech, "room_type ngoài danh mục cấu hình",
             "Phân nhóm cần loại phòng hợp lệ", "Gắn cờ để rà danh mục"),
            ("toa_do_sai", ~toa_do_dung, "Thiếu, sai kiểu hoặc ngoài miền tọa độ",
             "Bản đồ cần điểm hợp lệ", "Tạm bỏ khỏi phép tính bản đồ"),
            ("toa_do_ngoai_vung", co_ngoai_vung, "Điểm ngoài hình chữ nhật phân công",
             "Điểm có thể thay đổi giữa mốc", "Gắn cờ và giữ vùng phân công"),
            ("so_dem_bat_thuong", co_so_dem_sai, "minimum_nights thiếu hoặc không phải số nguyên trong ngưỡng",
             "Số đêm cần phù hợp miền phân tích", "Gắn cờ để rà nguồn", {"nguong": nguong_dem}),
            ("so_review_bat_thuong", ~dem_review_dung.fillna(False), "number_of_reviews thiếu hoặc sai miền số nguyên không âm",
             "Chỉ số lượt đánh giá cần số đếm hợp lệ", "Tạm bỏ số đếm này khỏi phân tích"),
        ])
        kiem_tra_gia(du_lieu, moc_chup, moc_gia, nguong_qa["price_max_gbp"], tien_te, bao_cao)

    elif ten_bang == "calendar":
        # Đọc trạng thái đã chuẩn hóa từ CSV, giữ giá trị gốc để so tác động
        ngay = khoa_kiem["calendar_date"]
        so_ngay_ky_vong = nguong_qa["calendar_days"]
        so_ngay_theo_cho_o = ngay.loc[dung_pham_vi].groupby(id_thuc_te).nunique()
        id_thieu_ngay = so_ngay_theo_cho_o.index[so_ngay_theo_cho_o.lt(so_ngay_ky_vong)]
        if not id_thieu_ngay.empty:
            bao_cao.append(dong_bao_cao(
                moc_chup, ten_bang, "thieu_ngay_lich_nguon", "Số ngày lịch của listing ít hơn qa.calendar_days",
                "Lịch nguồn thiếu ngày", "Giữ ngày có dữ liệu và báo độ phủ trong cửa sổ KPI",
                len(id_thieu_ngay), len(so_ngay_theo_cho_o), don_vi="id",
                id_anh_huong=json.dumps(sorted(id_thieu_ngay)), nguong=so_ngay_ky_vong, don_vi_nguong="ngay/listing",
            ))

        co_truoc_moc = ngay.lt(moc)
        available = chuyen_dung_sai(du_lieu["available"])
        du_lieu["du_dieu_kien_lich"] = dung_pham_vi & ~co_truoc_moc & available.notna()
        if listings_cung_moc is not None:
            id_hop_le = listings_cung_moc.loc[listings_cung_moc["du_dieu_kien_phan_tich"], "listing_id"]
            co_listing_khong_dung = ~id_thuc_te.isin(id_hop_le)
            du_lieu["du_dieu_kien_lich"] &= ~co_listing_khong_dung
            ghi_cac_co(du_lieu, bao_cao, moc_chup, "calendar", [
                ("listing_khong_dat_qa", co_listing_khong_dung, "Listing không đủ điều kiện phân tích ở mốc này",
                 "KPI lịch dùng đúng tập listing qua QA", "Tạm bỏ lịch của listing này"),
            ])
        du_lieu["available_kpi"] = available.astype("boolean").where(du_lieu["du_dieu_kien_lich"])
        ghi_cac_co(du_lieu, bao_cao, moc_chup, "calendar", [
            ("ngay_lich_truoc_moc", co_truoc_moc, "Ngày lịch trước snapshot",
             "KPI lịch xét ngày từ snapshot", "Không dùng ngày này cho KPI"),
            ("trang_thai_lech", available.isna(), "available thiếu hoặc khác True/False sau khi đọc CSV",
             "KPI cần trạng thái ghi nhận được", "Không dùng trạng thái này cho KPI"),
        ])

    else:
        listing_du_kien = id_thuc_te.map(bang_phan_cong.set_index("review_id")["listing_id"])
        co_sai_listing = listing_du_kien.notna() & du_lieu["listing_id"].ne(listing_du_kien)
        ngay_review = pd.to_datetime(du_lieu["date"], format="%Y-%m-%d", errors="coerce")
        co_noi_dung_thieu = du_lieu["comments"].astype("string").fillna("").str.strip().eq("")
        du_lieu["du_dieu_kien_llm"] = dung_pham_vi & ~co_sai_listing & ~co_noi_dung_thieu
        ghi_cac_co(du_lieu, bao_cao, moc_chup, "reviews", [
            ("review_sai_listing", co_sai_listing, "listing_id khác phân công của review",
             "Review cần nối đúng chỗ ở", "Tạm bỏ khỏi tập phân tích review"),
            ("ngay_review_sai", ngay_review.isna(), "Ngày review trống hoặc sai kiểu",
             "Phân tích theo ngày cần ngày hợp lệ", "Giữ nội dung để phân tích văn bản"),
            ("ngay_review_sau_moc", ngay_review.gt(moc), "Ngày review sau snapshot",
             "Mốc danh nghĩa có thể khác ngày thu thập", "Gắn cờ để rà nguồn"),
            ("review_thieu_noi_dung", co_noi_dung_thieu, "comments trống hoặc toàn khoảng trắng",
             "LLM và baseline cần nội dung", "Tạm bỏ khỏi phân tích văn bản"),
        ])

    return du_lieu, bao_cao



def kiem_tra_giua_cac_moc(cac_bang, danh_sach_moc, nguong_qa):
    bao_cao = []
    for moc_truoc, moc_chup in zip(danh_sach_moc, danh_sach_moc[1:]):
        if moc_chup not in cac_bang:
            continue
        if moc_truoc not in cac_bang:
            bao_cao.append(dong_bao_cao(
                moc_chup, "listings", "doi_chieu_moc_truoc", "Có listings của mốc liền trước",
                "Phải có hai mốc để so sánh", "Ghi rõ dữ liệu chưa có",
                None, None, trang_thai="chua_co_du_lieu", pham_vi="giua_moc", snapshot_truoc=moc_truoc,
            ))
            continue

        truoc = cac_bang[moc_truoc]["listings"]
        sau = cac_bang[moc_chup]["listings"]
        cot = ["listing_id", "latitude", "longitude", "number_of_reviews", "qa_toa_do_sai", "qa_so_review_bat_thuong"]
        truoc_dung = truoc.loc[truoc["du_dieu_kien_phan_tich"], cot].set_index("listing_id")
        sau_dung = sau.loc[sau["du_dieu_kien_phan_tich"], cot].set_index("listing_id")
        doi_chieu = sau_dung.join(truoc_dung, how="inner", rsuffix="_truoc", validate="one_to_one")
        cot_so = [cot for cot in doi_chieu if not cot.startswith("qa_")]
        doi_chieu[cot_so] = doi_chieu[cot_so].apply(pd.to_numeric, errors="coerce")

        # Haversine tính khoảng cách trên mặt cầu theo km
        toa_do_dung = ~(doi_chieu["qa_toa_do_sai"] | doi_chieu["qa_toa_do_sai_truoc"])
        cot_toa_do = ["latitude", "latitude_truoc", "longitude", "longitude_truoc"]
        toa_do = np.radians(doi_chieu.loc[toa_do_dung, cot_toa_do])
        lat, lat_truoc = toa_do["latitude"], toa_do["latitude_truoc"]
        lon, lon_truoc = toa_do["longitude"], toa_do["longitude_truoc"]
        a = (np.sin((lat - lat_truoc) / 2) ** 2
             + np.cos(lat) * np.cos(lat_truoc) * np.sin((lon - lon_truoc) / 2) ** 2)
        km = 6371.0088 * 2 * np.arcsin(np.sqrt(a.clip(0, 1)))
        sau["khoang_cach_moc_truoc_km"] = sau["listing_id"].map(km).where(sau["du_dieu_kien_phan_tich"])
        nguong_km = nguong_qa["coord_shift_max_km"]
        co_dich_chuyen = sau["du_dieu_kien_phan_tich"] & sau["khoang_cach_moc_truoc_km"].gt(nguong_km)
        so_review = doi_chieu["number_of_reviews"]
        so_review_truoc = doi_chieu["number_of_reviews_truoc"]
        dem_dung = ~(doi_chieu["qa_so_review_bat_thuong"] | doi_chieu["qa_so_review_bat_thuong_truoc"])
        id_giam = doi_chieu.index[dem_dung & so_review.lt(so_review_truoc)]
        mau_so_km = len(km)
        mau_so_review = int(dem_dung.sum())
        ghi_cac_co(sau, bao_cao, moc_chup, "listings", [
            ("toa_do_dich_chuyen", co_dich_chuyen, "Tọa độ lệch quá ngưỡng giữa hai mốc",
             "Theo dõi thay đổi vị trí", "Gắn cờ, giữ tọa độ gốc",
             {"mau_so": mau_so_km, "nguong": nguong_km, "don_vi_nguong": "km",
              "trang_thai": None if mau_so_km else "khong_du_mau"}),
            ("so_review_giam", sau["du_dieu_kien_phan_tich"] & sau["listing_id"].isin(id_giam), "Số review giảm giữa hai mốc",
             "Theo dõi biến đếm tích lũy", "Gắn cờ, giữ số nguồn",
             {"mau_so": mau_so_review, "trang_thai": None if mau_so_review else "khong_du_mau"}),
        ], pham_vi="giua_moc", snapshot_truoc=moc_truoc)

        # Prepare đã đối chiếu nội dung và tách một bản review duy nhất cho LLM
        review_truoc = cac_bang[moc_truoc]["reviews"]
        review_sau = cac_bang[moc_chup]["reviews"]
        id_truoc = review_truoc.loc[review_truoc["du_dieu_kien_phan_tich"], "review_id"]
        id_sau = review_sau.loc[review_sau["du_dieu_kien_phan_tich"], "review_id"]
        so_tai_xuat = int(id_sau.isin(id_truoc).sum())
        bao_cao.append(dong_bao_cao(
            moc_chup, "reviews", "review_tai_xuat", "Review ID đã xuất hiện ở mốc liền trước",
            "Một review có thể xuất hiện trong nhiều file", "Đầu vào LLM là reviews_qa.csv của mốc cuối",
            so_tai_xuat, len(id_sau), don_vi="review", trang_thai="ghi_nhan",
            pham_vi="giua_moc", snapshot_truoc=moc_truoc,
        ))

    return bao_cao



def kiem_tra_du_lieu(
    cau_hinh: dict, snapshot: str | None = None,
    thu_muc_du_an: Path = THU_MUC_DU_AN, *,
    phan_cong: dict | None = None,
) -> pd.DataFrame:
    """Kiểm các bảng đã chuẩn bị, nhận phân công đã kiểm khi chạy pipeline"""
    danh_sach_moc = chon_cac_moc(cau_hinh)
    cac_moc_xuat = chon_cac_moc(cau_hinh, snapshot)

    if phan_cong is None:
        phan_cong, _ = doc_phan_cong(thu_muc_du_an / "data" / "assignment", cau_hinh)
    thanh_pho = cau_hinh["city"]

    thu_muc = thu_muc_du_an / "data" / "processed" / thanh_pho
    cac_moc_doc = set(cac_moc_xuat)
    if snapshot and danh_sach_moc.index(snapshot) > 0:
        moc_truoc = danh_sach_moc[danh_sach_moc.index(snapshot) - 1]
        if all((thu_muc / moc_truoc / TEN_TEP_DAU_VAO[bang]).is_file() for bang in ["listings", "reviews"]):
            cac_moc_doc.add(moc_truoc)

    # Kiểm đầu vào trước khi xuất qua từng mốc, mỗi lần chỉ giữ một bảng calendar
    cac_tep = {}
    for moc in sorted(cac_moc_doc):
        for bang in TEN_TEP_DAU_VAO:
            if bang == "calendar" and moc not in cac_moc_xuat:
                continue
            tep = thu_muc / moc / TEN_TEP_DAU_VAO[bang]
            if not tep.is_file():
                raise FileNotFoundError(f"Chưa có {tep}. Chạy prepare.py trước QA")
            tieu_de = pd.read_csv(tep, nrows=0)
            if bang == "reviews" and "review_id" not in tieu_de:
                tieu_de = tieu_de.rename(columns={"id": "review_id"})
            kiem_tra_cau_truc(tieu_de, bang, cau_hinh["qa"]["keys"][bang])
            cac_tep[(moc, bang)] = tep

    def kiem_tra_tep(moc, bang, listings_cung_moc=None):
        du_lieu = pd.read_csv(cac_tep[(moc, bang)], dtype="string", keep_default_na=False)
        return kiem_tra_bang(du_lieu, bang, moc, cau_hinh["kpi"]["price_snapshot"],
                             phan_cong, cau_hinh["qa"], cau_hinh["currency"], listings_cung_moc=listings_cung_moc)

    cac_bang = {}
    bao_cao = []
    for moc in sorted(cac_moc_doc):
        cac_bang[moc] = {}
        for bang in ["listings", "reviews"]:
            cac_bang[moc][bang], cac_dong = kiem_tra_tep(moc, bang)
            bao_cao.extend(cac_dong)
    bao_cao.extend(kiem_tra_giua_cac_moc(cac_bang, danh_sach_moc, cau_hinh["qa"]))

    for moc in cac_moc_xuat:
        calendar, cac_dong = kiem_tra_tep(moc, "calendar", cac_bang[moc]["listings"])
        bao_cao.extend(cac_dong)
        for bang, du_lieu in {**cac_bang[moc], "calendar": calendar}.items():
            cac_cot_co = [cot for cot in du_lieu if cot.startswith("qa_")]
            du_lieu["qa_so_co"] = du_lieu[cac_cot_co].sum(axis=1)
            bao_cao.append(dong_bao_cao(
                moc, bang, "tong_co_it_nhat_mot_co", "Dòng có ít nhất một cờ",
                "Một dòng có thể mắc nhiều quy tắc", "Giữ cờ để truy lại dòng",
                int(du_lieu["qa_so_co"].gt(0).sum()), len(du_lieu),
            ))

            # KPI tính số liệu, QA ghép kết quả vào báo cáo
            for ket_qua in so_sanh_kpi_truoc_sau(du_lieu, bang, moc, cau_hinh, phan_cong):
                dong = dong_bao_cao(
                    moc, bang, ket_qua["quy_tac"], ket_qua["dieu_kien"], "Đo tác động QA",
                    ket_qua["hanh_dong"], ket_qua["so_anh_huong"], ket_qua["mau_so"],
                )
                bao_cao.append({**dong, **ket_qua})
            ghi_csv(thu_muc / moc / f"{bang}_qa.csv", du_lieu)

    ket_qua = pd.DataFrame(dong for dong in bao_cao if dong["snapshot_date"] in cac_moc_xuat)
    for cot in ["so_anh_huong", "mau_so", "n_truoc", "n_sau"]:
        ket_qua[cot] = ket_qua[cot].astype("Int64")
    ten_bao_cao = "qa_report.csv" if snapshot is None else f"qa_report_{snapshot}.csv"
    ghi_csv(thu_muc_du_an / "reports" / ten_bao_cao, ket_qua)
    return ket_qua



def main() -> None:
    trinh_doc = ArgumentParser(description="Kiểm QA các bảng đã chuẩn bị và xuất báo cáo")
    trinh_doc.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc.add_argument("--snapshot", help="Xuất QA một snapshot trong cấu hình")
    tham_so = trinh_doc.parse_args()

    cau_hinh = doc_cau_hinh(tham_so.config)
    bao_cao = kiem_tra_du_lieu(cau_hinh, snapshot=tham_so.snapshot)
    print(f"[HOÀN TẤT] {len(bao_cao)} dòng báo cáo")


if __name__ == "__main__":
    main()
