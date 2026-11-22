"""Chạy quy trình Airbnb từ cấu hình đến bảng kết quả và hình"""

from argparse import ArgumentParser
from pathlib import Path

from src.baseline import chay_baseline
from src.common import CAU_HINH_MAC_DINH, THU_MUC_DU_AN, doc_cau_hinh, doc_phan_cong, duong_dan_reviews_qa
from src.download import tai_du_lieu
from src.evaluate import chay_danh_gia
from src.kpi import xuat_kpi
from src.llm import chay_llm
from src.prepare import chuan_bi_du_lieu
from src.qa import kiem_tra_du_lieu
from src.viz import xuat_hinh


def chay_pipeline(cau_hinh: dict, *, skip_llm: bool = False,
                  duong_dan_nhan_tay: Path | None = None) -> list[Path]:
    """Gọi các mô-đun theo thứ tự phụ thuộc và trả danh sách hình vừa tạo"""
    thu_muc_du_lieu = THU_MUC_DU_AN / "data"
    thu_muc_xu_ly = thu_muc_du_lieu / "processed"
    thu_muc_bao_cao = THU_MUC_DU_AN / "reports"

    if duong_dan_nhan_tay is not None and not duong_dan_nhan_tay.is_file():
        raise FileNotFoundError(f"Không tìm thấy tệp nhãn tay {duong_dan_nhan_tay}")
    nhan_tay = duong_dan_nhan_tay or thu_muc_du_lieu / "samples" / "nhan_tay.csv"

    thanh_pho = cau_hinh["city"]
    reviews_qa = duong_dan_reviews_qa(cau_hinh)
    ket_qua_llm = thu_muc_xu_ly / "llm_results.csv"
    ket_qua_baseline = thu_muc_xu_ly / "baseline_results.csv"
    phan_cong, _ = doc_phan_cong(thu_muc_du_lieu / "assignment", cau_hinh)

    print(f"[1/8] Tải hoặc kiểm tra dữ liệu {thanh_pho}: {', '.join(sorted(cau_hinh['snapshots']))}", flush=True)
    tai_du_lieu(cau_hinh, tai_lai=cau_hinh["download"].get("tai_lai", False))

    print("[2/8] Chuẩn bị listings, calendar và reviews theo phân công", flush=True)
    chuan_bi_du_lieu(cau_hinh, phan_cong, thu_muc_du_lieu / "raw", thu_muc_xu_ly)

    print("[3/8] Gắn cờ và xuất báo cáo QA", flush=True)
    kiem_tra_du_lieu(cau_hinh, phan_cong=phan_cong)

    # LLM và baseline đọc cùng mẫu ở mốc cuối để đối chiếu theo review_id.
    # Khi cache đã đủ nhãn, bước LLM không gọi API nên chạy được khi không có khóa.
    print("[4/8] Trích xuất nhãn LLM", flush=True)
    chay_llm(cau_hinh, reviews_qa, thu_muc_xu_ly, THU_MUC_DU_AN / cau_hinh["llm"]["cache"], skip_llm=skip_llm)

    print("[5/8] Gán nhãn baseline", flush=True)
    chay_baseline(cau_hinh, reviews_qa, ket_qua_baseline)

    print("[6/8] Tổng hợp KPI sau QA", flush=True)
    xuat_kpi(cau_hinh, duong_dan_llm=ket_qua_llm)

    print("[7/8] Đánh giá LLM và baseline trên nhãn tay", flush=True)
    co_nhan_tay = nhan_tay.is_file()
    if co_nhan_tay:
        chay_danh_gia(cau_hinh, reviews_qa, nhan_tay, ket_qua_llm, ket_qua_baseline, thu_muc_bao_cao)
    else:
        print(f"[BỎ QUA] Chưa có {nhan_tay}. Cần nhãn tay để hoàn tất phần đánh giá", flush=True)

    print("[8/8] Sinh hình từ KPI và báo cáo", flush=True)
    # Không có nhãn tay thì không vẽ hình đánh giá từ một lần chạy cũ
    return xuat_hinh(cau_hinh, co_danh_gia=co_nhan_tay)


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(description="Chạy toàn bộ quy trình phân tích Airbnb")
    trinh_doc_tham_so.add_argument("--config", type=Path, default=CAU_HINH_MAC_DINH)
    trinh_doc_tham_so.add_argument("--skip-llm", action="store_true",
                                   help="Chỉ dùng cache LLM đã đủ nhãn, không gọi Gemini")
    trinh_doc_tham_so.add_argument("--human-labels", type=Path, help="Tệp nhãn tay dùng để chấm")
    tham_so = trinh_doc_tham_so.parse_args()

    try:
        cau_hinh = doc_cau_hinh(tham_so.config)
        cac_hinh = chay_pipeline(
            cau_hinh, skip_llm=tham_so.skip_llm, duong_dan_nhan_tay=tham_so.human_labels,
        )
    except (ValueError, OSError, RuntimeError, KeyError) as loi:
        trinh_doc_tham_so.exit(1, f"[PIPELINE LỖI] {loi}\n")

    print(f"[HOÀN TẤT] Đã sinh {len(cac_hinh)} hình", flush=True)
    for hinh in cac_hinh:
        print(f"  {hinh.relative_to(THU_MUC_DU_AN)}")


if __name__ == "__main__":
    main()
