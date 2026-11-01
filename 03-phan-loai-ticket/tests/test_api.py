import joblib
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.model import NEEDS_REVIEW, build_pipeline
from src.train import load_tickets


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Huấn luyện mô hình tạm để test không phụ thuộc vào models/ trên máy.
    df = load_tickets()
    model_path = tmp_path_factory.mktemp("models") / "ticket_router.joblib"
    joblib.dump(build_pipeline().fit(df["text"], df["group"]), model_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("TICKET_MODEL_PATH", str(model_path))
        with TestClient(app) as test_client:
            yield test_client


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ticket_ro_rang_xep_dung_nhom_dau(client):
    response = client.post("/tickets/route", json={"text": "Tôi bị trừ tiền hai lần khi gia hạn gói"})
    body = response.json()

    assert response.status_code == 200
    assert body["scores"][0]["group"] == "Thanh toán"
    assert body["needs_review"] == (body["group"] == NEEDS_REVIEW)
    assert sum(s["probability"] for s in body["scores"]) == pytest.approx(1, abs=1e-3)


def test_ticket_rong_bi_tu_choi(client):
    assert client.post("/tickets/route", json={"text": "   "}).status_code == 422
