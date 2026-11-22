import json

from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from .common import CAM_XUC, CAU_HINH_MAC_DINH, COT_ASPECT, SO_LAN_BOOTSTRAP, THU_MUC_DU_AN
from .common import doc_cau_hinh, duong_dan_reviews_qa, la_dung
from .common import write_csv as ghi_csv


def doc_bang_nhan(duong_dan: Path, cot_can_co: tuple[str, ...] = ()) -> pd.DataFrame:
    """Đọc ID dạng chuỗi để giữ nguyên mã review dài"""
    bang = pd.read_csv(duong_dan, dtype="string", keep_default_na=False)
    cot_thieu = {"review_id", *cot_can_co} - set(bang.columns)
    if cot_thieu:
        raise ValueError(f"{duong_dan.name} thiếu cột: {sorted(cot_thieu)}")

    bang["review_id"] = bang["review_id"].str.strip()
    id_trung = bang.loc[bang["review_id"].duplicated(), "review_id"]
    if bang["review_id"].eq("").any() or not id_trung.empty:
        raise ValueError(f"{duong_dan.name} có review_id trống hoặc trùng: {id_trung.head().tolist()}")
    return bang.set_index("review_id")


def tach_aspect(gia_tri: str, aspects: list[str], *, nhan_tay: bool) -> set[str]:
    """Đọc mảng JSON hoặc ô chọn nhiều giá trị trong bảng nhãn tay"""
    gia_tri = gia_tri.strip()
    if nhan_tay and not gia_tri.startswith("["):
        danh_sach = [muc.strip() for muc in gia_tri.split(",") if muc.strip()]
    else:
        danh_sach = json.loads(gia_tri)

    if not isinstance(danh_sach, list) or any(muc not in aspects for muc in danh_sach):
        raise ValueError(f"Danh sách aspect không hợp lệ: {gia_tri!r}")
    if len(danh_sach) != len(set(danh_sach)):
        raise ValueError(f"Danh sách aspect bị trùng: {gia_tri!r}")
    return set(danh_sach)


def chuan_bi_nhan(
    bang: pd.DataFrame, ten_bang: str, cac_cot: list[str], aspects: list[str], *, nhan_tay: bool = False,
) -> pd.DataFrame:
    """Kiểm các cột được chấm và chuyển danh sách aspect thành tập hợp"""
    cot_thieu = set(cac_cot) - set(bang.columns)
    if cot_thieu:
        raise ValueError(f"{ten_bang} thiếu cột: {sorted(cot_thieu)}")

    bang = bang[cac_cot].copy()
    bang["sentiment"] = bang["sentiment"].str.strip().str.lower()
    sai = ~bang["sentiment"].isin(CAM_XUC)
    if sai.any():
        raise ValueError(f"{ten_bang} có sentiment trống hoặc sai tại ID: {bang.index[sai][:5].tolist()}")

    for cot in COT_ASPECT:
        if cot not in cac_cot:
            continue
        da_tach = []
        for review_id, gia_tri in bang[cot].items():
            try:
                da_tach.append(tach_aspect(gia_tri, aspects, nhan_tay=nhan_tay))
            except ValueError as loi:
                raise ValueError(f"{ten_bang}, ID {review_id}, cột {cot}: {loi}") from loi
        bang[cot] = da_tach

    if "language" in cac_cot:
        bang["language"] = bang["language"].str.strip().str.lower()
        sai = ~bang["language"].str.fullmatch(r"[a-z]{2}|und")
        if sai.any():
            raise ValueError(f"{ten_bang} có language trống hoặc sai tại ID: {bang.index[sai][:5].tolist()}")
    return bang


def tinh_f1(tp: int, fp: int, fn: int) -> dict:
    """Tính điểm từ số nhãn đúng, thừa và thiếu"""
    return {
        "support": tp + fn, "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0,
    }


def cham_mot_cach(
    nhan_tay: pd.DataFrame, du_doan: pd.DataFrame, phuong_phap: str, nhan_macro: list[str],
) -> tuple[list[dict], pd.DataFrame, pd.DataFrame, pd.Series]:
    """Đo điểm, lập ma trận nhầm lẫn và ghi lỗi theo review"""
    diem = {"phuong_phap": phuong_phap, "so_review": len(nhan_tay)}
    dung_cam_xuc = nhan_tay["sentiment"].eq(du_doan["sentiment"])
    nham_lan = pd.crosstab(nhan_tay["sentiment"], du_doan["sentiment"]).reindex(
        index=CAM_XUC, columns=CAM_XUC, fill_value=0,
    )
    diem_theo_lop = []
    for nhan in CAM_XUC:
        tp = int(nham_lan.loc[nhan, nhan])
        fp = int(nham_lan[nhan].sum()) - tp
        fn = int(nham_lan.loc[nhan].sum()) - tp
        diem_theo_lop.append({**diem, "tieu_chi": "sentiment_theo_lop", "nhan": nhan, **tinh_f1(tp, fp, fn)})

    f1_macro = sum(dong["f1"] for dong in diem_theo_lop if dong["nhan"] in nhan_macro) / len(nhan_macro)
    cac_diem = [{**diem, "tieu_chi": "sentiment", "accuracy": dung_cam_xuc.mean(), "f1": f1_macro}]
    cac_diem.extend(diem_theo_lop)

    loi = pd.DataFrame({"phuong_phap": phuong_phap, "sai_sentiment": ~dung_cam_xuc}, index=nhan_tay.index)
    loi["sentiment_nhan_tay"] = nhan_tay["sentiment"]
    loi["sentiment_du_doan"] = du_doan["sentiment"]
    co_loi = ~dung_cam_xuc

    for cot in COT_ASPECT:
        if cot not in nhan_tay:
            continue

        # Mỗi cặp review và aspect đóng góp một lượt đếm trong micro-F1
        thieu = nhan_tay[cot] - du_doan[cot]
        thua = du_doan[cot] - nhan_tay[cot]
        fn, fp = int(thieu.map(len).sum()), int(thua.map(len).sum())
        tp = int(nhan_tay[cot].map(len).sum()) - fn
        cac_diem.append({**diem, "tieu_chi": cot, **tinh_f1(tp, fp, fn)})
        co_loi |= thieu.map(bool) | thua.map(bool)
        loi[f"{cot}_thieu"] = thieu.map(lambda tap: json.dumps(sorted(tap), ensure_ascii=False))
        loi[f"{cot}_thua"] = thua.map(lambda tap: json.dumps(sorted(tap), ensure_ascii=False))

    if "language" in nhan_tay:
        dung_ngon_ngu = nhan_tay["language"].eq(du_doan["language"])
        cac_diem.append({**diem, "tieu_chi": "language", "accuracy": dung_ngon_ngu.mean()})
        loi["language_nhan_tay"] = nhan_tay["language"]
        loi["language_du_doan"] = du_doan["language"]
        co_loi |= ~dung_ngon_ngu

    nham_lan.index.name = "nhan_tay"
    nham_lan.insert(0, "support", nham_lan.sum(axis=1))
    nham_lan.insert(0, "phuong_phap", phuong_phap)
    return cac_diem, nham_lan.reset_index(), loi.loc[co_loi], dung_cam_xuc


def chay_danh_gia(
    cau_hinh: dict, duong_dan_reviews: Path, duong_dan_nhan_tay: Path,
    duong_dan_llm: Path, duong_dan_baseline: Path, thu_muc_ket_qua: Path, *, danh_gia_ngon_ngu: bool = False,
) -> pd.DataFrame:
    """Chấm đúng mẫu nhãn tay đã giao và xuất ba bảng báo cáo"""
    reviews = doc_bang_nhan(
        duong_dan_reviews, ("human_sample", "du_dieu_kien_llm", "comments", "listing_id"),
    )
    # Chỉ chấm review nhãn tay còn trong dữ liệu và đạt QA; mốc khác có thể mất một vài review
    id_mau = reviews.index[la_dung(reviews["human_sample"]) & la_dung(reviews["du_dieu_kien_llm"])]
    if id_mau.empty:
        raise ValueError("Không có review human_sample=True nào đạt QA để chấm")
    if len(id_mau) < 100:  # Đề yêu cầu ít nhất 100 nhãn tay
        print(f"[CẢNH BÁO] Chỉ còn {len(id_mau)} review nhãn tay trong dữ liệu để chấm", flush=True)

    nhan_tay = doc_bang_nhan(duong_dan_nhan_tay)
    id_thieu = id_mau.difference(nhan_tay.index)
    if len(id_thieu):
        raise ValueError(f"Nhãn tay thiếu {len(id_thieu)} ID trong mẫu: {id_thieu[:5].tolist()}")

    cac_cot = ["sentiment"] + [cot for cot in COT_ASPECT if cot in nhan_tay]
    if danh_gia_ngon_ngu:
        cac_cot.append("language")
    aspects = cau_hinh["llm"]["aspects"]
    nhan_tay = chuan_bi_nhan(nhan_tay.loc[id_mau], "Nhãn tay", cac_cot, aspects, nhan_tay=True)

    cac_du_doan = {}
    for ten, duong_dan in [("llm", duong_dan_llm), ("baseline", duong_dan_baseline)]:
        bang = doc_bang_nhan(duong_dan)
        id_thieu = id_mau.difference(bang.index)
        if len(id_thieu):
            raise ValueError(f"{ten} thiếu {len(id_thieu)} ID trong mẫu nhãn tay: {id_thieu[:5].tolist()}")
        cac_du_doan[ten] = chuan_bi_nhan(bang.loc[id_mau], ten, cac_cot, aspects)

    # Dùng cùng tập lớp xuất hiện ở nhãn tay hoặc một trong hai bảng dự đoán
    cac_nhan = set(nhan_tay["sentiment"])
    for bang in cac_du_doan.values():
        cac_nhan.update(bang["sentiment"])
    nhan_macro = [nhan for nhan in CAM_XUC if nhan in cac_nhan]

    cac_diem, cac_nham_lan, cac_loi, dung_cam_xuc = [], [], [], {}
    for ten, bang in cac_du_doan.items():
        diem, nham_lan, loi, dung = cham_mot_cach(nhan_tay, bang, ten, nhan_macro)
        cac_diem.extend(diem)
        cac_nham_lan.append(nham_lan)
        cac_loi.append(loi)
        dung_cam_xuc[ten] = dung.astype(int)

    # Lấy mẫu lại theo listing để các review cùng chỗ ở đi cùng nhau
    chenh = dung_cam_xuc["llm"] - dung_cam_xuc["baseline"]
    theo_listing = chenh.groupby(reviews.loc[id_mau, "listing_id"]).agg(["sum", "size"])
    so_listing = len(theo_listing)
    rng = np.random.default_rng(cau_hinh["seed"])
    mau_lai = rng.integers(so_listing, size=(SO_LAN_BOOTSTRAP, so_listing))
    tong_chenh = theo_listing["sum"].to_numpy()[mau_lai].sum(axis=1)
    so_review = theo_listing["size"].to_numpy()[mau_lai].sum(axis=1)
    chenh_bootstrap = tong_chenh / so_review
    can_duoi, can_tren = np.quantile(chenh_bootstrap, [0.025, 0.975])
    cac_diem.append({
        "phuong_phap": "llm_tru_baseline", "tieu_chi": "chenh_accuracy_sentiment",
        "so_review": len(id_mau), "accuracy": chenh.mean(), "ci95_lower": can_duoi, "ci95_upper": can_tren,
        "so_listing": so_listing, "so_lan_bootstrap": SO_LAN_BOOTSTRAP, "seed": cau_hinh["seed"],
    })

    ket_qua = pd.DataFrame(cac_diem)
    loi = pd.concat(cac_loi).join(reviews["comments"]).reset_index()
    ghi_csv(thu_muc_ket_qua / "evaluation_metrics.csv", ket_qua)
    ghi_csv(thu_muc_ket_qua / "evaluation_confusion.csv", pd.concat(cac_nham_lan, ignore_index=True))
    ghi_csv(thu_muc_ket_qua / "evaluation_errors.csv", loi)
    return ket_qua


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(description="So sánh LLM và baseline trên mẫu nhãn tay")
    thu_muc_du_lieu = THU_MUC_DU_AN / "data"
    thu_muc_da_xu_ly = thu_muc_du_lieu / "processed"
    trinh_doc_tham_so.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc_tham_so.add_argument("--reviews", type=Path, help="Bảng reviews_qa.csv chứa cờ human_sample")
    trinh_doc_tham_so.add_argument("--human-labels", type=Path, default=thu_muc_du_lieu / "samples/nhan_tay.csv")
    trinh_doc_tham_so.add_argument("--llm", type=Path, default=thu_muc_da_xu_ly / "llm_results.csv")
    trinh_doc_tham_so.add_argument("--baseline", type=Path, default=thu_muc_da_xu_ly / "baseline_results.csv")
    trinh_doc_tham_so.add_argument("--output-dir", type=Path, default=THU_MUC_DU_AN / "reports")
    trinh_doc_tham_so.add_argument(
        "--danh-gia-ngon-ngu", action="store_true", help="Dùng khi ngôn ngữ đã được người gán nhãn kiểm tra",
    )
    tham_so = trinh_doc_tham_so.parse_args()

    try:
        cau_hinh = doc_cau_hinh(tham_so.config)
        duong_dan_reviews = tham_so.reviews or duong_dan_reviews_qa(cau_hinh)
        chay_danh_gia(
            cau_hinh, duong_dan_reviews, tham_so.human_labels, tham_so.llm, tham_so.baseline,
            tham_so.output_dir, danh_gia_ngon_ngu=tham_so.danh_gia_ngon_ngu,
        )
    except (ValueError, OSError) as loi:
        trinh_doc_tham_so.exit(1, f"[ĐÁNH GIÁ LỖI] {loi}\n")

    print(f"[HOÀN TẤT] Kết quả đánh giá ở {tham_so.output_dir}")


if __name__ == "__main__":
    main()
