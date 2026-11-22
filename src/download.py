import csv
import gzip
import json
import zlib
import time
import requests #Bổ sung
from pathlib import Path
from argparse import ArgumentParser
from .common import CAU_HINH_MAC_DINH, THU_MUC_DU_AN, chon_cac_moc, doc_cau_hinh


KICH_THUOC = 1024 * 1024    # 1MiB
SO_LAN_THU = 3              # Số lần tải tối đa cho một tệp khi gặp lỗi mạng

COLUMNS = {                           #Kiểm tra các file cần tải về và các cột cần đọc
    "data/listings.csv.gz": {
        "id",
        "latitude",
        "longitude",
        "neighbourhood_cleansed",
        "room_type",
        "number_of_reviews",
        "minimum_nights",
        "last_scraped",
        "price",
    },
    "data/calendar.csv.gz": {
        "listing_id",
        "date",
        "available",
    },
    "data/reviews.csv.gz": {
        "id",
        "listing_id",
        "date",
        "comments",
    },
    "visualisations/neighbourhoods.geojson": None,  #Để None để thông báo rằng sẽ đọc kiểm tra bằng json thay vì csv
}



def kiem_tra_file(duong_dan_file: Path, columns: set[str] | None = None, doc_het: bool = True) -> None:
    """Kiểm tra tệp không rỗng và đọc được đúng định dạng. Hàm gồm 2 nhánh kiểm tra: nếu columns là None thì đọc file json, 
    nếu columns là set thì đọc file csv và kiểm tra các cột cần thiết.
    doc_het=False chỉ kiểm tiêu đề và dòng đầu, bỏ bước giải nén toàn bộ tệp"""
    if not duong_dan_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy: {duong_dan_file}")

    if duong_dan_file.stat().st_size == 0:
        raise ValueError(f"Tệp rỗng: {duong_dan_file}")

    if columns is None:
        with open(duong_dan_file, "r", encoding="utf-8-sig") as f:
            du_lieu_vung = json.load(f)

        if not isinstance(du_lieu_vung, dict):
            raise ValueError("GeoJSON phải là một đối tượng JSON")

        if du_lieu_vung.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON thiếu FeatureCollection")

        cac_vung = du_lieu_vung.get("features")

        if not isinstance(cac_vung, list) or not cac_vung:
            raise ValueError("GeoJSON không có danh sách vùng")
        return

    with gzip.open(duong_dan_file, "rt", encoding="utf-8-sig", newline="") as f:
        doc_csv = csv.reader(f)
        ten_cac_cot = next(doc_csv, None)

        if not ten_cac_cot:
            raise ValueError("CSV rỗng hoặc dòng đầu tiên trống")

        cac_cot_thieu = (columns - set(ten_cac_cot))

        if cac_cot_thieu:
            raise ValueError(f"CSV thiếu cột: {sorted(cac_cot_thieu)}")

        dong_du_lieu_dau_tien = next(doc_csv, None)

        if not dong_du_lieu_dau_tien:
            raise ValueError("CSV không có dòng dữ liệu")
        # Đọc hết luồng gzip để phát hiện lỗi giải nén hoặc file bị cắt ngắn.
        while doc_het and f.read(KICH_THUOC):
            pass



def tai_file(phien_ket_noi: requests.Session, 
             url_nguon: str, duong_dan_luu: Path, columns: set[str] | None = None, tai_lai: bool = False) -> None:
    """Tải một tệp, kiểm tra rồi lưu thành tệp chính thức"""
    if duong_dan_luu.exists() and not tai_lai:
        kiem_tra_file(duong_dan_luu, columns, doc_het=False)  # Tệp có sẵn đã được kiểm đủ lúc tải nên chỉ kiểm nhanh
        print(f"[DÙNG FILE CÓ SẴN] File đã có và kiểm tra hợp lệ: {duong_dan_luu}", flush=True)
        return

    duong_dan_luu.parent.mkdir(parents=True, exist_ok=True)
    duong_dan_tam_thoi = duong_dan_luu.with_name(duong_dan_luu.name + ".part")

    print(f"[ĐANG TẢI] {url_nguon}", flush=True)

    for lan_thu in range(1, SO_LAN_THU + 1):
        try:
            with phien_ket_noi.get(url_nguon, stream=True, timeout=(10, 60), headers={"Accept-Encoding": "identity"}) as phan_hoi:
                phan_hoi.raise_for_status()

                with duong_dan_tam_thoi.open("wb") as f:
                    for khoi_du_lieu in phan_hoi.iter_content(chunk_size=KICH_THUOC):
                        if khoi_du_lieu:
                            f.write(khoi_du_lieu)

            print("[KIỂM TRA] Đang đọc tệp vừa tải...", flush=True)

            kiem_tra_file(duong_dan_tam_thoi, columns)
            duong_dan_tam_thoi.replace(duong_dan_luu)

            print(f"[HOÀN TẤT] {duong_dan_luu}", flush=True)
            return

        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError, gzip.BadGzipFile, EOFError, zlib.error) as loi:
            # Chỉ thử lại lỗi mạng tạm thời, tệp hỏng hoặc lỗi HTTP (404...) báo ngay
            if lan_thu == SO_LAN_THU:
                raise
            print(f"[THỬ LẠI] Lần {lan_thu}/{SO_LAN_THU} lỗi mạng ({type(loi).__name__}), tải lại sau {5 * lan_thu} giây", flush=True)
            time.sleep(5 * lan_thu)

        finally:
            duong_dan_tam_thoi.unlink(missing_ok=True)



def tai_du_lieu(cau_hinh: dict, snapshot: str | None =None, tai_lai: bool =False):
    """Tải nguồn theo thành phố và snapshot trong cấu hình"""
    snapshots = chon_cac_moc(cau_hinh, snapshot)
    thanh_pho = cau_hinh["city"]
    duong_dan_nguon = cau_hinh["data_root"]
    cac_duong_dan_luu = []

    with requests.Session() as phien_ket_noi:
        for snapshot in snapshots:
            thu_muc_luu = THU_MUC_DU_AN / "data" / "raw" / thanh_pho / snapshot

            for duong_dan_tuong_doi, columns in COLUMNS.items():
                url_nguon = f"https://data.insideairbnb.com/{duong_dan_nguon}/{snapshot}/{duong_dan_tuong_doi}"
                ten_tep = Path(duong_dan_tuong_doi).name
                duong_dan_luu = thu_muc_luu / ten_tep

                tai_file(phien_ket_noi, url_nguon, duong_dan_luu, columns, tai_lai=tai_lai)
                cac_duong_dan_luu.append(duong_dan_luu)

        print(f"Hoàn tất tải/kiểm tra {len(cac_duong_dan_luu)} tệp")

    return cac_duong_dan_luu



def main():
    """Đọc cấu hình từ --config và chạy bước tải"""
    trinh_doc_tham_so = ArgumentParser(description="Tải dữ liệu Inside Airbnb theo cấu hình")
    trinh_doc_tham_so.add_argument(
        "--config", type=Path, default=CAU_HINH_MAC_DINH,
    )
    trinh_doc_tham_so.add_argument("--snapshot", help="Chỉ tải một mốc YYYY-MM-DD có trong cấu hình")
    tham_so = trinh_doc_tham_so.parse_args()

    cau_hinh = doc_cau_hinh(tham_so.config)

    tai_du_lieu(cau_hinh, snapshot=tham_so.snapshot, tai_lai=cau_hinh["download"].get("tai_lai", False))


if __name__ == "__main__":
    main()
