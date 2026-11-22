import json
from argparse import ArgumentParser
from pathlib import Path

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")  # Vẽ được khi chạy pipeline trên máy không có cửa sổ đồ họa
from matplotlib import pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.ticker import PercentFormatter

from .common import CAU_HINH_MAC_DINH, THU_MUC_DU_AN, chon_cac_moc, doc_cau_hinh, la_dung
from .kpi import ten_kpi_gia

MAU_CHINH = "#126B70"
MAU_PHU = "#AD512D"
MAU_TRONG = "#E7EBEF"
MAU_CHU = "#172E42"


def chon_kpi(bang, ten, pham_vi, *, moc=None):
    """Chọn đúng chỉ số, phạm vi và mốc đã được tổng hợp"""
    duoc_chon = bang["kpi_ten"].eq(ten) & bang["pham_vi"].eq(pham_vi)
    if moc is not None:
        duoc_chon &= bang["snapshot_date"].eq(moc)
    return bang.loc[duoc_chon].copy()


def luu_hinh(hinh, truc, tieu_de, ghi_chu, duong_dan):
    truc.set_title(tieu_de, loc="left", pad=12)
    hinh.supxlabel(ghi_chu, x=0.015, ha="left", fontsize=9, color="#465667")
    try:
        hinh.savefig(duong_dan, dpi=180, bbox_inches="tight", pad_inches=0.2)
    finally:
        plt.close(hinh)
    return duong_dan


def ve_cot_ngang(nhom, gia_tri, nhan, mau, *, chieu_cao):
    hinh, truc = plt.subplots(figsize=(9.4, chieu_cao))
    cot = truc.barh(nhom, gia_tri, color=mau)
    truc.bar_label(cot, labels=nhan, padding=5, fontsize=9)
    truc.invert_yaxis()
    truc.margins(x=0.25)
    truc.grid(axis="x", alpha=0.25)
    return hinh, truc


def ve_ban_do(bang, duong_dan_geo, city, moc, duong_dan):
    """Ghép số chỗ ở theo quận với ranh giới tại cùng mốc"""
    so_cho_o = chon_kpi(bang, "so_listing", "neighbourhood", moc=moc)
    ranh_gioi = gpd.read_file(duong_dan_geo).to_crs("EPSG:4326")
    khong_khop = set(so_cho_o["khu_vuc"]) - set(ranh_gioi["neighbourhood"])
    if khong_khop:
        raise ValueError(f"Tên quận trong KPI không khớp GeoJSON: {sorted(khong_khop)}")

    ban_do = ranh_gioi.merge(
        so_cho_o[["khu_vuc", "gia_tri"]], left_on="neighbourhood", right_on="khu_vuc",
        how="left", validate="many_to_one",
    )
    if not ban_do["gia_tri"].notna().any():
        raise ValueError(f"Không có KPI số chỗ ở theo quận cho mốc {moc}")

    hinh, truc = plt.subplots(figsize=(9, 7))
    ban_do.plot(
        ax=truc, column="gia_tri", cmap="YlGnBu", edgecolor="white", linewidth=0.7,
        vmin=0, legend=True, legend_kwds={"label": "Số chỗ ở", "shrink": 0.76},
        missing_kwds={"color": MAU_TRONG, "edgecolor": "white"},
    )
    truc.set(xlabel="Kinh độ (°)", ylabel="Vĩ độ (°)")
    return luu_hinh(
        hinh, truc, f"{city} | Số chỗ ở trong mẫu theo quận · {moc}",
        "Nguồn: Inside Airbnb và mẫu được giao sau QA · Màu xám: không có dòng KPI", duong_dan,
    )


def ve_lich_theo_moc(bang, city, cac_moc, so_ngay, duong_dan):
    """So sánh mức sẵn có và độ phủ lịch trong cùng độ dài cửa sổ"""
    lich = bang.loc[bang["pham_vi"].eq("city")].pivot(
        index="snapshot_date", columns="kpi_ten", values="gia_tri",
    ).reindex(cac_moc)
    ngay = pd.to_datetime(lich.index)

    hinh, truc = plt.subplots(figsize=(max(9, 1.4 * len(cac_moc)), 4.6))
    truc.plot(ngay, lich["ty_le_ngay_san_co"], "o-", color=MAU_CHINH, label="Ngày sẵn có")
    truc.plot(ngay, lich["do_phu_lich"], "s--", color=MAU_PHU, label="Độ phủ lịch")
    truc.set(xlabel="Ngày chụp dữ liệu", ylabel="Tỷ lệ (%)", ylim=(0, 1.06), xticks=ngay)
    truc.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    if len(ngay) == 1:
        le = pd.Timedelta(days=7)
        truc.set_xlim(ngay[0] - le, ngay[0] + le)
    truc.yaxis.set_major_formatter(PercentFormatter(1))
    truc.legend(loc="lower left", ncols=2)
    truc.grid(axis="y", alpha=0.25)
    return luu_hinh(
        hinh, truc, f"{city} | Mức sẵn có và độ phủ lịch trong {so_ngay} ngày từ mỗi mốc",
        "Mẫu được giao sau QA · Ngày không sẵn có có thể do chủ nhà khóa lịch", duong_dan,
    )


def ve_lich_theo_vung(bang, city, cac_moc, so_ngay, min_n, duong_dan):
    lich = chon_kpi(bang, "ty_le_ngay_san_co", "analysis_area")
    # Giữ ô thiếu và ô dưới ngưỡng trống thay vì tô như tỷ lệ 0%
    lich["gia_tri"] = lich["gia_tri"].where(la_dung(lich["du_mau"]))
    ma_tran = lich.pivot(index="khu_vuc", columns="snapshot_date", values="gia_tri").reindex(columns=cac_moc)
    if ma_tran.empty:
        raise ValueError("Không có KPI lịch theo vùng phân công")

    hinh, truc = plt.subplots(figsize=(max(7.8, 1.2 * len(cac_moc) + 3), 5.2))
    mau = plt.get_cmap("YlGnBu").with_extremes(bad=MAU_TRONG)
    gia_tri_lich = ma_tran.to_numpy()
    anh = truc.imshow(gia_tri_lich, cmap=mau, aspect="auto", vmin=0, vmax=1)
    hinh.colorbar(anh, ax=truc, label="Tỷ lệ ngày sẵn có (%)", format=PercentFormatter(1))
    truc.set_xticks(range(len(cac_moc)), cac_moc)
    truc.set_yticks(range(len(ma_tran)), ma_tran.index)
    truc.set(xlabel="Ngày chụp dữ liệu", ylabel="Vùng phân công")
    for i, dong in enumerate(gia_tri_lich):
        for j, gia_tri in enumerate(dong):
            nhan = f"{gia_tri:.0%}" if pd.notna(gia_tri) else "—"
            mau_chu = "white" if gia_tri >= 0.62 else "black"
            truc.text(j, i, nhan, ha="center", va="center", color=mau_chu)
    return luu_hinh(
        hinh, truc, f"{city} | Lịch sẵn có theo vùng trong {so_ngay} ngày từ mỗi mốc",
        f"Mẫu được giao sau QA · Ô xám: thiếu KPI hoặc ít hơn {min_n} chỗ ở đủ điều kiện", duong_dan,
    )


def ve_gia_theo_quan(bang, city, moc, ten_gia, don_vi, min_n, duong_dan):
    gia = chon_kpi(bang, ten_gia, "neighbourhood", moc=moc).dropna(subset=["gia_tri"])
    gia = gia.loc[la_dung(gia["du_mau"])]
    if gia.empty:
        return None

    # Chọn quận có nhiều dữ liệu giá nhất rồi mới sắp xếp theo giá
    gia = gia.sort_values(["mau_so", "khu_vuc"], ascending=[False, True]).head(12)
    gia = gia.sort_values(["gia_tri", "khu_vuc"], ascending=[False, True])
    thong_ke = "trung vị" if ten_gia == "gia_trung_vi_gbp" else "trung bình"
    nhan = [f"{tri:,.2f}  (n={n:g})" for tri, n in zip(gia["gia_tri"], gia["mau_so"])]
    hinh, truc = ve_cot_ngang(gia["khu_vuc"], gia["gia_tri"], nhan, MAU_CHINH, chieu_cao=5.8)
    truc.set(xlabel=f"Giá {thong_ke} ({don_vi})", ylabel="Quận")
    return luu_hinh(
        hinh, truc, f"{city} | Giá {thong_ke} theo quận · {moc}",
        f"Tối đa 12 quận có nhiều giá hợp lệ nhất · n: số chỗ ở có giá hợp lệ (tối thiểu {min_n})",
        duong_dan,
    )


def ve_do_nhay_gia(bang, city, moc, ten_gia, don_vi, duong_dan):
    """Vẽ lại các kịch bản giá do QA báo cáo, giữ cả mẫu số"""
    nhan = {
        "kpi_truoc_sau": "Sau QA · KPI chính",
        "kpi_bo_gia_vuot_nguong": "Bỏ giá vượt ngưỡng",
        "kpi_bo_gia_ngoai_rao_iqr": "Bỏ giá ngoại lai theo IQR",
    }
    gia = bang.loc[
        bang["snapshot_date"].eq(moc) & bang["kpi_ten"].eq(ten_gia)
        & bang["quy_tac"].isin(nhan)
    ].set_index("quy_tac").reindex(nhan)
    truoc = gia.loc["kpi_truoc_sau", ["kpi_truoc", "n_truoc"]]
    if truoc.isna().any() or pd.isna(gia.loc["kpi_truoc_sau", "kpi_sau"]):
        return None

    gia = gia.dropna(subset=["kpi_sau", "n_sau"])
    cac_nhan = ["Trước QA", *gia.index.map(nhan)]
    gia_tri = [truoc["kpi_truoc"], *gia["kpi_sau"]]
    so_mau = [truoc["n_truoc"], *gia["n_sau"]]

    nhan_cot = [f"{tri:,.2f}  (n={n:g})" for tri, n in zip(gia_tri, so_mau)]
    mau = [MAU_PHU] + [MAU_CHINH] * len(gia)
    hinh, truc = ve_cot_ngang(cac_nhan, gia_tri, nhan_cot, mau, chieu_cao=4.1)
    thong_ke = "trung vị" if ten_gia == "gia_trung_vi_gbp" else "trung bình"
    truc.set(xlabel=f"Giá {thong_ke} ({don_vi})", ylabel="Cách xử lý giá")
    return luu_hinh(
        hinh, truc, f"{city} | Độ nhạy của KPI giá với quy tắc QA · {moc}",
        "Nguồn: báo cáo QA · n: số giá được dùng · Các kịch bản không thay đổi KPI chính", duong_dan,
    )


def ve_kpi_llm(bang, city, moc, duong_dan):
    """Dùng kỳ tất cả review để không cộng trùng mẫu qua các năm và mốc"""
    bang = bang.loc[bang["ky_review"].eq("tat_ca")]
    toan_mau = chon_kpi(bang, "ty_le_review_tich_cuc", "city", moc=moc)
    theo_vung = chon_kpi(bang, "ty_le_review_tich_cuc", "analysis_area", moc=moc).sort_values("khu_vuc")
    du_lieu = pd.concat([toan_mau.assign(khu_vuc="Toàn mẫu"), theo_vung])
    du_lieu = du_lieu.loc[du_lieu["mau_so"].gt(0)].dropna(subset=["gia_tri"])
    if du_lieu.empty:
        return None

    mau = du_lieu["pham_vi"].map({"city": MAU_PHU, "analysis_area": MAU_CHINH})
    nhan = [
        f"{tri:.1%}  ({n:g}/{ky_vong:g})" for tri, n, ky_vong in
        zip(du_lieu["gia_tri"], du_lieu["mau_so"], du_lieu["mau_ky_vong"])
    ]
    hinh, truc = ve_cot_ngang(du_lieu["khu_vuc"], du_lieu["gia_tri"], nhan, mau, chieu_cao=5)
    truc.set(xlabel="Review có nhãn positive (%)", ylabel="Phạm vi", xlim=(0, 1.29),
             xticks=[0, 0.25, 0.5, 0.75, 1])
    truc.xaxis.set_major_formatter(PercentFormatter(1))
    return luu_hinh(
        hinh, truc, f"{city} | Tỷ lệ review tích cực theo LLM · Tham chiếu vùng {moc}",
        "Trong ngoặc: số review có nhãn hợp lệ / số được chọn · Chỉ hiện nhóm có nhãn", duong_dan,
    )


def ve_khia_canh_llm(ket_qua_llm, aspects, city, duong_dan):
    """Tỷ lệ review được khen/chê từng khía cạnh trong mẫu LLM, mỗi review đếm một lần"""
    so_review = len(ket_qua_llm)
    ty_le = pd.DataFrame({
        ten: ket_qua_llm[cot].map(json.loads).explode().value_counts() / so_review
        for cot, ten in [("positive_aspects", "khen"), ("negative_aspects", "che")]
    }).reindex(aspects).fillna(0).sort_values("che")

    # Hai trục riêng vì tỷ lệ khen lớn hơn tỷ lệ chê hàng chục lần
    hinh, (truc_khen, truc_che) = plt.subplots(1, 2, figsize=(9.4, 4.6), sharey=True)
    for truc, cot, mau, nhan in [
        (truc_khen, "khen", MAU_CHINH, "Review khen (%)"),
        (truc_che, "che", MAU_PHU, "Review chê (%)"),
    ]:
        thanh = truc.barh(ty_le.index, ty_le[cot], color=mau)
        truc.bar_label(thanh, labels=[f"{tri:.1%}" for tri in ty_le[cot]], padding=4, fontsize=9)
        truc.set(xlabel=nhan)
        truc.margins(x=0.3)
        truc.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        truc.grid(axis="x", alpha=0.25)
    truc_khen.set_ylabel("Khía cạnh")
    return luu_hinh(
        hinh, truc_khen, f"{city} | Khía cạnh được khen và bị chê theo LLM · {so_review} review mẫu",
        "Một review có thể nhắc nhiều khía cạnh · Sắp theo tỷ lệ bị chê", duong_dan,
    )


def ve_tich_cuc_theo_nam(bang, city, duong_dan):
    """Tỷ lệ review tích cực toàn mẫu theo năm viết, chỉ giữ năm đủ mẫu"""
    theo_nam = bang.loc[bang["pham_vi"].eq("city") & bang["ky_review"].ne("tat_ca") & la_dung(bang["du_mau"])]
    theo_nam = theo_nam.dropna(subset=["gia_tri"]).sort_values("ky_review")
    if theo_nam.empty:
        return None

    nam = theo_nam["ky_review"].astype(int)
    hinh, truc = plt.subplots(figsize=(9.4, 4.4))
    truc.plot(nam, theo_nam["gia_tri"], "o-", color=MAU_CHINH)
    for x, y, n in zip(nam, theo_nam["gia_tri"], theo_nam["mau_so"]):
        truc.annotate(f"n={n:g}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    truc.set(xlabel="Năm viết review", ylabel="Review tích cực (%)", ylim=(0.5, 1.05), xticks=nam)
    truc.yaxis.set_major_formatter(PercentFormatter(1))
    truc.grid(axis="y", alpha=0.25)
    return luu_hinh(
        hinh, truc, f"{city} | Tỷ lệ review tích cực theo năm viết (nhãn LLM)",
        "Mỗi review đếm một lần · Chỉ hiện năm có review từ ít nhất 10 chỗ ở · n: số review", duong_dan,
    )


def ve_bat_thuong(bang, city, don_vi, duong_dan):
    """Giá và mức sẵn có theo quận, ghi tên các quận bị z-score đánh dấu"""
    diem = bang.pivot(index="khu_vuc", columns="chi_so", values="gia_tri")
    if not {"log10_gia", "ty_le_san_co"}.issubset(diem.columns):
        return None
    bat_thuong = bang.loc[bang["bat_thuong"]]

    hinh, truc = plt.subplots(figsize=(9.4, 5.2))
    truc.scatter(10 ** diem["log10_gia"], diem["ty_le_san_co"], color=MAU_TRONG, edgecolor=MAU_CHU, s=45)
    for khu_vuc, nhom in bat_thuong.groupby("khu_vuc"):
        ten = nhom["chi_so"].map({"log10_gia": "giá", "ty_le_san_co": "sẵn có", "thay_doi_san_co": "thay đổi sẵn có"})
        nhan = ", ".join(f"{chi_so} z={z:+.1f}" for chi_so, z in zip(ten, nhom["z"]))
        x, y = 10 ** diem.loc[khu_vuc, "log10_gia"], diem.loc[khu_vuc, "ty_le_san_co"]
        truc.scatter(x, y, color=MAU_PHU, s=60, zorder=3)
        truc.annotate(f"{khu_vuc}\n{nhan}", (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    truc.set(xscale="log", xlabel=f"Giá niêm yết trung vị ({don_vi}, thang log)", ylabel="Tỷ lệ ngày sẵn có mốc cuối (%)",
             xticks=[100, 150, 200, 300], xticklabels=["100", "150", "200", "300"])
    truc.xaxis.set_minor_formatter("")
    truc.yaxis.set_major_formatter(PercentFormatter(1))
    truc.grid(alpha=0.25)
    return luu_hinh(
        hinh, truc, f"{city} | Quận lệch so với các quận khác (|z| ≥ 2)",
        f"Mỗi điểm là một quận có ít nhất 10 chỗ ở · Thay đổi sẵn có tính từ {bang['moc_dau'].iloc[0]} "
        f"đến {bang['moc_cuoi'].iloc[0]}", duong_dan,
    )


def ve_danh_gia(bang, city, duong_dan):
    """Dùng điểm và khoảng tin cậy do evaluate tính trên nhãn tay"""
    diem = bang.loc[bang["tieu_chi"].eq("sentiment")].set_index("phuong_phap")
    diem = diem.reindex(["baseline", "llm"]).dropna(subset=["accuracy", "f1", "so_review"])
    if len(diem) != 2:
        return None

    hinh, truc = plt.subplots(figsize=(8.6, 4.6))
    for cach, lech, mau in [("baseline", -0.17, MAU_PHU), ("llm", 0.17, MAU_CHINH)]:
        cot = truc.bar([lech, 1 + lech], diem.loc[cach, ["accuracy", "f1"]], width=0.34,
                       label="Baseline" if cach == "baseline" else "LLM", color=mau)
        truc.bar_label(cot, labels=[f"{tri:.1%}" for tri in cot.datavalues], padding=4)
    truc.set(xticks=[0, 1], xticklabels=["Accuracy", "Macro F1"], ylabel="Điểm (%)",
             ylim=(0, 1.13), yticks=[0, 0.25, 0.5, 0.75, 1])
    truc.yaxis.set_major_formatter(PercentFormatter(1))
    truc.legend(loc="upper right", bbox_to_anchor=(1, 1.12), ncols=2, frameon=False)
    truc.grid(axis="y", alpha=0.25)

    ghi_chu = f"Cùng bộ {diem.loc['llm', 'so_review']:g} review có nhãn tay"
    chenh = bang.loc[bang["tieu_chi"].eq("chenh_accuracy_sentiment")]
    if len(chenh) == 1:
        dong = chenh.iloc[0]
        ghi_chu += (
            f" · LLM − baseline: {100 * dong['accuracy']:+.1f} điểm %"
            f"\nKhoảng tin cậy 95%: [{100 * dong['ci95_lower']:+.1f}; {100 * dong['ci95_upper']:+.1f}] điểm %"
            f" · Bootstrap theo chỗ ở: {dong['so_lan_bootstrap']:g} lần, seed {dong['seed']:g}"
        )
    return luu_hinh(hinh, truc, f"{city} | Đánh giá nhãn cảm xúc: LLM và baseline", ghi_chu, duong_dan)


def xuat_hinh(cau_hinh, *, snapshot=None, thu_muc_du_an=THU_MUC_DU_AN,
              thu_muc_kpi=None, thu_muc_bao_cao=None, thu_muc_xuat=None, co_danh_gia=True):
    """Đọc kết quả có sẵn và trả danh sách đường dẫn hình vừa tạo"""
    cac_moc = chon_cac_moc(cau_hinh, snapshot)

    thu_muc_kpi = thu_muc_kpi or thu_muc_du_an / "data/processed"
    thu_muc_bao_cao = thu_muc_bao_cao or thu_muc_du_an / "reports"
    thu_muc_xuat = thu_muc_xuat or thu_muc_du_an / "figures"
    kpi = cau_hinh["kpi"]
    city = cau_hinh["city"]
    ten_thanh_pho = city.title()
    moc_cuoi = cac_moc[-1]
    moc_gia = kpi["price_snapshot"]
    so_ngay = kpi["calendar_horizon_days"]
    min_n = kpi["min_n"]
    don_vi = f"{cau_hinh['currency']}/đêm"
    ten_gia = ten_kpi_gia(kpi)
    hau_to = f"_{snapshot}" if snapshot else ""

    def doc_kpi(ten):
        bang = pd.read_csv(thu_muc_kpi / f"kpi_{ten}{hau_to}.csv")
        return bang.loc[bang["city"].eq(city) & bang["snapshot_date"].isin(cac_moc)]

    def tep_hinh(ten):
        return thu_muc_xuat / f"{ten}{hau_to}.png"

    listings = doc_kpi("listings")
    lich = doc_kpi("calendar")
    for ten, bang in [("listings", listings), ("calendar", lich)]:
        moc_thieu = set(cac_moc) - set(bang["snapshot_date"])
        if moc_thieu:
            raise ValueError(f"KPI {ten} của {city} thiếu mốc {sorted(moc_thieu)}")

    thu_muc_xuat.mkdir(parents=True, exist_ok=True)
    duong_dan_geo = thu_muc_du_an / "data/raw" / city / moc_cuoi / "neighbourhoods.geojson"
    bao_cao_qa = thu_muc_bao_cao / f"qa_report{hau_to}.csv"
    tep_llm = thu_muc_kpi / f"kpi_llm{hau_to}.csv"
    tep_nhan_llm = thu_muc_kpi / "llm_results.csv"
    tep_danh_gia = thu_muc_bao_cao / "evaluation_metrics.csv"

    with plt.rc_context({
        "font.family": "DejaVu Sans", "font.size": 10, "text.color": MAU_CHU,
        "axes.labelcolor": MAU_CHU, "axes.titleweight": "bold", "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "figure.constrained_layout.use": True,
    }):
        cac_hinh = [
            ve_ban_do(listings, duong_dan_geo, ten_thanh_pho, moc_cuoi, tep_hinh("01_cho_o_theo_quan")),
            ve_lich_theo_moc(lich, ten_thanh_pho, cac_moc, so_ngay, tep_hinh("02_lich_theo_moc")),
            ve_lich_theo_vung(lich, ten_thanh_pho, cac_moc, so_ngay, min_n, tep_hinh("03_lich_theo_vung")),
        ]
        if moc_gia in cac_moc:
            cac_hinh.append(ve_gia_theo_quan(
                listings, ten_thanh_pho, moc_gia, ten_gia, don_vi, min_n, tep_hinh("04_gia_theo_quan"),
            ))
            if bao_cao_qa.is_file():
                cac_hinh.append(ve_do_nhay_gia(
                    pd.read_csv(bao_cao_qa), ten_thanh_pho, moc_gia, ten_gia, don_vi,
                    tep_hinh("05_do_nhay_gia_qa"),
                ))
            else:
                print(f"[BỎ QUA] Chưa có {bao_cao_qa.name} để vẽ độ nhạy giá")

        hinh_llm = None
        if tep_llm.is_file():
            hinh_llm = ve_kpi_llm(doc_kpi("llm"), ten_thanh_pho, moc_cuoi, tep_hinh("06_review_tich_cuc_llm"))
        if hinh_llm is None:
            print(f"[BỎ QUA] {tep_llm.name} chưa có KPI LLM hợp lệ cho mốc {moc_cuoi}")
        cac_hinh.append(hinh_llm)
        if tep_llm.is_file():
            cac_hinh.append(ve_tich_cuc_theo_nam(
                doc_kpi("llm"), ten_thanh_pho, tep_hinh("09_review_tich_cuc_theo_nam"),
            ))
        tep_bat_thuong = thu_muc_kpi / f"kpi_bat_thuong{hau_to}.csv"
        if tep_bat_thuong.is_file():
            cac_hinh.append(ve_bat_thuong(
                pd.read_csv(tep_bat_thuong), ten_thanh_pho, don_vi, tep_hinh("10_bat_thuong_theo_quan"),
            ))
        if tep_nhan_llm.is_file():
            cac_hinh.append(ve_khia_canh_llm(
                pd.read_csv(tep_nhan_llm, dtype="string"), cau_hinh["llm"]["aspects"], ten_thanh_pho,
                tep_hinh("07_khia_canh_llm"),
            ))

        # Báo cáo đánh giá mặc định thuộc mẫu ở mốc cuối của cấu hình
        if co_danh_gia and moc_cuoi == max(cau_hinh["snapshots"]) and tep_danh_gia.is_file():
            cac_hinh.append(ve_danh_gia(
                pd.read_csv(tep_danh_gia), ten_thanh_pho, tep_hinh("08_llm_so_voi_baseline"),
            ))

    return [hinh for hinh in cac_hinh if hinh is not None]


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(description="Sinh hình từ kết quả KPI, QA và đánh giá Airbnb")
    trinh_doc_tham_so.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc_tham_so.add_argument("--snapshot")
    trinh_doc_tham_so.add_argument("--kpi-dir", type=Path)
    trinh_doc_tham_so.add_argument("--reports-dir", type=Path)
    trinh_doc_tham_so.add_argument("--output-dir", type=Path)
    tham_so = trinh_doc_tham_so.parse_args()

    try:
        cau_hinh = doc_cau_hinh(tham_so.config)
        cac_hinh = xuat_hinh(
            cau_hinh, snapshot=tham_so.snapshot, thu_muc_kpi=tham_so.kpi_dir,
            thu_muc_bao_cao=tham_so.reports_dir, thu_muc_xuat=tham_so.output_dir,
        )
    except (ValueError, OSError) as loi:
        trinh_doc_tham_so.exit(1, f"[VIZ LỖI] {loi}\n")

    for hinh in cac_hinh:
        print(f"[ĐÃ VẼ] {hinh}")


if __name__ == "__main__":
    main()
