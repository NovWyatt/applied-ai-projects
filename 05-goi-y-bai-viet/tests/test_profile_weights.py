import numpy as np

from src.recommender import profile_weights


def test_moi_bai_co_mot_trong_so_duong():
    weights = np.asarray(profile_weights(6))
    assert weights.shape == (6,)
    assert (weights > 0).all()


def test_bai_moi_khong_nhe_hon_bai_cu():
    weights = np.asarray(profile_weights(10))
    assert weights[-1] >= weights[0]


def test_chi_mot_bai():
    assert np.asarray(profile_weights(1)).shape == (1,)
