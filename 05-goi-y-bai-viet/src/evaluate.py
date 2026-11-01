"""Đánh giá bộ gợi ý bằng cách giấu những bài đọc gần nhất.

Với mỗi người dùng, giấu N_HIDDEN bài đọc cuối, dựng hồ sơ từ phần còn lại, rồi
xem bài bị giấu có nằm trong top-k gợi ý không (HitRate@k). Bài đọc gần nhất là
thứ khó đoán nhất với người vừa đổi sở thích, nên cách chia này phơi ra đúng
điểm yếu của hồ sơ "mọi bài như nhau".

    python -m src.evaluate
"""

import sys
from collections.abc import Callable

import numpy as np
import pandas as pd

from src.data import load_articles, load_history
from src.recommender import ArticleRecommender, profile_weights
from src.sample_data import changes_interest

N_HIDDEN = 2
KS = (3, 5)

RecommendFn = Callable[[ArticleRecommender, list[str], int], pd.DataFrame]


def split_last(history: pd.DataFrame, n_hidden: int = N_HIDDEN) -> tuple[pd.DataFrame, pd.DataFrame]:
    hidden = history.groupby("user_id").cumcount(ascending=False) < n_hidden
    return history[~hidden], history[hidden]


def half_life(n_reads_to_halve: float) -> Callable[[int], np.ndarray]:
    """Trọng số giảm một nửa sau mỗi n_reads_to_halve bài, tính ngược từ bài mới nhất."""
    return lambda n: 0.5 ** ((n - 1 - np.arange(n)) / n_reads_to_halve)


def with_weighting(weighting: Callable[[int], np.ndarray]) -> RecommendFn:
    return lambda rec, reads, k: rec.recommend(reads, k, weighting=weighting)


STRATEGIES: list[tuple[str, RecommendFn]] = [
    ("Bài phổ biến nhất (mốc so sánh)", lambda rec, reads, k: rec.popular(reads, k)),
    ("Hồ sơ: mọi bài như nhau", with_weighting(lambda n: np.ones(n))),
    ("Hồ sơ: giảm nửa sau 6 bài", with_weighting(half_life(6))),
    ("Hồ sơ: giảm nửa sau 3 bài", with_weighting(half_life(3))),
    ("Hồ sơ: giảm nửa sau 1 bài", with_weighting(half_life(1))),
    ("Hồ sơ: chỉ bài mới nhất", with_weighting(lambda n: np.eye(n)[-1])),
]


def evaluate(recommend_fn: RecommendFn, rec: ArticleRecommender,
             train: pd.DataFrame, hidden: pd.DataFrame) -> dict[str, str]:
    hits = []  # (k, người dùng có đổi sở thích không, trúng hay trượt) cho từng bài bị giấu
    for user_id, group in hidden.groupby("user_id"):
        reads = train.loc[train["user_id"] == user_id, "article_id"].tolist()
        recommended = recommend_fn(rec, reads, max(KS))["article_id"].tolist()
        for article_id in group["article_id"]:
            for k in KS:
                hits.append((k, changes_interest(user_id), article_id in recommended[:k]))
    hits = pd.DataFrame(hits, columns=["k", "changes", "hit"])

    row = {f"Hit@{k}": f"{hits.loc[hits.k == k, 'hit'].mean():.0%}" for k in KS}
    top = hits[hits.k == max(KS)]
    row[f"Hit@{max(KS)} ổn định"] = f"{top.loc[~top.changes, 'hit'].mean():.0%}"
    row[f"Hit@{max(KS)} đổi sở thích"] = f"{top.loc[top.changes, 'hit'].mean():.0%}"
    return row


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    articles, history = load_articles(), load_history()
    train, hidden = split_last(history)
    # Độ phổ biến chỉ được tính trên phần không bị giấu, tránh lộ đáp án.
    rec = ArticleRecommender(articles, train)
    print(f"{len(articles)} bài viết, {history['user_id'].nunique()} người dùng, {len(history)} lượt đọc. "
          f"Giấu {N_HIDDEN} bài cuối của mỗi người ({len(hidden)} bài).\n")

    strategies = list(STRATEGIES)
    try:
        profile_weights(3)
        strategies.append(("→ profile_weights đang dùng", with_weighting(profile_weights)))
    except NotImplementedError:
        print("(profile_weights chưa được viết, bỏ qua dòng cách đang dùng)\n")

    table = pd.DataFrame([{"Cách làm": name, **evaluate(fn, rec, train, hidden)} for name, fn in strategies])
    print(table.to_string(index=False))
    n_candidates = len(articles) - history.groupby("user_id").size().mean() + N_HIDDEN
    print(f"\nChọn ngẫu nhiên: Hit@5 khoảng {5 / n_candidates:.0%}")


if __name__ == "__main__":
    main()
