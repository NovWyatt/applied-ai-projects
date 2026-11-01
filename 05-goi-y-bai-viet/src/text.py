"""Chuẩn hóa văn bản tiếng Việt trước khi đưa vào TF-IDF."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Đưa về chữ thường, bỏ dấu tiếng Việt và gộp khoảng trắng.

    Bỏ dấu giúp "đăng nhập" và "dang nhap" trở thành cùng một từ.
    """
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # "đ" là một ký tự riêng chứ không phải "d" cộng dấu, nên NFD không tách được.
    text = text.replace("đ", "d")
    return _WHITESPACE.sub(" ", text).strip()
