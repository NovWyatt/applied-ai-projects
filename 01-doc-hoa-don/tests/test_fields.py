import pytest

from src.fields import (AmountLine, amount_lines, find_date, find_store, has_foreign_letters, has_vowelless_word,
                        label_kind, normalize_text, parse_amount)
from src.ocr import OcrLine


@pytest.mark.parametrize("text, expected", [
    ("Tổng cộng  1.187.500", 1187500),
    ("TỔNG THANH TOÁN  265,140", 265140),
    ("Tổng tiền:  156.000đ", 156000),
    ("TOTAL  210,000 VND", 210000),
    ("Chiết khấu 5%  -62.500", -62500),
    ("Giặt sấy  60000", 60000),
])
def test_doc_so_tien(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", [
    "Số lít  4,52",
    "MST: 0312345678",
    "Ngày 7/9/2026",
    "Ngày 21 tháng 08 năm 2026",
    "ĐT: 028 3822 1234",
    "Số HĐ: 000123",
])
def test_khong_nham_thanh_so_tien(text):
    assert parse_amount(text) is None


@pytest.mark.parametrize("text, expected", [
    ("Ngày: 12/10/2026  08:15", "2026-10-12"),
    ("Ngày 03-09-2026 19:42", "2026-09-03"),
    ("Ngày 21 tháng 08 năm 2026", "2026-08-21"),
    ("21.10.2026 12:30  Bàn 7", "2026-10-21"),
    ("Ngày: 2026-10-30 07:05", "2026-10-30"),
    ("Ngày 7/9/2026", "2026-09-07"),
])
def test_doc_ngay(text, expected):
    assert find_date([OcrLine(text, 1.0)]) == expected


def test_ngay_khong_ton_tai_bi_bo_qua():
    assert find_date([OcrLine("Ngày 31/02/2026", 1.0)]) is None


@pytest.mark.parametrize("label, kind", [
    (normalize_text("Tồng cng"), "gross"),   # OCR làm rơi chữ
    ("tong tin", "gross"),
    ("thanh tien", "gross"),                 # giống "thanh toan" 80% nhưng giống hệt "thanh tien"
    ("con phai tra", "balance"),             # giống "phai tra" 80% nhưng không phải số đã trả
    ("tong thanh toan", "paid"),
    ("total", "paid"),
    ("tien khach dua", None),
    ("tam tinh", None),
    ("cng tien hang", None),
])
def test_xep_loai_nhan(label, kind):
    assert label_kind(label) == kind


def test_phat_hien_chu_khong_thuoc_tieng_viet():
    assert has_foreign_letters("VĂN PHÒNG PHÅM")
    assert not has_foreign_letters("VĂN PHÒNG PHẨM HỒNG HÀ")


def test_phat_hien_tu_bi_roi_nguyen_am():
    assert has_vowelless_word("CÀ PHÊ MT CHÚT")
    assert not has_vowelless_word("CÀ PHÊ MỘT CHÚT")
    assert not has_vowelless_word("88 Nguyễn Trãi, Q.5")  # số và chữ cái đứng một mình không tính


def test_ten_don_vi_bo_qua_tieu_de_hoa_don():
    lines = [OcrLine("HÓA ĐƠN BÁN HÀNG", 1.0), OcrLine("CÀ PHÊ MỘT CHÚT", 0.99)]
    assert find_store(lines).text == "CÀ PHÊ MỘT CHÚT"


def test_nhan_cua_dong_so_tien_da_bo_dau():
    lines = [OcrLine("Ngày: 12/10/2026", 1.0), OcrLine("Tồng cng:  83.000", 0.95)]
    assert amount_lines(lines) == [AmountLine("tong cng", 83000, 1)]
