from src.search import Candidate, rerank


def candidate(sku, dino, clip):
    return Candidate(sku, {"sku": sku}, dino, clip)


def test_clip_sua_mau_khi_dinov2_phan_van():
    # DINOv2 gần như hòa giữa hai túi khác màu; CLIP thấy rõ túi vàng mới đúng.
    candidates = [candidate("tui-xanh", 0.80, 0.78), candidate("tui-vang", 0.79, 0.88), candidate("coc", 0.60, 0.80)]
    assert rerank(candidates)[0][0].sku == "tui-vang"


def test_dinov2_chac_chan_thi_giu_dung_loai():
    # DINOv2 chắc chắn đây là cốc; CLIP chỉ hơi nghiêng về chai cùng màu.
    candidates = [candidate("coc-trang", 0.85, 0.80), candidate("chai-trang", 0.55, 0.83)]
    assert rerank(candidates)[0][0].sku == "coc-trang"


def test_giu_du_ung_vien_xep_giam_dan():
    candidates = [candidate("a", 0.7, 0.8), candidate("b", 0.6, 0.9), candidate("c", 0.5, 0.7)]
    scores = [score for _, score in rerank(candidates)]
    assert len(scores) == 3 and scores == sorted(scores, reverse=True)
