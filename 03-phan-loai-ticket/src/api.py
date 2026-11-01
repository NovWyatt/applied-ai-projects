"""API nhận ticket mới và gợi ý nhóm tiếp nhận.

Chạy từ thư mục 03-phan-loai-ticket (cần huấn luyện trước bằng `python -m src.train`):

    uvicorn src.api:app --reload

Mở http://127.0.0.1:8000/docs để thử trực tiếp trên trình duyệt.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import joblib
from fastapi import FastAPI, Request
from pydantic import BaseModel, StringConstraints

from src.model import DEFAULT_MODEL_PATH, NEEDS_REVIEW, choose_group, rank_groups

TicketText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=5000)]


class TicketIn(BaseModel):
    text: TicketText


class GroupScore(BaseModel):
    group: str
    probability: float


class RoutingResult(BaseModel):
    group: str
    needs_review: bool
    confidence: float
    scores: list[GroupScore]


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(os.environ.get("TICKET_MODEL_PATH", DEFAULT_MODEL_PATH))
    if not model_path.exists():
        raise RuntimeError(f"Chưa có mô hình tại {model_path}. Chạy `python -m src.train` trước.")
    app.state.pipeline = joblib.load(model_path)
    yield


app = FastAPI(title="Phân loại ticket", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tickets/route", response_model=RoutingResult)
def route_ticket(ticket: TicketIn, request: Request) -> RoutingResult:
    ranked = rank_groups(request.app.state.pipeline, ticket.text)
    group = choose_group(ranked)
    return RoutingResult(
        group=group,
        needs_review=group == NEEDS_REVIEW,
        confidence=round(ranked[0][1], 4),
        scores=[GroupScore(group=g, probability=round(p, 4)) for g, p in ranked],
    )
