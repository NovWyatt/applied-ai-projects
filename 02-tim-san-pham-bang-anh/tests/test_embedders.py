import numpy as np
from PIL import Image

from src.embedders import ColorHistogram, pad_to_square


def test_them_vien_cho_vuong_khong_cat_anh():
    image = Image.new("RGB", (400, 300), (200, 30, 30))
    square = pad_to_square(image)
    assert square.size == (400, 400)
    # Ảnh gốc nằm giữa, không bị cắt mất cột nào.
    assert square.getpixel((0, 200)) == (200, 30, 30) and square.getpixel((399, 200)) == (200, 30, 30)


def test_bieu_do_mau_da_chuan_hoa():
    red, blue = Image.new("RGB", (64, 64), (220, 20, 20)), Image.new("RGB", (64, 64), (20, 20, 220))
    vectors = ColorHistogram().embed([red, red, blue])
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1)
    assert vectors[0] @ vectors[1] > 0.99   # cùng màu
    assert vectors[0] @ vectors[2] < 0.1    # khác màu
