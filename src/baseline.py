from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from .common import CAU_HINH_MAC_DINH, COT_NHAN, THU_MUC_DU_AN
from .common import doc_cau_hinh, doc_mau_llm, duong_dan_reviews_qa, ghi_nhan_csv


TU_KHEN = set(
    "amazing beautiful best bright cheap clean comfortable convenient cozy cosy easy excellent friendly "
    "good great helpful ideal immaculate love loved lovely nice perfect pleasant quiet recommend "
    "recommended relaxing responsive safe spotless spacious superb welcoming wonderful".split()
)
TU_CHE = set(
    "awful bad broken cold cramped dated difficult dirty disappointing dusty expensive filthy "
    "freezing horrible loud misleading mold mould noisy overpriced poor rude shabby slow small "
    "stained terrible tiny uncomfortable unhelpful unpleasant unresponsive unsafe worst".split()
)
TU_PHU_DINH = {"not", "no", "never"}

TU_KHOA_ASPECT = {
    "vị trí": {"location", "located", "central", "station", "tube", "underground", "transport", "bus", "walk"},
    "sạch sẽ": {"clean", "dirty", "spotless", "immaculate", "dusty", "filthy", "mold", "mould", "stained"},
    "chủ nhà": {"host", "hosts", "hostess", "responsive", "unresponsive", "communication"},
    "giá trị": {"price", "value", "cost", "cheap", "expensive", "overpriced", "worth"},
    "tiện nghi": {"amenities", "kitchen", "shower", "wifi", "heating", "bed", "mattress", "equipment"},
    "độ ồn": {"noise", "noisy", "quiet", "loud", "soundproof", "silent"},
    "an toàn": {"safe", "unsafe", "secure", "security", "lock", "locks"},
    "không gian": {"space", "spacious", "cramped", "roomy", "tiny", "small", "size", "layout"},
}


def gan_nhan_baseline(du_lieu: pd.DataFrame, aspects: list[str]) -> pd.DataFrame:
    """Gán cảm xúc và khía cạnh cho cả cột comments bằng thao tác chuỗi của pandas"""
    van_ban = du_lieu["comments"].str.lower().str.replace("’", "'", regex=False)

    # Tách review thành vế câu, rồi tách vế thành từ; mỗi dòng của bảng tu là một từ
    ve = van_ban.str.split(r"[.!?,;\n]+|<br\s*/?>|\b(?:but|however|although|though|except)\b", regex=True)
    ve = ve.explode().rename_axis("dong").reset_index(name="ve")
    tu = ve["ve"].str.findall(r"[a-z]+(?:'[a-z]+)?").explode().dropna().rename_axis("ma_ve").reset_index(name="tu")
    tu["dong"] = tu["ma_ve"].map(ve["dong"])

    # Phủ định trong ba từ ngay trước từ khen/chê của cùng vế làm đảo dấu
    phu_dinh = (tu["tu"].isin(TU_PHU_DINH) | tu["tu"].str.endswith("n't")).groupby(tu["ma_ve"])
    co_phu_dinh = (phu_dinh.shift(1, fill_value=False) | phu_dinh.shift(2, fill_value=False)
                   | phu_dinh.shift(3, fill_value=False))
    diem = tu["tu"].map({**dict.fromkeys(TU_CHE, -1), **dict.fromkeys(TU_KHEN, 1)})  # khen 1, chê -1
    diem = diem.where(~co_phu_dinh, -diem)
    tu["ve_khen"] = diem.eq(1).groupby(tu["ma_ve"]).transform("any")
    tu["ve_che"] = diem.eq(-1).groupby(tu["ma_ve"]).transform("any")

    # Cả hai phía hoặc không có tín hiệu đều thuộc mixed
    theo_review = tu.groupby("dong")[["ve_khen", "ve_che"]].any().reindex(du_lieu.index, fill_value=False)
    co_khen, co_che = theo_review["ve_khen"], theo_review["ve_che"]
    ket_qua = pd.DataFrame({
        "review_id": du_lieu["review_id"],
        "sentiment": np.select([co_khen & ~co_che, co_che & ~co_khen], ["positive", "negative"], "mixed"),
    })

    # Chỉ gán khía cạnh khi từ khóa và dấu hiệu khen/chê ở cùng vế, giữ thứ tự aspect trong YAML
    tu["aspect"] = tu["tu"].map({tu_khoa: aspect for aspect, cac_tu in TU_KHOA_ASPECT.items() for tu_khoa in cac_tu})
    tu["thu_tu_aspect"] = tu["aspect"].map({aspect: i for i, aspect in enumerate(aspects)})
    for cot, co_ve in [("positive_aspects", "ve_khen"), ("negative_aspects", "ve_che")]:
        cap = tu.loc[tu[co_ve] & tu["thu_tu_aspect"].notna(), ["dong", "thu_tu_aspect", "aspect"]]
        cap = cap.drop_duplicates().sort_values(["dong", "thu_tu_aspect"])
        danh_sach = cap.groupby("dong")["aspect"].agg(list).reindex(du_lieu.index)
        # Review không có khía cạnh nào nhận danh sách rỗng thay vì NaN
        ket_qua[cot] = danh_sach.where(danh_sach.notna(), pd.Series([[]] * len(du_lieu), index=du_lieu.index))

    # Quy ước en cho đối chứng từ khóa tiếng Anh
    ket_qua["language"] = "en"
    return ket_qua[COT_NHAN].reset_index(drop=True)


def chay_baseline(cau_hinh: dict, duong_dan_reviews: Path, duong_dan_ket_qua: Path) -> pd.DataFrame:
    """Đọc đúng mẫu LLM, gán nhãn đối chứng và ghi cùng định dạng với kết quả Gemini"""
    mau_reviews = doc_mau_llm(duong_dan_reviews, cau_hinh["llm"]["sample_size"])
    ket_qua = gan_nhan_baseline(mau_reviews, cau_hinh["llm"]["aspects"])
    ghi_nhan_csv(duong_dan_ket_qua, ket_qua)
    return ket_qua


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(description="Gán nhãn đối chứng bằng từ khóa")
    trinh_doc_tham_so.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc_tham_so.add_argument("--input", type=Path, help="Bảng reviews đã xử lý")
    trinh_doc_tham_so.add_argument("--output", type=Path, help="Đường dẫn lưu bảng nhãn baseline")
    tham_so = trinh_doc_tham_so.parse_args()

    cau_hinh = doc_cau_hinh(tham_so.config)
    duong_dan_reviews = tham_so.input or duong_dan_reviews_qa(cau_hinh)
    duong_dan_ket_qua = tham_so.output or THU_MUC_DU_AN / "data" / "processed" / "baseline_results.csv"
    ket_qua = chay_baseline(cau_hinh, duong_dan_reviews, duong_dan_ket_qua)
    print(f"[HOÀN TẤT] Đã gán nhãn baseline cho {len(ket_qua)} review: {duong_dan_ket_qua}")


if __name__ == "__main__":
    main()
