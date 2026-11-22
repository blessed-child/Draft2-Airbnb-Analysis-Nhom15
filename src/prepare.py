from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from .common import CAU_HINH_MAC_DINH, THU_MUC_DU_AN, doc_cau_hinh, doc_phan_cong
from .common import chuyen_dung_sai, kiem_tra_id_phan_cong, kiem_tra_phan_cong_review
from .common import write_csv as ghi_csv


def bao_id_thieu(id_thuc_te: pd.Series, id_phan_cong: pd.Series, ten_bang: str, moc_chup: str) -> None:
    """Mốc khác có thể thiếu một phần ID được giao; chỉ dừng khi không còn ID nào, phần thiếu QA ghi ở thieu_id_phan_cong"""
    so_thieu = (~id_phan_cong.isin(id_thuc_te)).sum()
    if so_thieu == len(id_phan_cong):
        raise ValueError(f"{ten_bang} mốc {moc_chup} không có ID nào thuộc phân công")
    if so_thieu:
        print(f"[CẢNH BÁO] {ten_bang} mốc {moc_chup} thiếu {so_thieu} ID được giao", flush=True)


# mục 1 - 9
def chuan_bi_cho_o_mot_moc(duong_dan_nguon: Path, phan_cong: pd.DataFrame, moc_gia: str) -> pd.DataFrame:
    """Lọc ID, ghép vùng và chuẩn hóa listings của một mốc"""
    moc_chup = duong_dan_nguon.parent.name # hiểu đơn giản thì mốc chụp là tên của cái thư mục snapshot chứa các bản csv cần thiết
    du_lieu_tho = pd.read_csv(duong_dan_nguon, dtype=str, keep_default_na=False) # đọc đường dẫn

    # So khớp cả cột ID một lần, giữ nguyên các cột nguồn của dòng thuộc nhóm
    id_phan_cong = phan_cong["listing_id"] # Lấy ID từ bảng phân công data/assignment/listings.csv
    thuoc_nhom = du_lieu_tho["id"].isin(id_phan_cong) # kiểm tra những id trùng khớp nhau trong hai bảng để lọc ra 1000 id
    du_lieu = du_lieu_tho.loc[thuoc_nhom].rename(columns={"id": "listing_id", "price": "price_raw"}) # cái này đơn giản chỉ là đổi tên cột cho dễ đọc với dễ xử lý thôi hahaaha
    du_lieu = du_lieu.merge(phan_cong, on="listing_id", how="left", validate="many_to_one") # bước này là merge hai bảng phân công và bảng nguồn lại thành một theo id

    bao_id_thieu(du_lieu["listing_id"], id_phan_cong, "Listings", moc_chup) # báo nếu mốc này thiếu id được giao
    if du_lieu["analysis_area"].fillna("").str.strip().eq("").any():
        raise ValueError(f"Mốc {moc_chup} có listing thiếu vùng phân công") # kiểm tra xem có bị thiếu vùng phân công hay không

    du_lieu["snapshot_date"] = pd.to_datetime(moc_chup, format="%Y-%m-%d") # tạo cột snapshot_date với mốc chụp hiện tại
    du_lieu["listing_id"] = du_lieu["listing_id"].astype("string") # chuyển toàn bộ id thành string

    cot_toa_do = ["latitude", "longitude"]
    cot_so_dem_va_review = ["minimum_nights", "number_of_reviews"]
    # Giữ dòng có ô sai kiểu và giữ cả số lẻ để QA gắn cờ.
    du_lieu[cot_toa_do] = du_lieu[cot_toa_do].apply(pd.to_numeric, errors="coerce")
    du_lieu[cot_so_dem_va_review] = du_lieu[cot_so_dem_va_review].apply(pd.to_numeric, errors="coerce")

    du_lieu["price_gbp"] = pd.Series(pd.NA, index=du_lieu.index, dtype="Float64") # đây là bước xử lý giá tiền nhé
    if moc_chup == moc_gia: # cái đoạn này sẽ khó hiểu hơn đấy, ít nhất là đối với t =))
        # Giữ giá nguồn để QA phân biệt ô thiếu với giá không chuyển được sang số
        gia_dang_chuoi = (
            du_lieu["price_raw"].astype("string").str.strip()
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .replace("", pd.NA)
        )
        du_lieu["price_gbp"] = pd.to_numeric(gia_dang_chuoi, errors="coerce").astype("Float64")

    return du_lieu


# mục 9
# cái hàm bên dưới này là xử lý cho những mốc snapshot còn lại nhé
def xu_ly_cho_o(
    cau_hinh: dict, # dict đã đọc từ YAML, chứa các mục như city và snapshots
    thu_muc_tho: Path, # trỏ tới thư mục dữ liệu thô
    thu_muc_ket_qua: Path, # trỏ tới nơi ghi CSV đã xử lý
    *,
    phan_cong: pd.DataFrame, # bảng phân công listing đã được kiểm ở doc_phan_cong
) -> None:
    """Xử lý các mốc bằng phân công đã kiểm"""
    thanh_pho = cau_hinh["city"] # london
    danh_sach_moc = cau_hinh["snapshots"] # ['2025-09-14', '2025-12-13', '2026-03-21', '2026-06-19']

    moc_gia = cau_hinh["kpi"]["price_snapshot"] # 2026-06-19

    phan_cong = phan_cong[["listing_id", "analysis_area"]]
    cac_bang_theo_moc = {} # tạo một cái dict rỗng tí nữa sẽ thêm output vào cái này
    for moc_chup in danh_sach_moc:
        duong_dan_nguon = thu_muc_tho / thanh_pho / moc_chup / "listings.csv.gz"
        cac_bang_theo_moc[moc_chup] = chuan_bi_cho_o_mot_moc( # cái này chính là gọi lại cái hàm def ban đầu đó
            duong_dan_nguon, phan_cong, moc_gia
        )

    du_lieu_tong_hop = pd.concat(cac_bang_theo_moc.values(), ignore_index=True, sort=False) # nối 4 bảng 1000 dòng thành 1 bảng mới có 4000 dòng
    thu_muc_thanh_pho = thu_muc_ket_qua / thanh_pho # cái / là để ghép đường dẫn -> data/processed/london/
    for moc_chup, du_lieu in cac_bang_theo_moc.items():
        ghi_csv(thu_muc_thanh_pho / moc_chup / "listings_assigned.csv", du_lieu) # cái này là ghi thành 4 file riêng đã xử lý
    ghi_csv(thu_muc_thanh_pho / "listings_all_snapshots.csv", du_lieu_tong_hop) # ghi chung 4 file đã xử lý


# mục 10
def loc_lich_mot_moc(duong_dan_nguon: Path, id_phan_cong: pd.Series) -> pd.DataFrame:
    """Mục 10: giữ dòng lịch thuộc ID phân công, dùng chung quy tắc kiểm ID"""
    kiem_tra_id_phan_cong(id_phan_cong, "listing_id")

    cac_khoi_da_loc = []
    with pd.read_csv(
        duong_dan_nguon,
        usecols=["listing_id", "date", "available"],
        dtype="string",
        keep_default_na=False,
        chunksize=200_000,
    ) as cac_khoi_lich:
        # chia thành các khối 200000 dòng rồi lọc ra những id khớp với phân công, sau đó thêm vào list rỗng
        for khoi_lich in cac_khoi_lich:
            thuoc_nhom = khoi_lich["listing_id"].isin(id_phan_cong) # hàm này trả về true false để lấy 1000 id khớp này
            cac_khoi_da_loc.append(khoi_lich.loc[thuoc_nhom]) # thêm vào list rỗng những dòng khớp với phân công

    du_lieu_lich = pd.concat(cac_khoi_da_loc, ignore_index=True) # nối các dataframe nhỏ đã được lưu thành 1 dataframe lớn
    moc_chup = duong_dan_nguon.parent.name
    bao_id_thieu(du_lieu_lich["listing_id"], id_phan_cong, "Calendar", moc_chup)

    du_lieu_lich["snapshot_date"] = moc_chup # thêm cột snapshot_date với giá trị là mốc chụp hiện tại
    return du_lieu_lich


# mục 11
def chuan_hoa_lich(du_lieu_lich: pd.DataFrame) -> pd.DataFrame:
    """Mục 11: chuẩn hóa ngày, trạng thái và kiểm tra khóa của bảng lịch"""
    du_lieu = du_lieu_lich.rename(columns={"date": "calendar_date"}) # cái này là đổi tên đó bro
    du_lieu["listing_id"] = du_lieu["listing_id"].astype("string") # chuyển id thành string
    du_lieu["snapshot_date"] = pd.to_datetime(du_lieu["snapshot_date"], format="%Y-%m-%d", errors="coerce")
    du_lieu["calendar_date"] = pd.to_datetime(du_lieu["calendar_date"], format="%Y-%m-%d", errors="coerce")

    # Giữ các dòng thiếu hoặc trùng khóa để QA xử lý (qa_khoa_thieu, qa_khoa_trung)

    bang_doi_trang_thai = {"t": True, "f": False}
    # Giữ dòng có trạng thái thiếu hoặc sai để QA gắn cờ.
    du_lieu["available"] = du_lieu["available"].map(bang_doi_trang_thai).astype("boolean")

    return du_lieu


# mục 12
def ghep_vung_vao_lich(du_lieu_lich: pd.DataFrame, du_lieu_cho_o: pd.DataFrame) -> pd.DataFrame:
    """Mục 12: gắn hai cột vùng từ listings của cùng mốc"""
    khoa_ghep = ["snapshot_date", "listing_id"]
    cot_vung = ["analysis_area", "neighbourhood_cleansed"]
    bang_vung = du_lieu_cho_o[khoa_ghep + cot_vung]
    # Chỉ sử dụng các listing có khóa duy nhất để tạo bảng tra vùng
    bang_vung = bang_vung.loc[~bang_vung.duplicated(subset=khoa_ghep, keep=False)]

    du_lieu_da_ghep = du_lieu_lich.merge(
        bang_vung, on=khoa_ghep, how="left", validate="many_to_one"
    )
    # Không dừng toàn bộ chương trình khi có dòng không ghép được,
    # để các cột vùng thiếu giá trị và giao cho QA ghi nhận.
    return du_lieu_da_ghep


# mục 10 - 12
def xu_ly_lich(
    cau_hinh: dict,
    moc_chup: str,
    thu_muc_tho: Path,
    thu_muc_ket_qua: Path,
    *,
    phan_cong: pd.DataFrame,
) -> None:
    """Lọc, chuẩn hóa lịch và ghép vùng của một mốc, ghi một file calendar_assigned.csv"""
    phan_cong = phan_cong[["listing_id", "analysis_area"]]
    thu_muc_theo_moc = Path(cau_hinh["city"]) / moc_chup
    du_lieu_lich = loc_lich_mot_moc(
        thu_muc_tho / thu_muc_theo_moc / "calendar.csv.gz", phan_cong["listing_id"]
    )
    du_lieu_lich = chuan_hoa_lich(du_lieu_lich)
    du_lieu_cho_o = chuan_bi_cho_o_mot_moc(
        thu_muc_tho / thu_muc_theo_moc / "listings.csv.gz", phan_cong, cau_hinh["kpi"]["price_snapshot"]
    )
    du_lieu_da_ghep = ghep_vung_vao_lich(du_lieu_lich, du_lieu_cho_o)
    ghi_csv(thu_muc_ket_qua / thu_muc_theo_moc / "calendar_assigned.csv", du_lieu_da_ghep)


# mục 13
def loc_danh_gia_mot_moc(duong_dan_nguon: Path, id_phan_cong: pd.Series) -> pd.DataFrame:
    """Mục 13: giữ nguyên nội dung các review thuộc danh sách phân công"""
    cac_khoi_da_loc = []
    with pd.read_csv(
        duong_dan_nguon, usecols=["id", "listing_id", "date", "comments"],
        dtype="string", keep_default_na=False, chunksize=100_000,
    ) as cac_khoi_danh_gia: # mỗi lần đọc 100000 review_id
        for khoi_danh_gia in cac_khoi_danh_gia: # lọc id giống nhau trong mỗi vòng lặp rồi thêm vào list rỗng
            thuoc_nhom = khoi_danh_gia["id"].isin(id_phan_cong)
            khoi_da_loc = khoi_danh_gia.loc[thuoc_nhom] # lọc ra những id chuẩn
            cac_khoi_da_loc.append(khoi_da_loc)

    du_lieu_danh_gia = pd.concat(cac_khoi_da_loc, ignore_index=True) # nối tất cả thành một cái dataframe
    moc_chup = duong_dan_nguon.parent.name
    id_da_loc = du_lieu_danh_gia["id"]
    # Giữ các dòng review trùng ID để QA kiểm tra và gắn cờ (qa_khoa_trung)
    bao_id_thieu(id_da_loc, id_phan_cong, "Reviews", moc_chup)

    du_lieu_danh_gia = du_lieu_danh_gia.rename(columns={"id": "review_id"})
    du_lieu_danh_gia["snapshot_date"] = moc_chup
    return du_lieu_danh_gia


def chuan_hoa_phan_cong_review(phan_cong: pd.DataFrame) -> pd.DataFrame:
    """Chuyển hai cờ chọn mẫu sang boolean sau khi kiểm phân công"""
    kiem_tra_phan_cong_review(phan_cong)
    phan_cong = phan_cong.copy()
    for cot in ["llm_sample", "human_sample"]:
        phan_cong[cot] = chuyen_dung_sai(phan_cong[cot])
    return phan_cong


def ghep_co_mau(du_lieu_danh_gia: pd.DataFrame, phan_cong_mau: pd.DataFrame) -> pd.DataFrame:
    # merge hai bảng lại với nhau và có thêm hai cột mới là llm_sample + human_sample
    du_lieu_danh_gia_co_mau = du_lieu_danh_gia.merge(
        phan_cong_mau, on="review_id", how="left", validate="many_to_one",
    )
    cot_co_mau = ["llm_sample", "human_sample"]
    if du_lieu_danh_gia_co_mau[cot_co_mau].isna().any().any():
        raise ValueError("Có review không ghép được cờ chọn mẫu")
    return du_lieu_danh_gia_co_mau


# mục 15
def tach_danh_gia_va_lan_xuat_hien(cac_bang_theo_moc: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    moc_cuoi = max(cac_bang_theo_moc)
    du_lieu_moc_cuoi = cac_bang_theo_moc[moc_cuoi]
    cot_noi_dung = ["listing_id", "date", "comments"]
    cot_doi_chieu = ["review_id", "listing_id", "date", "comments"]

    # Chỉ so sánh các ID không bị trùng trong mốc cuối
    moc_cuoi_khong_trung = du_lieu_moc_cuoi.loc[
        ~du_lieu_moc_cuoi.duplicated(subset="review_id", keep=False), cot_doi_chieu
    ]

    # Mục 15b — Đối chiếu nội dung của cùng review ở hai mốc
    for moc_chup, du_lieu in cac_bang_theo_moc.items():
        if moc_chup == moc_cuoi:
            continue
        # Chỉ so sánh các ID không bị trùng trong từng snapshot
        du_lieu_khong_trung = du_lieu.loc[
            ~du_lieu.duplicated(subset="review_id", keep=False), cot_doi_chieu
        ]
        doi_chieu = du_lieu_khong_trung.merge(
            moc_cuoi_khong_trung, on="review_id",
            how="inner", # giữ những id có mặt ở cả hai bảng, review chỉ có ở một mốc không cần đối chiếu
            suffixes=("_truoc", "_cuoi"), # giúp phân biệt các cột trùng tên
            validate="one_to_one",
        )

        for ten_cot in cot_noi_dung:
            co_khac = doi_chieu[f"{ten_cot}_truoc"].ne(doi_chieu[f"{ten_cot}_cuoi"])
            if co_khac.any():
                id_mau = doi_chieu.loc[co_khac, "review_id"].head(5).tolist()
                raise ValueError(
                    f"Mốc {moc_chup} và {moc_cuoi} có {co_khac.sum()} review khác {ten_cot}. "
                    f"Review ID cần kiểm tra (tối đa 5): {id_mau}."
                )

    # Mục 15c — Tách nội dung review và lần xuất hiện theo snapshot
    # reviews_unique.csv chỉ được tạo từ các bản ghi có ID duy nhất trong snapshot tương ứng.
    # Mỗi review giữ một dòng nội dung, kèm hai cờ chọn mẫu; lấy bản ở mốc muộn nhất có review đó.
    danh_sach_duy_nhat = [
        du_lieu.loc[~du_lieu.duplicated(subset="review_id", keep=False)]
        for moc, du_lieu in sorted(cac_bang_theo_moc.items())
    ]
    danh_gia_duy_nhat = (
        pd.concat(danh_sach_duy_nhat, ignore_index=True)
        .drop_duplicates("review_id", keep="last").drop(columns="snapshot_date")
    )

    # Mỗi dòng cho biết một review có mặt trong một snapshot.
    # review_appearances.csv cần loại bản ghi trùng theo cặp (review_id, snapshot_date) khi tạo bảng tổng hợp.
    cot_lan_xuat_hien = ["review_id", "snapshot_date"]
    lan_xuat_hien = pd.concat(
        [du_lieu[cot_lan_xuat_hien] for du_lieu in cac_bang_theo_moc.values()],
        ignore_index=True,
    ).drop_duplicates(subset=cot_lan_xuat_hien)

    return danh_gia_duy_nhat, lan_xuat_hien


def xu_ly_danh_gia(
    thanh_pho: str, danh_sach_moc: list[str],
    thu_muc_tho: Path, thu_muc_ket_qua: Path, *, tach_bang: bool,
    phan_cong_mau: pd.DataFrame,
) -> None:
    """Chuẩn bị review, nhận cờ mẫu đã kiểm từ bước điều phối"""
    phan_cong_mau = chuan_hoa_phan_cong_review(phan_cong_mau)
    phan_cong_mau = phan_cong_mau[["review_id", "llm_sample", "human_sample"]]
    id_phan_cong = phan_cong_mau["review_id"]

    # Mục 15a dùng lại phần lọc mục 13 cho từng snapshot trong cấu hình.
    cac_bang_theo_moc = {}
    for moc_chup in danh_sach_moc:
        duong_dan_nguon = thu_muc_tho / thanh_pho / moc_chup / "reviews.csv.gz" # lấy đường dẫn của bảng review phân công và nguồn
        du_lieu_danh_gia = loc_danh_gia_mot_moc(duong_dan_nguon, id_phan_cong)
        cac_bang_theo_moc[moc_chup] = ghep_co_mau(du_lieu_danh_gia, phan_cong_mau)

    if tach_bang:
        danh_gia_duy_nhat, lan_xuat_hien = tach_danh_gia_va_lan_xuat_hien(cac_bang_theo_moc)

    thu_muc_thanh_pho = thu_muc_ket_qua / thanh_pho
    for moc_chup, du_lieu in cac_bang_theo_moc.items():
        ghi_csv(thu_muc_thanh_pho / moc_chup / "reviews_assigned.csv", du_lieu)
    if tach_bang:
        ghi_csv(thu_muc_thanh_pho / "reviews_unique.csv", danh_gia_duy_nhat)
        ghi_csv(thu_muc_thanh_pho / "review_appearances.csv", lan_xuat_hien)


def chuan_bi_du_lieu(
    cau_hinh: dict,
    phan_cong: dict[str, pd.DataFrame],
    thu_muc_tho: Path,
    thu_muc_ket_qua: Path,
    bang_can_xu_ly: str = "all",
) -> None:
    """Chạy mục 1–15 cho các bảng được chọn, dùng chung cho CLI và run_pipeline.py"""
    danh_sach_moc = cau_hinh["snapshots"]

    if bang_can_xu_ly in ["all", "listings"]:
        xu_ly_cho_o(
            cau_hinh,
            thu_muc_tho,
            thu_muc_ket_qua,
            phan_cong=phan_cong["listings"],
        )

    if bang_can_xu_ly in ["all", "calendar"]:
        for moc_chup in danh_sach_moc:
            xu_ly_lich(
                cau_hinh,
                moc_chup,
                thu_muc_tho,
                thu_muc_ket_qua,
                phan_cong=phan_cong["listings"],
            )

    if bang_can_xu_ly in ["all", "reviews"]:
        xu_ly_danh_gia(
            cau_hinh["city"],
            danh_sach_moc,
            thu_muc_tho,
            thu_muc_ket_qua,
            tach_bang=True,
            phan_cong_mau=phan_cong["reviews"],
        )


def main() -> None:
    trinh_doc_tham_so = ArgumentParser(
        description="Chuẩn bị listings, calendar và reviews theo phân công"
    )

    trinh_doc_tham_so.add_argument(
        "--config",
        type=Path,
        default=CAU_HINH_MAC_DINH,
    )

    trinh_doc_tham_so.add_argument(
        "--raw-dir",
        type=Path,
        default=THU_MUC_DU_AN / "data" / "raw",
    )

    trinh_doc_tham_so.add_argument(
        "--output-dir",
        type=Path,
        default=THU_MUC_DU_AN / "data" / "processed",
    )

    trinh_doc_tham_so.add_argument(
        "--table",
        choices=["all", "listings", "calendar", "reviews"],
        default="all",
        help="Chọn bảng cần xử lý (listings, calendar, reviews), mặc định xử lý cả ba bảng",
    )

    tham_so = trinh_doc_tham_so.parse_args()
    cau_hinh = doc_cau_hinh(tham_so.config)
    phan_cong, _ = doc_phan_cong(THU_MUC_DU_AN / "data" / "assignment", cau_hinh)
    chuan_bi_du_lieu(cau_hinh, phan_cong, tham_so.raw_dir, tham_so.output_dir, tham_so.table)
    print(f"Hoàn tất chuẩn bị dữ liệu: {tham_so.table}")


if __name__ == "__main__":
    main()
