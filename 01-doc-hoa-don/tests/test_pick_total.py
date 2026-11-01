from src.fields import AmountLine, pick_total


def lines(*pairs):
    return [AmountLine(label, amount, i) for i, (label, amount) in enumerate(pairs)]


def test_bo_qua_tam_tinh_va_tien_khach_dua():
    receipt = lines(("tam tinh", 83000), ("tong cong", 83000), ("tien khach dua", 100000), ("tien thoi", 17000))
    assert pick_total(receipt) == 83000


def test_nhan_bi_ocr_lam_roi_dau():
    receipt = lines(("cng tien hang", 245500), ("vat 8%", 19640), ("tong thanh toan", 265140), ("khach dua", 300000))
    assert pick_total(receipt) == 265140


def test_khong_co_nhan_tong_thi_khong_doan():
    assert pick_total(lines(("banh kem dau", 250000), ("nen so", 10000))) is None


def test_thanh_toan_sau_chiet_khau_thang_tong_cong():
    receipt = lines(("tong cong", 1250000), ("chit khu 5%", -62500), ("thanh toan", 1187500))
    assert pick_total(receipt) == 1187500


def test_con_phai_tra_sau_dat_coc_khong_phai_tong():
    receipt = lines(("tong", 275000), ("dat coc", 100000), ("con phai tra", 175000))
    assert pick_total(receipt) == 275000


def test_hai_dong_thanh_toan_khac_so_thi_khong_doan():
    receipt = lines(("tong cong", 500000), ("thanh toan", 300000), ("phai tra", 200000))
    assert pick_total(receipt) is None
