from src.data import Line
from src.extract import ActionItem, build_prompt, review

ATTENDEES = ["Lan", "Minh", "Hùng"]
LINES = [
    Line(10, "Vậy Minh gửi báo giá cho Phương Nam trước thứ Sáu tuần này nhé."),
    Line(14, "Dạ vâng ạ."),
    Line(15, "Chị ơi, khách hàng Hòa Bình vừa hỏi về việc gia hạn hợp đồng bảo trì."),
    Line(29, "Hùng gọi lại cho Hòa Bình nhé, khi nào tiện thì gọi, không gấp."),
]


def test_bao_mo_hinh_khi_khong_co_ten_nguoi_noi():
    assert "KHÔNG có tên người nói" in build_prompt(LINES, ATTENDEES)
    assert "KHÔNG có tên người nói" not in build_prompt([Line(0, "Chào.", "Lan")], ATTENDEES)


def test_viec_ro_rang_khong_can_kiem_tra():
    item = ActionItem(viec="Gửi báo giá cho Phương Nam", phu_trach="Minh", han="thứ Sáu tuần này", dong=1)
    assert review(item, LINES, ATTENDEES) == {}


def test_nguoi_phu_trach_khong_co_trong_danh_sach_du_hop():
    item = ActionItem(viec="Gửi báo giá cho Phương Nam", phu_trach="Hoàng", han="thứ Sáu tuần này", dong=1)
    assert "phu_trach" in review(item, LINES, ATTENDEES)


def test_han_khong_nam_o_cau_giao_viec():
    # Mô hình lấy nhầm hạn của việc khác: "thứ Sáu tuần này" là hạn gửi báo giá, không phải hạn gọi lại.
    item = ActionItem(viec="Gọi lại cho Hòa Bình", phu_trach="Hùng", han="thứ Sáu tuần này", dong=4)
    assert "han" in review(item, LINES, ATTENDEES)


def test_dai_tu_va_cau_khong_phai_han():
    # Không có tên người nói, mô hình ghi luôn "Em"; "khi nào tiện" thì không phải hạn chót.
    item = ActionItem(viec="Gọi lại cho Hòa Bình", phu_trach="Em", han="khi nào tiện", dong=4)
    assert set(review(item, LINES, ATTENDEES)) == {"phu_trach", "han"}


def test_ten_khong_trung_dai_tu_khi_bo_dau():
    # "Minh" bỏ dấu trùng "mình"; ở đây Minh là tên thật và có trong dòng giao việc.
    item = ActionItem(viec="Gửi báo giá", phu_trach="Minh", han="", dong=1)
    assert review(item, LINES, ATTENDEES) == {}


def test_viec_khong_ai_nhan_khong_han():
    item = ActionItem(viec="Họp lại tuần sau", phu_trach="", han="", dong=4)
    assert "viec" in review(item, LINES, ATTENDEES)
