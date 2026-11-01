from src.text import normalize_text


def test_bo_dau_va_doi_chu_d():
    assert normalize_text("Không ĐĂNG nhập được") == "khong dang nhap duoc"


def test_gop_khoang_trang():
    assert normalize_text("  lỗi \n  500  ") == "loi 500"


def test_co_dau_va_khong_dau_thanh_mot():
    assert normalize_text("hoàn tiền") == normalize_text("hoan tien")
