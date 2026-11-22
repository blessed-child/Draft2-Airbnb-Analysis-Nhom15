from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from .common import CAM_XUC, CAU_HINH_MAC_DINH, SO_LAN_BOOTSTRAP, THU_MUC_DU_AN
from .common import chon_cac_moc, chuyen_dung_sai, doc_cau_hinh, la_dung
from .common import write_csv as ghi_csv


def lay_gia_tri_kpi(du_lieu, ten_bang, moc_chup, cau_hinh_kpi, *, sau_qa):
    """Giữ giá hoặc trạng thái lịch đủ điều kiện, đặt các ô còn lại thành NA"""
    if ten_bang == "listings":
        cot = "price_gbp_kpi" if sau_qa else "price_gbp"
        gia = pd.to_numeric(du_lieu[cot], errors="coerce")
        return gia.where(gia.gt(0) & np.isfinite(gia))

    ngay = pd.to_datetime(du_lieu["calendar_date"], format="%Y-%m-%d", errors="coerce")
    bat_dau = pd.Timestamp(moc_chup)
    ket_thuc = bat_dau + pd.Timedelta(days=cau_hinh_kpi["calendar_horizon_days"])
    trong_cua_so = ngay.ge(bat_dau) & ngay.lt(ket_thuc)
    trang_thai = chuyen_dung_sai(du_lieu["available"])
    if sau_qa:
        trong_cua_so &= la_dung(du_lieu["du_dieu_kien_lich"])
    return trang_thai.where(trong_cua_so)


def gia_thong_ke(gia: pd.Series, cau_hinh_kpi: dict) -> float | None:
    if not gia.notna().any():
        return None
    return float(gia.median() if cau_hinh_kpi["price_stat"] == "median" else gia.mean())


def ten_kpi_gia(cau_hinh_kpi: dict) -> str:
    return "gia_trung_vi_gbp" if cau_hinh_kpi["price_stat"] == "median" else "gia_trung_binh_gbp"


def tinh_kpi(du_lieu, ten_bang, moc_chup, cau_hinh_kpi, *, sau_qa):
    """Trả giá trị, số quan sát và cờ chọn dòng để báo cáo trước/sau"""
    if ten_bang not in ("listings", "calendar"):
        raise ValueError(f"Chưa có công thức KPI cho bảng {ten_bang}.")
    gia_tri = lay_gia_tri_kpi(du_lieu, ten_bang, moc_chup, cau_hinh_kpi, sau_qa=sau_qa)
    duoc_dung = gia_tri.notna()
    n = int(duoc_dung.sum())
    if ten_bang == "listings":
        ket_qua = gia_thong_ke(gia_tri, cau_hinh_kpi)
    else:
        ket_qua = float(gia_tri.mean()) if n else None
    return ket_qua, n, duoc_dung


def so_sanh_kpi_truoc_sau(du_lieu, ten_bang, moc_chup, cau_hinh, phan_cong):
    """Tính KPI chính, kịch bản giá và độ phủ để QA ghi báo cáo"""
    kpi = cau_hinh["kpi"]
    can_so_gia = ten_bang == "listings" and moc_chup == kpi["price_snapshot"] and "gia_trung_vi_gbp" in kpi["qa_compare"]
    can_so_lich = ten_bang == "calendar" and "ty_le_ngay_san_co" in kpi["qa_compare"]
    if not (can_so_gia or can_so_lich):
        return []
    truoc, n_truoc, co_truoc = tinh_kpi(du_lieu, ten_bang, moc_chup, kpi, sau_qa=False)
    sau, n_sau, co_sau = tinh_kpi(du_lieu, ten_bang, moc_chup, kpi, sau_qa=True)
    ten_kpi = "ty_le_ngay_san_co"
    don_vi = "ty_le_0_1"
    if can_so_gia:
        ten_kpi = ten_kpi_gia(kpi)
        don_vi = f"{cau_hinh['currency']}/dem"
    dong_chinh = {
        "quy_tac": "kpi_truoc_sau", "pham_vi": "kpi", "kpi_ten": ten_kpi,
        "kpi_truoc": truoc, "kpi_sau": sau, "n_truoc": n_truoc, "n_sau": n_sau,
        "don_vi_kpi": don_vi, "so_anh_huong": int((co_truoc & ~co_sau).sum()), "mau_so": n_truoc,
        "dieu_kien": "Cùng công thức và cửa sổ trước/sau QA",
        "hanh_dong": "Trước QA dùng giá dương hữu hạn hoặc ngày/trạng thái đọc được; sau QA áp dụng điều kiện dùng dữ liệu",
        "trang_thai": "dat",
    }
    if n_sau == 0:
        dong_chinh["trang_thai"] = "khong_du_mau"
    elif dong_chinh["so_anh_huong"] > 0:
        dong_chinh["trang_thai"] = "can_xem_lai"
    ket_qua = [dong_chinh]
    if can_so_gia:
        # Hai kịch bản bổ sung đều so với KPI chính sau QA
        for ten_co in ["gia_vuot_nguong", "gia_ngoai_rao_iqr"]:
            if ten_co == "gia_ngoai_rao_iqr" and not du_lieu.attrs.get("iqr_da_kiem", False):
                continue
            co = du_lieu[f"qa_{ten_co}"]
            gia = pd.to_numeric(du_lieu["price_gbp_kpi"], errors="coerce").loc[co_sau & ~co]
            gia_tri = gia_thong_ke(gia, kpi)
            dong = dong_chinh.copy()
            dong.update(
                quy_tac=f"kpi_bo_{ten_co}", pham_vi="kich_ban", kpi_truoc=sau,
                kpi_sau=gia_tri, n_truoc=n_sau, n_sau=len(gia), mau_so=n_sau,
                so_anh_huong=int((co_sau & co).sum()),
                dieu_kien=f"Kịch bản bỏ cờ {ten_co}", hanh_dong="So độ nhạy; giữ giá cao trong KPI chính",
                trang_thai="dat",
            )
            if gia.empty:
                dong["trang_thai"] = "khong_du_mau"
            elif dong["so_anh_huong"] > 0:
                dong["trang_thai"] = "can_xem_lai"
            ket_qua.append(dong)
    else:
        so_cap_ky_vong = len(phan_cong["listings"]) * kpi["calendar_horizon_days"]
        ket_qua.append({
            "quy_tac": "thieu_cap_trong_cua_so", "pham_vi": "trong_moc",
            "so_anh_huong": so_cap_ky_vong - n_sau, "mau_so": so_cap_ky_vong,
            "don_vi": "cap_listing_ngay", "do_phu": n_sau / so_cap_ky_vong if so_cap_ky_vong else None,
            "dieu_kien": "Cặp listing-ngày hợp lệ ít hơn số kỳ vọng trong cửa sổ cấu hình",
            "hanh_dong": "Công bố độ phủ, dùng mẫu số quan sát hợp lệ",
        })
    return ket_qua


def cac_nhom_kpi(listings: pd.DataFrame, cau_hinh: dict):
    """Nhóm toàn mẫu, theo quận, rồi theo vùng phân công"""
    yield "city", cau_hinh["city"], listings
    kpi = cau_hinh["kpi"]
    for pham_vi, cot_vung in [
        ("neighbourhood", kpi["area_col"]),
        ("analysis_area", kpi["area_col_assignment"]),
    ]:
        co_vung = listings[cot_vung].str.strip().ne("")
        if pham_vi == "analysis_area":
            co_vung &= la_dung(listings["du_dieu_kien_theo_vung"])
        else:
            co_vung &= ~la_dung(listings["qa_quan_thieu"])
        for ten_vung, nhom in listings.loc[co_vung].groupby(cot_vung):
            yield pham_vi, ten_vung, nhom


def dong_kpi(thong_tin, ten, gia_tri, don_vi, so_listing, *, tu_so=None, mau_so=None,
             mau_ky_vong=None, ky_review="", trang_thai=None):
    moc_chup, cau_hinh, pham_vi, khu_vuc = thong_tin
    du_mau = so_listing >= cau_hinh["kpi"]["min_n"]
    return {
        "snapshot_date": moc_chup, "city": cau_hinh["city"], "pham_vi": pham_vi,
        "khu_vuc": khu_vuc, "ky_review": ky_review, "kpi_ten": ten, "gia_tri": gia_tri,
        "don_vi": don_vi, "tu_so": tu_so, "mau_so": mau_so, "mau_ky_vong": mau_ky_vong,
        "so_listing": so_listing, "du_mau": du_mau,
        "trang_thai": trang_thai or ("khong_co_du_lieu" if gia_tri is None else "da_tinh"),
    }


def doc_bang_qa(duong_dan: Path) -> pd.DataFrame:
    return pd.read_csv(duong_dan, dtype="string", keep_default_na=False)


def tong_hop_mot_moc(thu_muc, moc_chup, cau_hinh, phan_cong):
    kpi = cau_hinh["kpi"]
    listings = doc_bang_qa(thu_muc / "listings_qa.csv")
    listings = listings.loc[la_dung(listings["du_dieu_kien_phan_tich"])]
    lich = doc_bang_qa(thu_muc / "calendar_qa.csv")
    trang_thai = lay_gia_tri_kpi(lich, "calendar", moc_chup, kpi, sau_qa=True)
    # Gom lịch một lần theo listing để các nhóm dùng chung tử số và mẫu số
    lich["san_co"] = trang_thai
    theo_listing = lich.groupby("listing_id")["san_co"].agg(["sum", "count"])
    listings = listings.join(theo_listing, on="listing_id", validate="one_to_one")
    listings[["sum", "count"]] = listings[["sum", "count"]].fillna(0)
    listings["gia_hop_le"] = lay_gia_tri_kpi(listings, "listings", moc_chup, kpi, sau_qa=True)
    cac_dong_listings, cac_dong_lich = [], []

    for pham_vi, khu_vuc, nhom in cac_nhom_kpi(listings, cau_hinh):
        thong_tin = (moc_chup, cau_hinh, pham_vi, khu_vuc)
        loai_phong = nhom["room_type"]
        loai_phong = loai_phong.loc[loai_phong.isin(cau_hinh["qa"]["room_types"])]
        n_loai = len(loai_phong)
        n_nguyen_can = int(loai_phong.eq("Entire home/apt").sum())
        n = len(nhom)
        cac_dong_listings.extend([
            dong_kpi(thong_tin, "so_listing", n, "listing", n),
            dong_kpi(thong_tin, "ty_le_nguyen_can", n_nguyen_can / n_loai if n_loai else None,
                     "ty_le_0_1", n_loai, tu_so=n_nguyen_can, mau_so=n_loai),
        ])
        if moc_chup == kpi["price_snapshot"]:
            # Thêm giá riêng nguyên căn để so khu vực không bị lệch vì cơ cấu loại phòng
            for ten_gia, gia in [
                (ten_kpi_gia(kpi), nhom["gia_hop_le"]),
                (f"{ten_kpi_gia(kpi)}_nguyen_can", nhom.loc[nhom["room_type"].eq("Entire home/apt"), "gia_hop_le"]),
            ]:
                n_gia = int(gia.count())
                cac_dong_listings.append(dong_kpi(
                    thong_tin, ten_gia, gia_thong_ke(gia, kpi),
                    f"{cau_hinh['currency']}/dem", n_gia, mau_so=n_gia,
                ))

        so_cap = int(nhom["count"].sum())
        so_cap_san_co = int(nhom["sum"].sum())
        n_lich = int(nhom["count"].gt(0).sum())
        if pham_vi == "city":
            n_ky_vong = len(phan_cong)
        elif pham_vi == "analysis_area":
            n_ky_vong = int(phan_cong[kpi["area_col_assignment"]].eq(khu_vuc).sum())
        else:
            n_ky_vong = n
        so_cap_ky_vong = n_ky_vong * kpi["calendar_horizon_days"]
        cac_dong_lich.extend([
            # mau_ky_vong cho phép tính cận khi coi toàn bộ cặp thiếu là bận hoặc trống
            dong_kpi(thong_tin, "ty_le_ngay_san_co", so_cap_san_co / so_cap if so_cap else None,
                     "ty_le_0_1", n_lich, tu_so=so_cap_san_co, mau_so=so_cap, mau_ky_vong=so_cap_ky_vong),
            dong_kpi(thong_tin, "do_phu_lich", so_cap / so_cap_ky_vong if so_cap_ky_vong else None,
                     "ty_le_0_1", n_lich, tu_so=so_cap, mau_so=so_cap_ky_vong),
        ])
    return listings, cac_dong_listings, cac_dong_lich


def tong_hop_llm(thu_muc, listings, moc_chup, cau_hinh, duong_dan_llm):
    danh_gia = doc_bang_qa(thu_muc / "reviews_unique.csv")
    mau = danh_gia.loc[la_dung(danh_gia["llm_sample"]), ["review_id", "listing_id", "date"]]
    danh_gia_qa = doc_bang_qa(thu_muc / moc_chup / "reviews_qa.csv")
    id_mau_cung_moc = danh_gia_qa.loc[la_dung(danh_gia_qa["llm_sample"]), "review_id"]
    if not mau["review_id"].isin(id_mau_cung_moc).any():
        mau = mau.iloc[:0]
    id_dat_qa = danh_gia_qa.loc[la_dung(danh_gia_qa["du_dieu_kien_llm"]), "review_id"]

    co_tep_llm = duong_dan_llm.is_file()
    if co_tep_llm and not mau.empty:
        nhan = pd.read_csv(duong_dan_llm, usecols=["review_id", "sentiment"], dtype="string")
        nhan = nhan.loc[nhan["review_id"].isin(mau["review_id"])].drop_duplicates()
        if nhan["review_id"].duplicated().any():
            raise ValueError("Kết quả LLM có nhãn cảm xúc mâu thuẫn cho cùng review_id.")
        mau = mau.merge(nhan, on="review_id", how="left", validate="one_to_one")
    else:
        mau = mau.assign(sentiment=pd.NA)
    hop_le = mau["sentiment"].isin(CAM_XUC) & mau["review_id"].isin(id_dat_qa)
    mau["tich_cuc"] = mau["sentiment"].eq("positive").where(hop_le)
    mau["nam_viet"] = pd.to_datetime(mau["date"], format="%Y-%m-%d", errors="coerce").dt.year

    # Mốc chỉ tham chiếu vùng của listing, thời gian review lấy theo năm viết
    cac_dong = []
    for pham_vi, khu_vuc, nhom in cac_nhom_kpi(listings, cau_hinh):
        thong_tin = (moc_chup, cau_hinh, pham_vi, khu_vuc)
        review_nhom = mau if pham_vi == "city" else mau.loc[mau["listing_id"].isin(nhom["listing_id"])]
        cac_ky = [("tat_ca", review_nhom), *review_nhom.groupby("nam_viet")]
        for ky, review_ky in cac_ky:
            co_nhan = review_ky["tich_cuc"].notna()
            n = int(co_nhan.sum())
            so_tich_cuc = int(review_ky["tich_cuc"].sum())
            so_listing = review_ky.loc[co_nhan, "listing_id"].nunique()
            trang_thai = None
            if mau.empty:
                trang_thai = "khong_co_mau_llm"
            elif len(review_ky) and not co_tep_llm:
                trang_thai = "chua_co_tep_llm"
            elif n < len(review_ky):
                trang_thai = "thieu_nhan_llm" if n else "chua_co_nhan_llm_hop_le"
            cac_dong.append(dong_kpi(
                thong_tin, "ty_le_review_tich_cuc", so_tich_cuc / n if n else None,
                "ty_le_0_1", so_listing, tu_so=so_tich_cuc, mau_so=n,
                mau_ky_vong=len(review_ky), ky_review=ky, trang_thai=trang_thai,
            ))
    return cac_dong, mau


def so_sanh_quan(listings, danh_gia, moc_chup, cau_hinh):
    """Khoảng tin cậy bootstrap theo listing cho tỷ lệ tích cực của quận, chênh lệch từng cặp quận và Spearman giá với tỷ lệ tích cực"""
    kpi = cau_hinh["kpi"]
    co_nhan = danh_gia.loc[danh_gia["tich_cuc"].notna()].astype({"tich_cuc": "int64"})
    theo_listing = co_nhan.groupby("listing_id")["tich_cuc"].agg(["sum", "size"])
    theo_listing = theo_listing.join(
        listings.set_index("listing_id")[[kpi["area_col"], "gia_hop_le"]], how="inner", validate="one_to_one",
    )
    cac_dong = []
    if moc_chup == kpi["price_snapshot"] and not theo_listing.empty:
        co_gia = theo_listing["gia_hop_le"].notna()
        cac_dong.append({
            "phep_so_sanh": "spearman_gia_va_ty_le_tich_cuc", "gia_tri": theo_listing.loc[co_gia, "gia_hop_le"].corr(
                theo_listing.loc[co_gia, "sum"] / theo_listing.loc[co_gia, "size"], method="spearman"),
            "so_listing": int(co_gia.sum()),
        })

    # Chỉ so quận có đủ listing có nhãn. Mỗi quận được lấy mẫu lại riêng vì listing không thuộc hai quận
    du_mau = theo_listing.groupby(kpi["area_col"])["sum"].transform("size").ge(kpi["min_n"])
    theo_quan = theo_listing.loc[du_mau].groupby(kpi["area_col"]).agg(
        tu_so=("sum", "sum"), mau_so=("size", "sum"), so_listing=("sum", "size"))
    theo_quan = theo_quan.assign(ty_le=theo_quan["tu_so"] / theo_quan["mau_so"]).sort_values("ty_le", ascending=False)
    if len(theo_quan) >= 2:
        rng = np.random.default_rng(cau_hinh["seed"])
        ty_le_lai = []
        for ten_quan in theo_quan.index:
            nhom = theo_listing.loc[theo_listing[kpi["area_col"]].eq(ten_quan)]
            mau_lai = rng.integers(len(nhom), size=(SO_LAN_BOOTSTRAP, len(nhom)))
            ty_le_lai.append(nhom["sum"].to_numpy()[mau_lai].sum(axis=1) / nhom["size"].to_numpy()[mau_lai].sum(axis=1))
        ty_le_lai = np.array(ty_le_lai)
        # Quận đứng trước luôn có tỷ lệ quan sát cao hơn quận đứng sau
        quan_a, quan_b = np.triu_indices(len(theo_quan), k=1)
        chenh = ty_le_lai[quan_a] - ty_le_lai[quan_b]
        can = np.quantile(ty_le_lai, [0.025, 0.975], axis=1)
        can_chenh = np.quantile(chenh, [0.025, 0.975], axis=1)
        cac_dong.extend(pd.DataFrame({
            "phep_so_sanh": "ty_le_tich_cuc", "khu_vuc_a": theo_quan.index, "gia_tri": theo_quan["ty_le"].to_numpy(),
            "ci95_lower": can[0], "ci95_upper": can[1], "so_listing": theo_quan["so_listing"].to_numpy(),
            "so_review": theo_quan["mau_so"].to_numpy(),
        }).to_dict("records"))
        cac_dong.extend(pd.DataFrame({
            "phep_so_sanh": "chenh_ty_le_tich_cuc", "khu_vuc_a": theo_quan.index[quan_a], "khu_vuc_b": theo_quan.index[quan_b],
            "gia_tri": theo_quan["ty_le"].to_numpy()[quan_a] - theo_quan["ty_le"].to_numpy()[quan_b],
            "ci95_lower": can_chenh[0], "ci95_upper": can_chenh[1],
            "so_listing": theo_quan["so_listing"].to_numpy()[quan_a] + theo_quan["so_listing"].to_numpy()[quan_b],
            "so_review": theo_quan["mau_so"].to_numpy()[quan_a] + theo_quan["mau_so"].to_numpy()[quan_b],
        }).to_dict("records"))
    bang = pd.DataFrame(cac_dong, columns=[
        "phep_so_sanh", "khu_vuc_a", "khu_vuc_b", "gia_tri", "ci95_lower", "ci95_upper", "so_listing", "so_review"])
    return bang.assign(so_lan_bootstrap=SO_LAN_BOOTSTRAP, seed=cau_hinh["seed"])


def tim_bat_thuong(bang_listings, bang_calendar, cau_hinh):
    """Tìm quận lệch hẳn so với các quận khác bằng z-score, chỉ xét quận đủ mẫu"""
    listings, lich = pd.DataFrame(bang_listings), pd.DataFrame(bang_calendar)
    chon = lambda bang, ten: bang.loc[bang["pham_vi"].eq("neighbourhood") & bang["kpi_ten"].eq(ten) & bang["du_mau"]]
    san_co = chon(lich, "ty_le_ngay_san_co").pivot(index="khu_vuc", columns="snapshot_date", values="gia_tri")
    if san_co.empty:  # Không quận nào đủ mẫu thì chỉ giữ KPI cơ bản, bảng bất thường để trống
        print("[BỎ QUA] Không quận nào đủ mẫu để tìm quận bất thường", flush=True)
        return pd.DataFrame(columns=[
            "moc_dau", "moc_cuoi", "khu_vuc", "chi_so", "gia_tri", "z", "z_ben_vung",
            "bat_thuong", "bat_thuong_z25", "bat_thuong_ben_vung",
        ])
    cac_chi_so = {"ty_le_san_co": san_co[san_co.columns.max()]}
    if len(san_co.columns) > 1:
        cac_chi_so["thay_doi_san_co"] = san_co[san_co.columns.max()] - san_co[san_co.columns.min()]
    gia = chon(listings, ten_kpi_gia(cau_hinh["kpi"])).set_index("khu_vuc")["gia_tri"]
    if not gia.empty:
        cac_chi_so["log10_gia"] = np.log10(gia.astype("float64"))  # Giá lệch phải nên xét trên log

    bang = pd.DataFrame(cac_chi_so).rename_axis("khu_vuc").reset_index()
    bang = bang.melt(id_vars="khu_vuc", var_name="chi_so", value_name="gia_tri").dropna()
    theo_chi_so = bang.groupby("chi_so")["gia_tri"]
    bang["z"] = (bang["gia_tri"] - theo_chi_so.transform("mean")) / theo_chi_so.transform("std")
    # z bền vững dùng trung vị và MAD nên ít bị chính các quận lệch kéo theo
    do_lech = bang["gia_tri"] - theo_chi_so.transform("median")
    mad = do_lech.abs().groupby(bang["chi_so"]).transform("median").replace(0, np.nan)  # MAD bằng 0 thì z không xác định, để trống thay vì inf
    bang["z_ben_vung"] = 0.6745 * do_lech / mad
    bang["bat_thuong"] = bang["z"].abs().ge(2)
    bang["bat_thuong_z25"] = bang["z"].abs().ge(2.5)
    bang["bat_thuong_ben_vung"] = bang["z_ben_vung"].abs().ge(3.5)
    bang.insert(0, "moc_dau", san_co.columns.min())
    bang.insert(1, "moc_cuoi", san_co.columns.max())
    return bang.sort_values(["chi_so", "z"], ignore_index=True)


def xuat_kpi(cau_hinh, *, snapshot=None, duong_dan_llm=None, thu_muc_xuat=None, thu_muc_du_an=THU_MUC_DU_AN):
    danh_sach_moc = chon_cac_moc(cau_hinh, snapshot)

    thu_muc_xu_ly = thu_muc_du_an / "data" / "processed"
    thu_muc_thanh_pho = thu_muc_xu_ly / cau_hinh["city"]
    phan_cong = pd.read_csv(thu_muc_du_an / "data" / "assignment" / "listings.csv", dtype="string")
    duong_dan_llm = duong_dan_llm or thu_muc_xu_ly / "llm_results.csv"
    thu_muc_xuat = thu_muc_xuat or thu_muc_xu_ly
    bang_listings, bang_calendar = [], []

    for moc_chup in danh_sach_moc:
        listings, cac_dong_listings, cac_dong_lich = tong_hop_mot_moc(
            thu_muc_thanh_pho / moc_chup, moc_chup, cau_hinh, phan_cong,
        )
        bang_listings.extend(cac_dong_listings)
        bang_calendar.extend(cac_dong_lich)
    duoi_tep = f"_{snapshot}.csv" if snapshot else ".csv"

    def ghi_bang_kpi(ten, cac_dong):
        bang = pd.DataFrame(cac_dong)
        for cot in ["tu_so", "mau_so", "mau_ky_vong"]:
            bang[cot] = bang[cot].astype("Int64")
        ghi_csv(thu_muc_xuat / f"kpi_{ten}{duoi_tep}", bang)

    ghi_bang_kpi("listings", bang_listings)
    ghi_bang_kpi("calendar", bang_calendar)
    ghi_csv(thu_muc_xuat / f"kpi_bat_thuong{duoi_tep}", tim_bat_thuong(bang_listings, bang_calendar, cau_hinh))

    # Chỉ tổng hợp mỗi review một lần, dùng phân vùng của mốc cuối trong lần chạy
    moc_llm = danh_sach_moc[-1]
    bang_llm, danh_gia_llm = tong_hop_llm(thu_muc_thanh_pho, listings, moc_llm, cau_hinh, duong_dan_llm)
    ghi_bang_kpi("llm", bang_llm)
    ghi_csv(thu_muc_xuat / f"kpi_so_sanh_quan{duoi_tep}", so_sanh_quan(listings, danh_gia_llm, moc_llm, cau_hinh))


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(description="Tổng hợp KPI cho mẫu Airbnb đã qua QA")
    trinh_doc_tham_so.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc_tham_so.add_argument("--snapshot")
    trinh_doc_tham_so.add_argument("--llm-results", type=Path)
    trinh_doc_tham_so.add_argument("--output-dir", type=Path)
    tham_so = trinh_doc_tham_so.parse_args()
    cau_hinh = doc_cau_hinh(tham_so.config)
    xuat_kpi(cau_hinh, snapshot=tham_so.snapshot, duong_dan_llm=tham_so.llm_results,
             thu_muc_xuat=tham_so.output_dir)


if __name__ == "__main__":
    main()
