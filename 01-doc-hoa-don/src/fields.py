"""Tách Ngày, Đơn vị và Tổng tiền từ các dòng chữ OCR.

OCR đọc số rất chuẩn nhưng hay làm rơi dấu tiếng Việt ("Tổng cộng" thành
"Tồng cng"), nên mọi phép so khớp nhãn đều làm trên chữ đã bỏ dấu và cho
phép sai lệch nhỏ.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from src.ocr import OcrLine

MIN_STORE_SCORE = 0.95
MIN_LABEL_RATIO = 0.8
# Nhãn dòng tổng, chia theo ý nghĩa:
# - paid: số khách thực trả, đã trừ chiết khấu và cộng VAT, nên được ưu tiên.
# - gross: tổng trước giảm trừ, dùng khi hóa đơn không có dòng "thanh toán".
# - balance: còn nợ sau đặt cọc, KHÔNG phải tổng hóa đơn. Phải có nhóm này vì
#   "con phai tra" giống "phai tra" tới 80%, đủ để bị nhận nhầm là số đã trả.
TOTAL_LABELS = {
    "paid": ("tong thanh toan", "thanh toan", "phai thanh toan", "phai tra", "total"),
    "gross": ("tong cong", "tong tien", "tong", "thanh tien"),
    "balance": ("con phai tra", "con lai", "con no"),
}
# Dấu thanh và dấu mũ/móc/trăng của tiếng Việt. Dấu khác (Å, ū, ā...) là OCR đọc sai.
VIETNAMESE_MARKS = {"̀", "́", "̃", "̉", "̣", "̂", "̆", "̛"}
NOT_STORE_WORDS = ("hoa don", "phieu", "mst", "dt:", "hotline", "dia chi", "so hd")

_WHITESPACE = re.compile(r"\s+")
# Số tiền ở cuối dòng: 1.187.500 / 265,140 / 100118 / -62.500, có thể kèm đ, d, VND.
# Số viết liền phải từ 5 chữ số, để không nhận năm "2026" hay đuôi số điện thoại "1234".
# Cũng không nhận "4,52" (số lít), "0312345678" (mã số thuế, số 0 đầu) hay "7/9/2026" (ngày).
_AMOUNT_AT_END = re.compile(
    r"(?<![\w/.,:-])(-?(?:\d{1,3}(?:[.,]\d{3})+|[1-9]\d{4,8}))\s*(?:đ|d|vnd|₫)?\s*$", re.IGNORECASE)
_DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?!\d)")
_DATE_YMD = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_DATE_WORDS = re.compile(r"ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})")


@dataclass
class AmountLine:
    label: str   # chữ bên trái số tiền, đã bỏ dấu và viết thường, ví dụ "tong cong"
    amount: int  # số tiền, ví dụ 83000; chiết khấu là số âm
    index: int   # thứ tự dòng trên hóa đơn, tính từ trên xuống


@dataclass
class ReceiptFields:
    ngay: str | None = None       # YYYY-MM-DD
    don_vi: str | None = None
    tong_tien: int | None = None
    can_kiem_tra: list[str] = field(default_factory=list)

    def as_row(self) -> dict:
        return {"ngay": self.ngay, "don_vi": self.don_vi, "tong_tien": self.tong_tien,
                "can_kiem_tra": ", ".join(self.can_kiem_tra)}


def normalize_text(text: str) -> str:
    """Chữ thường, bỏ dấu tiếng Việt, gộp khoảng trắng."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace("đ", "d")
    return _WHITESPACE.sub(" ", text).strip()


def label_kind(label: str) -> str | None:
    """Nhóm trong TOTAL_LABELS có cụm từ giống nhãn (đã bỏ dấu) nhất.

    Chịu được chữ bị OCR làm rơi ("tong cng" vẫn là "tong cong"). Lấy nhóm giống
    NHẤT chứ không phải nhóm đầu tiên vượt ngưỡng: "thanh tien" giống "thanh toan"
    80% nhưng giống hệt "thanh tien" của nhóm gross.
    """
    best_kind, best_ratio = None, MIN_LABEL_RATIO
    for kind, phrases in TOTAL_LABELS.items():
        for phrase in phrases:
            ratio = SequenceMatcher(None, label, phrase).ratio()
            if ratio > best_ratio or (ratio == best_ratio and best_kind is None):
                best_kind, best_ratio = kind, ratio
    return best_kind


def has_foreign_letters(text: str) -> bool:
    """Có chữ cái không thuộc bảng chữ tiếng Việt, dấu hiệu OCR đọc sai dấu."""
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) == "Mn":
            if ch not in VIETNAMESE_MARKS:
                return True
        elif ch.isalpha() and not ch.isascii() and ch not in "đĐ":
            return True
    return False


def has_vowelless_word(text: str) -> bool:
    """Có từ không chứa nguyên âm, dấu hiệu OCR làm rơi chữ.

    Âm tiết tiếng Việt nào cũng có nguyên âm, và chữ OCR hay làm rơi nhất lại là
    nguyên âm mang hai lớp dấu (ộ, ể, ấ): "MỘT" thành "MT", "Tổng cộng" thành "Tng cng".
    """
    for word in normalize_text(text).split():
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and not any(vowel in letters for vowel in "aeiouy"):
            return True
    return False


def parse_amount(text: str) -> int | None:
    match = _AMOUNT_AT_END.search(text.strip())
    return int(re.sub(r"[.,]", "", match.group(1))) if match else None


def amount_lines(lines: list[OcrLine]) -> list[AmountLine]:
    """Các dòng kết thúc bằng một số tiền, kèm nhãn bên trái."""
    result = []
    for index, line in enumerate(lines):
        match = _AMOUNT_AT_END.search(line.text.strip())
        if match:
            label = normalize_text(line.text.strip()[:match.start()]).rstrip(" :")
            result.append(AmountLine(label, int(re.sub(r"[.,]", "", match.group(1))), index))
    return result


def find_date(lines: list[OcrLine]) -> str | None:
    """Ngày hợp lệ đầu tiên, dạng YYYY-MM-DD."""
    for line in lines:
        text = normalize_text(line.text)
        candidates = [(int(d), int(m), int(y)) for d, m, y in _DATE_DMY.findall(text)]
        candidates += [(int(d), int(m), int(y)) for y, m, d in _DATE_YMD.findall(text)]
        candidates += [(int(d), int(m), int(y)) for d, m, y in _DATE_WORDS.findall(text)]
        for day, month, year in candidates:
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                continue
    return None


def find_store(lines: list[OcrLine]) -> OcrLine | None:
    """Tên đơn vị thường là dòng chữ đầu tiên ở trên cùng, không phải địa chỉ hay mã số."""
    for line in lines[:4]:
        text = normalize_text(line.text)
        letters = sum(ch.isalpha() for ch in text)
        digits = sum(ch.isdigit() for ch in text)
        if letters >= 3 and digits < letters / 2 and not any(word in text for word in NOT_STORE_WORDS):
            return line
    return None


def pick_total(lines: list[AmountLine]) -> int | None:
    """Chọn tổng tiền của hóa đơn trong các dòng có số tiền.

    Trả về None khi không chắc, để người kiểm tra điền vào.
    """
    by_kind: dict[str, set[int]] = {}
    for line in lines:
        kind = label_kind(line.label)
        if kind:
            by_kind.setdefault(kind, set()).add(line.amount)
    for kind in ("paid", "gross"):
        amounts = by_kind.get(kind)
        if amounts:
            # Hai dòng cùng loại mà khác số (ví dụ trả một phần bằng thẻ, một phần tiền mặt): không đoán.
            return amounts.pop() if len(amounts) == 1 else None
    return None


def extract_fields(lines: list[OcrLine]) -> ReceiptFields:
    fields = ReceiptFields(ngay=find_date(lines), tong_tien=pick_total(amount_lines(lines)))
    store = find_store(lines)
    if store:
        fields.don_vi = store.text
    if fields.ngay is None:
        fields.can_kiem_tra.append("Ngày")
    if (store is None or store.score < MIN_STORE_SCORE
            or has_foreign_letters(store.text) or has_vowelless_word(store.text)):
        fields.can_kiem_tra.append("Đơn vị")
    if fields.tong_tien is None:
        fields.can_kiem_tra.append("Tổng tiền")
    return fields
