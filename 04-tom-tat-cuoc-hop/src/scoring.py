"""So kết quả với đáp án: lỗi chép lời (WER), tên người, và từng đầu việc."""

import re
from difflib import SequenceMatcher

from src.data import normalize


def words(text: str) -> list[str]:
    """Tách từ, giữ dấu tiếng Việt (vì "mình" và "Minh" là hai từ khác nhau)."""
    return re.sub(r"[^\w]+", " ", text.lower()).split()


def edit_distance(a: list[str], b: list[str]) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref = words(reference)
    return edit_distance(ref, words(hypothesis)) / max(len(ref), 1)


def name_hits(reference: str, hypothesis: str, names: list[str]) -> tuple[int, int]:
    """(số lần tên được chép đúng, số lần tên được nhắc trong lời nói thật)."""
    count = lambda name, text: len(re.findall(rf"(?<!\w){re.escape(name.lower())}(?!\w)", text.lower()))
    pairs = [(count(name, reference), count(name, hypothesis)) for name in names]
    return sum(min(ref, hyp) for ref, hyp in pairs), sum(ref for ref, _ in pairs)


HONORIFICS = {"anh", "chi", "em", "ban", "co", "chu", "ong", "ba"}
WEEKDAYS = {"2": "hai", "3": "ba", "4": "tu", "5": "nam", "6": "sau", "7": "bay"}
DEADLINE_PREFIXES = ("cham nhat", "truoc", "trong", "vao", "han la", "han", "ngay")


def same_person(a: str, b: str) -> bool:
    strip = lambda name: " ".join(w for w in normalize(name).split() if w not in HONORIFICS)
    return strip(a) == strip(b)


DIGITS = {"một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5,
          "sáu": 6, "bảy": 7, "tám": 8, "chín": 9}
NUMBER = rf"(?:{'|'.join(DIGITS)}|mười|mươi)(?:\s+(?:{'|'.join(DIGITS)}|mười|mươi)){{0,2}}"


def words_to_int(words: str) -> str:
    """ "hai mươi" -> "20", "mười một" -> "11", "mười lăm" -> "15" (số từ 1 đến 99)."""
    tens, units = 0, 0
    for word in words.split():
        if word == "mười":
            tens = 1
        elif word == "mươi":
            tens, units = units, 0
        else:
            units = DIGITS[word]
    return str(tens * 10 + units)


def normalize_deadline(text: str) -> str:
    """ "Trước thứ 6 tuần này" -> "thu sau tuan nay"; "ngày mười lăm tháng mười một" -> "15/11"."""
    # Đổi số đọc bằng chữ khi còn dấu: bỏ dấu rồi thì "sáu" (6) và "sau" (tuần sau) trùng nhau.
    text = re.sub(rf"\b({NUMBER}|\d{{1,2}})\s+tháng\s+({NUMBER}|\d{{1,2}})\b",
                  lambda m: "/".join(g if g.isdigit() else words_to_int(g) for g in m.groups()), text.lower())
    text = normalize(text)
    changed = True
    while changed:
        changed = False
        for prefix in DEADLINE_PREFIXES:
            if text.startswith(prefix + " "):
                text, changed = text[len(prefix) + 1:], True
    text = re.sub(r"\bthu (\d)\b", lambda m: "thu " + WEEKDAYS.get(m.group(1), m.group(1)), text)
    text = re.sub(r"\b(cuoi|dau|giua) (thang|quy|nam) nay\b", r"\1 \2", text)  # "cuối tháng này" = "cuối tháng"
    text = re.sub(r"\b(\d{1,2}) thang (\d{1,2})\b", r"\1/\2", text)
    text = re.sub(r"\b(\d{1,2})/(\d{1,2})(/\d{4})?\b", lambda m: f"{int(m.group(1))}/{int(m.group(2))}", text)
    return text


def same_deadline(a: str, b: str) -> bool:
    return normalize_deadline(a) == normalize_deadline(b)


def contains(text: str, keyword: str, min_ratio: float = 0.8) -> bool:
    """Có từ khóa, chấp nhận sai một chút do chép lời ("dam nhap" vẫn khớp "dang nhap")."""
    if keyword in text:
        return True
    size, tokens = len(keyword.split()), text.split()
    return any(SequenceMatcher(None, " ".join(tokens[i:i + size]), keyword).ratio() >= min_ratio
               for i in range(len(tokens) - size + 1))


def match_items(predicted: list[str], truth: list[dict]) -> dict[int, int]:
    """Ghép đầu việc máy rút ra với đáp án. Trả về {chỉ số đáp án: chỉ số kết quả}.

    predicted: mô tả từng việc máy rút ra. truth: việc đúng, có "viec" và "tu_khoa" (đã bỏ dấu).
    Một cặp ghép được khi kết quả chứa ít nhất một nửa số từ khóa. Ghép một-một, cặp
    có điểm cao hơn được ghép trước; điểm = tỉ lệ từ khóa + độ giống của cả câu, để
    "Gửi tài liệu khóa đào tạo" về với "Gửi tài liệu khóa học" chứ không phải "Học khóa đào tạo".
    """
    texts = [normalize(text) for text in predicted]
    pairs = []
    for t, want in enumerate(truth):
        for p, text in enumerate(texts):
            keywords = sum(contains(text, keyword) for keyword in want["tu_khoa"]) / len(want["tu_khoa"])
            if keywords >= 0.5:
                pairs.append((keywords + SequenceMatcher(None, text, normalize(want["viec"])).ratio(), t, p))
    matched, used = {}, set()
    for _, t, p in sorted(pairs, key=lambda x: -x[0]):
        if t not in matched and p not in used:
            matched[t] = p
            used.add(p)
    return matched
