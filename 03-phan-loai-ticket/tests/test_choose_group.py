from src.model import NEEDS_REVIEW, choose_group


def test_rat_tu_tin_thi_tu_chuyen():
    ranked = [("Thanh toán", 0.95), ("Tài khoản", 0.03), ("Kỹ thuật", 0.02)]
    assert choose_group(ranked) == "Thanh toán"


def test_phan_van_giua_cac_nhom_thi_can_kiem_tra():
    ranked = [("Thanh toán", 0.36), ("Tài khoản", 0.33), ("Kỹ thuật", 0.31)]
    assert choose_group(ranked) == NEEDS_REVIEW


def test_vuot_nguong_nhung_sat_nhom_thu_hai_thi_can_kiem_tra():
    # Ví dụ "App bị treo khi bấm nút thanh toán": Kỹ thuật hay Thanh toán đều có lý.
    ranked = [("Kỹ thuật", 0.55), ("Thanh toán", 0.40), ("Tài khoản", 0.05)]
    assert choose_group(ranked) == NEEDS_REVIEW
