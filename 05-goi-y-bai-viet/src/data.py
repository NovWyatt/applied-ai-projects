"""Đọc kho bài viết và lịch sử đọc."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTICLES_PATH = DATA_DIR / "articles.csv"
HISTORY_PATH = DATA_DIR / "history.csv"


def load_articles(path: Path = ARTICLES_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def load_history(path: Path = HISTORY_PATH) -> pd.DataFrame:
    history = pd.read_csv(path, parse_dates=["read_at"])
    return history.sort_values(["user_id", "read_at"]).reset_index(drop=True)


def reads_of(history: pd.DataFrame, user_id: str) -> list[str]:
    """Các bài người dùng đã đọc, từ cũ nhất đến mới nhất."""
    return history.loc[history["user_id"] == user_id, "article_id"].tolist()
