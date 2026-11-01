from src.text import normalize_text


def test_bo_dau_va_doi_chu_d():
    assert normalize_text("Đọc Báo Cáo tài chính") == "doc bao cao tai chinh"


def test_gop_khoang_trang():
    assert normalize_text("  lập \n  trình  ") == "lap trinh"
