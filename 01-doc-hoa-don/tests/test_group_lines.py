from src.ocr import group_lines


def box(x0, y0, x1, y1, tilt=0.0):
    """Khung chữ 4 góc; tilt là số pixel y thay đổi trên mỗi pixel x (ảnh nghiêng)."""
    return [[x0, y0 + tilt * x0], [x1, y0 + tilt * x1], [x1, y1 + tilt * x1], [x0, y1 + tilt * x0]]


def test_anh_nghieng_van_ghep_dung_nhan_voi_so_tien():
    # Nghiêng ~3.4 độ: nếu không chỉnh, "100.000" sẽ bị ghép nhầm lên dòng "Tổng cộng".
    tilt = -0.06
    texts = ["Tổng cộng", "83.000", "Tiền khách đưa", "100.000"]
    polys = [box(70, 418, 180, 452, tilt), box(480, 418, 580, 452, tilt),
             box(70, 452, 220, 486, tilt), box(480, 452, 580, 486, tilt)]
    lines = group_lines(texts, [0.99, 1.0, 0.97, 1.0], polys)
    assert [line.text for line in lines] == ["Tổng cộng  83.000", "Tiền khách đưa  100.000"]
    assert [line.score for line in lines] == [0.99, 0.97]


def test_khong_co_chu():
    assert group_lines([], [], []) == []
