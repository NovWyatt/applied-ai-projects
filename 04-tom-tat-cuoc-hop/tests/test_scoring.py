from src.scoring import match_items, name_hits, same_deadline, same_person, wer


def test_wer_dem_ca_dau():
    # "mình" và "Minh" khác nhau: chép nhầm tên là một lỗi.
    assert wer("Minh gửi báo giá", "mình gửi báo giá") == 0.25
    assert wer("Minh gửi báo giá.", "minh gửi báo giá") == 0


def test_dem_ten_chep_dung():
    assert name_hits("Minh gửi, Minh nhé. Lan duyệt.", "mình gửi, Minh nhé. Lan duyệt.", ["Minh", "Lan"]) == (2, 3)


def test_cung_han_du_cach_noi_khac_nhau():
    assert same_deadline("Trước thứ 6 tuần này", "thứ Sáu tuần này")
    assert same_deadline("ngày 15 tháng 11", "15/11")
    assert same_deadline("chậm nhất ngày 20/11/2026", "20/11")
    assert same_deadline("ngày hai mươi tháng mười một", "20/11")
    assert same_deadline("mười lăm tháng mười một", "15/11")
    assert same_deadline("thứ Sáu tuần sau", "thứ 6 tuần sau")
    assert same_deadline("Cuối tháng này", "cuối tháng")
    assert not same_deadline("thứ Ba tuần sau", "thứ Hai tuần sau")
    assert not same_deadline("khi nào tiện", "")


def test_cung_nguoi_bo_qua_cach_xung_ho():
    assert same_person("anh Phong", "Phong")
    assert same_person("", "")
    assert not same_person("Minh", "")


def test_ghep_viec_theo_tu_khoa_mot_mot():
    truth = [{"viec": "Liên hệ ban nhạc, xin báo giá", "tu_khoa": ["ban nhac", "lien he"]},
             {"viec": "Hỏi giám đốc về ngân sách cho ban nhạc", "tu_khoa": ["ngan sach", "giam doc"]}]
    predicted = ["Hỏi giám đốc ngân sách cho ban nhạc", "Liên hệ ban nhạc xin báo giá", "Họp tiếp tuần sau"]
    assert match_items(predicted, truth) == {0: 1, 1: 0}


def test_ghep_viec_khi_chua_ca_tu_khoa_cua_viec_khac():
    truth = [{"viec": "Học khóa đào tạo sản phẩm mới", "tu_khoa": ["hoc khoa", "dao tao"]},
             {"viec": "Gửi tài liệu khóa học cho Minh", "tu_khoa": ["tai lieu"]}]
    assert match_items(["Gửi tài liệu khóa đào tạo sản phẩm mới cho Minh"], truth) == {1: 0}


def test_ghep_viec_chiu_duoc_loi_chep_loi():
    truth = [{"viec": "Sửa lỗi đăng nhập trên ứng dụng", "tu_khoa": ["dang nhap"]}]
    assert match_items(["Sửa lỗi đam nhập trên ứng dụng điện thoại"], truth) == {0: 0}
