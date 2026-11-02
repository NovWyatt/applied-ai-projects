from src.data import Line, format_transcript, normalize, parse_transcript


def test_bo_dau_va_dau_cau():
    assert normalize("Trước Thứ Sáu, đúng 15/11!") == "truoc thu sau dung 15/11"


def test_doc_bien_ban_co_va_khong_co_ten_nguoi_noi():
    lines = parse_transcript("[00:05] Lan: Minh gửi báo giá nhé.\n[01:12] Dạ vâng ạ.\nDòng rác", ["Lan", "Minh"])
    assert lines == [Line(5, "Minh gửi báo giá nhé.", "Lan"), Line(72, "Dạ vâng ạ.")]


def test_dau_hai_cham_trong_loi_noi_khong_phai_ten():
    lines = parse_transcript("[00:05] Lưu ý: hạn là thứ Sáu.", ["Lan", "Minh"])
    assert lines[0].speaker is None and lines[0].text == "Lưu ý: hạn là thứ Sáu."


def test_ghi_roi_doc_lai_giu_nguyen():
    lines = [Line(3.4, "Chào cả nhà.", "Lan"), Line(65, "Dạ.")]
    assert format_transcript(lines) == "[00:03] Lan: Chào cả nhà.\n[01:05] Dạ."
    assert parse_transcript(format_transcript(lines), ["Lan"]) == [Line(3, "Chào cả nhà.", "Lan"), Line(65, "Dạ.")]
