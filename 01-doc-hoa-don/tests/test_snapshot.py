"""Chạy phần tách trường trên kết quả OCR thật của 8 hóa đơn mẫu (data/ocr_snapshot.json)."""

import pandas as pd
import pytest

from src.evaluate import load_snapshot
from src.fields import amount_lines, find_date
from src.make_receipts import TRUTH_PATH

TRUTH = pd.read_csv(TRUTH_PATH).set_index("file")


@pytest.fixture(scope="module")
def snapshot():
    return load_snapshot()


@pytest.mark.parametrize("file", TRUTH.index)
def test_ngay_dung(snapshot, file):
    assert find_date(snapshot[file]) == TRUTH.at[file, "ngay"]


@pytest.mark.parametrize("file", TRUTH.index)
def test_tong_dung_nam_trong_cac_dong_so_tien(snapshot, file):
    # Nếu gom dòng sai thì số tiền tổng sẽ không đứng cùng dòng với nhãn của nó.
    assert TRUTH.at[file, "tong_tien"] in [line.amount for line in amount_lines(snapshot[file])]
