"""Đọc cả thư mục ảnh hóa đơn và xuất bảng CSV.

Chạy từ thư mục 01-doc-hoa-don:

    python -m src.read_receipts                              # đọc data/receipts
    python -m src.read_receipts anh/cua/toi -o output/thang10.csv

Ô nào không chắc được ghi ở cột can_kiem_tra. Muốn xem ảnh và sửa trực tiếp
thì dùng giao diện: streamlit run app.py
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.fields import extract_fields
from src.ocr import PROJECT_DIR, read_lines

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
COLUMNS = {"file": "Tệp", "ngay": "Ngày", "don_vi": "Đơn vị", "tong_tien": "Tổng tiền",
           "can_kiem_tra": "Cần kiểm tra"}


def read_folder(folder: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES):
        print(f"  đọc {path.name}", flush=True)
        rows.append({"file": path.name, **extract_fields(read_lines(path)).as_row()})
    return pd.DataFrame(rows, columns=list(COLUMNS)).astype({"tong_tien": "Int64"})


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Đọc ảnh hóa đơn thành bảng CSV.")
    parser.add_argument("folder", nargs="?", type=Path, default=PROJECT_DIR / "data" / "receipts")
    parser.add_argument("-o", "--output", type=Path, default=PROJECT_DIR / "output" / "hoa_don.csv")
    args = parser.parse_args()

    table = read_folder(args.folder).rename(columns=COLUMNS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig để Excel mở đúng tiếng Việt.
    table.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"\n{table.to_string(index=False)}\n")
    flagged = (table["Cần kiểm tra"] != "").sum()
    print(f"Đã ghi {len(table)} hóa đơn vào {args.output}. {flagged} hóa đơn có ô cần kiểm tra.")


if __name__ == "__main__":
    main()
