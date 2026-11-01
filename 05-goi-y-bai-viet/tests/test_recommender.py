import pytest

from src.data import load_articles, load_history
from src.recommender import POPULAR_REASON, ArticleRecommender

PYTHON_READS = ["a11", "a14", "a17"]  # pytest, FastAPI, async


@pytest.fixture(scope="module")
def recommender():
    return ArticleRecommender(load_articles(), load_history())


def test_khong_goi_y_bai_da_doc(recommender):
    recommended = recommender.recommend(PYTHON_READS, k=10)["article_id"]
    assert not set(recommended) & set(PYTHON_READS)


def test_doc_python_thi_bai_dau_la_lap_trinh(recommender):
    assert recommender.recommend(PYTHON_READS, k=3)["topic"].iloc[0] == "Lập trình"


def test_ly_do_tro_ve_mot_bai_da_doc(recommender):
    titles = load_articles().set_index("article_id").loc[PYTHON_READS, "title"]
    reasons = recommender.recommend(PYTHON_READS, k=3)["reason"]
    assert all(any(title in reason for title in titles) for reason in reasons)


def test_nguoi_moi_nhan_bai_pho_bien(recommender):
    recommended = recommender.recommend([], k=3)
    assert len(recommended) == 3
    assert (recommended["reason"] == POPULAR_REASON).all()


def test_bo_qua_bai_khong_con_trong_kho(recommender):
    recommended = recommender.recommend(["a11", "bai-da-xoa"], k=3)
    assert len(recommended) == 3
