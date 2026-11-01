"""Sinh ảnh hóa đơn giả lập và file đáp án data/truth.csv.

Mỗi hóa đơn dùng một kiểu ghi ngày, kiểu số tiền và nhãn tổng khác nhau, kèm
những số tiền gây nhiễu (tạm tính, tiền khách đưa, chiết khấu, đặt cọc) để
kiểm tra phần tách trường. Ảnh được xoay nhẹ, làm mờ và thêm nhiễu cho giống
ảnh chụp bằng điện thoại.

    python -m src.make_receipts
"""

import random
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECEIPTS_DIR = DATA_DIR / "receipts"
TRUTH_PATH = DATA_DIR / "truth.csv"

# Font hỗ trợ tiếng Việt: Windows trước, rồi Linux, macOS.
FONT_CANDIDATES = {
    "sans": ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/Library/Fonts/Arial.ttf"],
    "sans-bold": ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/Library/Fonts/Arial Bold.ttf"],
    "mono": ["C:/Windows/Fonts/cour.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/Library/Fonts/Courier New.ttf"],
    "mono-bold": ["C:/Windows/Fonts/courbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                  "/Library/Fonts/Courier New Bold.ttf"],
}

WIDTH, MARGIN, FONT_SIZE = 560, 28, 22
HR = ("hr",)

# Mỗi dòng: ("C", chữ) tiêu đề giữa, ("c", chữ) giữa, ("l", chữ) trái,
# ("lr", trái, phải) nhãn bên trái và số tiền căn phải, HR là đường kẻ.


@dataclass
class Receipt:
    file: str
    style: str  # "sans" hoặc "mono"
    rows: list[tuple]
    date: str   # đáp án, dạng YYYY-MM-DD
    store: str
    total: int


RECEIPTS = [
    Receipt("hd01_ca_phe.jpg", "sans", [
        ("C", "CÀ PHÊ MỘT CHÚT"), ("c", "12 Lê Lợi, Q.1, TP.HCM"), ("c", "ĐT: 028 3822 1234"), HR,
        ("C", "HÓA ĐƠN BÁN HÀNG"), ("l", "Ngày: 12/10/2026  08:15"), ("l", "Thu ngân: Lan"), HR,
        ("l", "Cà phê sữa đá"), ("lr", "  2 x 29.000", "58.000"),
        ("l", "Bánh mì ốp la"), ("lr", "  1 x 25.000", "25.000"), HR,
        ("lr", "Tạm tính", "83.000"), ("lr", "Tổng cộng", "83.000"),
        ("lr", "Tiền khách đưa", "100.000"), ("lr", "Tiền thối", "17.000"), HR,
        ("c", "Cảm ơn quý khách!"),
    ], "2026-10-12", "CÀ PHÊ MỘT CHÚT", 83000),
    Receipt("hd02_sieu_thi.jpg", "mono", [
        ("C", "SIÊU THỊ MINI AN PHÚ"), ("c", "MST: 0312345678"), ("c", "88 Nguyễn Trãi, Q.5"), HR,
        ("l", "Ngày 03-09-2026 19:42"), ("l", "Số HĐ: 000123"), HR,
        ("lr", "Sữa tươi 1L x2", "64,000"), ("lr", "Mì gói x10", "45,000"), ("lr", "Nước giặt 2kg", "136,500"), HR,
        ("lr", "Cộng tiền hàng", "245,500"), ("lr", "VAT 8%", "19,640"), ("lr", "TỔNG THANH TOÁN", "265,140"),
        ("lr", "Khách đưa", "300,000"), ("lr", "Trả lại", "34,860"),
    ], "2026-09-03", "SIÊU THỊ MINI AN PHÚ", 265140),
    Receipt("hd03_nha_thuoc.jpg", "sans", [
        ("C", "NHÀ THUỐC TÂM AN"), ("c", "Số 5 Trần Phú, Hà Đông, Hà Nội"), HR,
        ("l", "Ngày 21 tháng 08 năm 2026"), HR,
        ("lr", "Paracetamol 500mg", "35.000đ"), ("lr", "Vitamin C", "48.000đ"), ("lr", "Khẩu trang y tế", "73.000đ"), HR,
        ("lr", "Tổng tiền:", "156.000đ"), ("c", "Xin cảm ơn, hẹn gặp lại!"),
    ], "2026-08-21", "NHÀ THUỐC TÂM AN", 156000),
    Receipt("hd04_bun_bo.jpg", "mono", [
        ("C", "QUÁN BÚN BÒ CÔ BA"), ("c", "Hotline 0909 123 456"), HR,
        ("l", "21.10.2026 12:30  Bàn 7"), HR,
        ("lr", "Bún bò đặc biệt x2", "120,000"), ("lr", "Chả giò x1", "45,000"),
        ("lr", "Trà đá x3", "15,000"), ("lr", "Nước cam x1", "30,000"), HR,
        ("lr", "TOTAL", "210,000 VND"),
    ], "2026-10-21", "QUÁN BÚN BÒ CÔ BA", 210000),
    Receipt("hd05_van_phong_pham.jpg", "sans", [
        ("C", "VĂN PHÒNG PHẨM HỒNG HÀ"), ("c", "25 Lý Thường Kiệt, Hoàn Kiếm"), HR,
        ("C", "PHIẾU THANH TOÁN"), ("l", "Ngày: 05/11/2026"), HR,
        ("lr", "Giấy A4 x5 ram", "450.000"), ("lr", "Bút bi x2 hộp", "180.000"), ("lr", "Sổ tay x10", "620.000"), HR,
        ("lr", "Tổng cộng", "1.250.000"), ("lr", "Chiết khấu 5%", "-62.500"), ("lr", "Thanh toán", "1.187.500"),
    ], "2026-11-05", "VĂN PHÒNG PHẨM HỒNG HÀ", 1187500),
    Receipt("hd06_xang_dau.jpg", "mono", [
        ("C", "CỬA HÀNG XĂNG DẦU SỐ 12"), ("c", "QL1A, Bình Chánh, TP.HCM"), HR,
        ("l", "Ngày: 2026-10-30 07:05"), ("l", "Mặt hàng: Xăng RON 95"),
        ("lr", "Số lít", "4,52"), ("lr", "Đơn giá", "22.150"), HR,
        ("lr", "Thành tiền", "100.118"),
    ], "2026-10-30", "CỬA HÀNG XĂNG DẦU SỐ 12", 100118),
    Receipt("hd07_tiem_banh.jpg", "sans", [
        ("C", "TIỆM BÁNH HẠNH PHÚC"), ("c", "Bánh kem - Bánh mì - Bánh ngọt"), HR,
        ("l", "Ngày 7/9/2026"), HR,
        ("lr", "Bánh kem dâu", "250.000"), ("lr", "Nến số", "10.000"), ("lr", "Hộp quà", "15.000"), HR,
        ("lr", "Tổng", "275.000"), ("lr", "Đặt cọc", "100.000"), ("lr", "Còn phải trả", "175.000"),
    ], "2026-09-07", "TIỆM BÁNH HẠNH PHÚC", 275000),
    Receipt("hd08_giat_ui.jpg", "mono", [
        ("C", "GIẶT ỦI SẠCH THƠM"), ("c", "Nhận giao tận nơi"), HR,
        ("l", "Ngày nhận: 18/10/2026"), ("l", "Ngày trả: 20/10/2026"), HR,
        ("lr", "Giặt sấy 5kg", "60.000"), HR,
        ("lr", "Phải trả", "60.000"),
    ], "2026-10-18", "GIẶT ỦI SẠCH THƠM", 60000),
]


def load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(f"Không tìm thấy font {kind} hỗ trợ tiếng Việt: {FONT_CANDIDATES[kind]}")


def render(receipt: Receipt) -> Image.Image:
    body = load_font(receipt.style, FONT_SIZE)
    title = load_font(f"{receipt.style}-bold", FONT_SIZE + 4)
    line_height = int(FONT_SIZE * 1.6)
    height = 2 * MARGIN + line_height * len(receipt.rows)
    paper = Image.new("L", (WIDTH, height), 250)
    draw = ImageDraw.Draw(paper)

    for i, row in enumerate(receipt.rows):
        y = MARGIN + i * line_height
        kind = row[0]
        if kind == "hr":
            draw.line([(MARGIN, y + line_height // 2), (WIDTH - MARGIN, y + line_height // 2)], fill=120, width=1)
        elif kind in ("C", "c"):
            font = title if kind == "C" else body
            draw.text((WIDTH // 2, y), row[1], font=font, fill=20, anchor="ma")
        elif kind == "l":
            draw.text((MARGIN, y), row[1], font=body, fill=20)
        elif kind == "lr":
            draw.text((MARGIN, y), row[1], font=body, fill=20)
            draw.text((WIDTH - MARGIN, y), row[2], font=body, fill=20, anchor="ra")
    return paper


def photograph(paper: Image.Image, rng: random.Random) -> Image.Image:
    """Đặt tờ hóa đơn lên nền tối, xoay lệch, làm mờ và thêm nhiễu."""
    pad = 40
    photo = Image.new("L", (paper.width + 2 * pad, paper.height + 2 * pad), rng.randint(90, 140))
    photo.paste(paper, (pad, pad))
    photo = photo.rotate(rng.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True, fillcolor=110)
    photo = photo.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.8)))
    noise = np.random.default_rng(rng.randint(0, 10_000)).normal(0, 6, (photo.height, photo.width))
    pixels = np.clip(np.asarray(photo, dtype=float) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels).convert("RGB")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(1)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    for receipt in RECEIPTS:
        photograph(render(receipt), rng).save(RECEIPTS_DIR / receipt.file, quality=82)
    truth = pd.DataFrame([{"file": r.file, "ngay": r.date, "don_vi": r.store, "tong_tien": r.total}
                          for r in RECEIPTS])
    truth.to_csv(TRUTH_PATH, index=False)
    print(f"Đã sinh {len(RECEIPTS)} ảnh vào {RECEIPTS_DIR} và đáp án vào {TRUTH_PATH}")


if __name__ == "__main__":
    main()
