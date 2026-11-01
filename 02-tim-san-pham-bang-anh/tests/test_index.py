import numpy as np
import pytest

from src.index import CatalogIndex

PAYLOADS = [
    {"sku": "SP01", "loai": "Cốc", "ten": "Cốc đỏ"},
    {"sku": "SP02", "loai": "Cốc", "ten": "Cốc xanh"},
    {"sku": "SP03", "loai": "Giày", "ten": "Giày đỏ"},
]


@pytest.fixture
def index():
    # Vector 2 chiều tự đặt, không cần mô hình. Chỉ mục giữ trong bộ nhớ.
    index = CatalogIndex(path=None)
    index.build({
        "dang": np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]),
        "mau": np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]),
    }, PAYLOADS)
    yield index
    index.close()


def test_tim_theo_vector_co_ten(index):
    assert [hit.sku for hit in index.search("dang", np.array([1.0, 0.0]), k=2)] == ["SP01", "SP02"]
    assert {hit.sku for hit in index.search("mau", np.array([1.0, 0.0]), k=2)} == {"SP01", "SP03"}


def test_loc_theo_loai(index):
    hits = index.search("mau", np.array([1.0, 0.0]), k=3, category="Giày")
    assert [hit.sku for hit in hits] == ["SP03"]


def test_lay_lai_vector_da_luu(index):
    vectors = index.vectors_of("mau", ["SP02", "SP03"])
    assert set(vectors) == {"SP02", "SP03"}
    assert np.allclose(vectors["SP02"], [0.0, 1.0])
