"""So kết quả đọc với đáp án data/truth.csv.

Mặc định dùng kết quả OCR đã lưu trong data/ocr_snapshot.json: chạy trong một
giây, không cần Paddle, và lần nào cũng ra cùng kết quả. Thêm --refresh-ocr để
chạy lại PaddleOCR trên ảnh mẫu và lưu lại bản mới.

    python -m src.evaluate
    python -m src.evaluate --refresh-ocr
"""

import argparse
import json
import sys
import unicodedata

import pandas as pd

from src.fields import amount_lines, extract_fields, normalize_text, pick_total
from src.make_receipts import RECEIPTS_DIR, TRUTH_PATH
from src.ocr import PROJECT_DIR, OcrLine

SNAPSHOT_PATH = PROJECT_DIR / "data" / "ocr_snapshot.json"


def refresh_snapshot(files: list[str]) -> None:
    from src.ocr import read_lines  # chỉ cần Paddle khi chạy lại OCR

    snapshot = {}
    for name in files:
        print(f"  OCR {name}", flush=True)
        snapshot[name] = [vars(line) for line in read_lines(RECEIPTS_DIR / name)]
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")


def load_snapshot() -> dict[str, list[OcrLine]]:
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return {name: [OcrLine(**line) for line in lines] for name, lines in data.items()}


def same_text(a: str | None, b: str) -> bool:
    return a is not None and unicodedata.normalize("NFC", a).casefold() == unicodedata.normalize("NFC", b).casefold()


def score_field(results: pd.DataFrame, correct_col: str, flag: str) -> dict:
    correct = results[correct_col]
    flagged = results["can_kiem_tra"].str.contains(flag)
    return {"Đúng": f"{correct.sum()}/{len(results)}", "Bị đánh dấu kiểm tra": int(flagged.sum()),
            "Sai lọt lưới": int((~correct & ~flagged).sum())}


def print_candidates(snapshot: dict[str, list[OcrLine]], truth: pd.DataFrame) -> None:
    """Các dòng có số tiền của từng hóa đơn, để thiết kế pick_total."""
    for row in truth.itertuples():
        print(f"{row.file}  (tổng đúng: {row.tong_tien:,})")
        for line in amount_lines(snapshot[row.file]):
            print(f"    [{line.index:2d}] {line.label!r:28} {line.amount:>12,}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-ocr", action="store_true", help="chạy lại PaddleOCR trên ảnh mẫu")
    args = parser.parse_args()

    truth = pd.read_csv(TRUTH_PATH)
    if args.refresh_ocr or not SNAPSHOT_PATH.exists():
        refresh_snapshot(truth["file"].tolist())
    snapshot = load_snapshot()

    try:
        pick_total([])
    except NotImplementedError:
        print("pick_total chưa được viết. Các dòng có số tiền trên từng hóa đơn:\n")
        print_candidates(snapshot, truth)
        return

    rows = []
    for row in truth.itertuples():
        fields = extract_fields(snapshot[row.file])
        rows.append({
            "file": row.file, **fields.as_row(),
            "ngay_dung": fields.ngay == row.ngay,
            "don_vi_dung": same_text(fields.don_vi, row.don_vi),
            "don_vi_dung_bo_dau": fields.don_vi is not None and normalize_text(fields.don_vi) == normalize_text(row.don_vi),
            "tong_dung": fields.tong_tien == row.tong_tien,
        })
    results = pd.DataFrame(rows)

    summary = pd.DataFrame([
        {"Trường": "Ngày", **score_field(results, "ngay_dung", "Ngày")},
        {"Trường": "Tổng tiền", **score_field(results, "tong_dung", "Tổng tiền")},
        {"Trường": "Đơn vị (đúng cả dấu)", **score_field(results, "don_vi_dung", "Đơn vị")},
        {"Trường": "Đơn vị (đúng khi bỏ dấu)", **score_field(results, "don_vi_dung_bo_dau", "Đơn vị")},
    ])
    print(summary.to_string(index=False), "\n")
    print("'Sai lọt lưới' là ô sai mà không bị đánh dấu kiểm tra, loại lỗi nguy hiểm nhất.\n")

    detail = results.merge(truth, on="file", suffixes=("", "_dap_an"))
    print(detail[["file", "ngay", "tong_tien", "tong_tien_dap_an", "don_vi", "can_kiem_tra"]].to_string(index=False))


if __name__ == "__main__":
    main()
