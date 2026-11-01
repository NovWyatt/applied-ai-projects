"""Gợi ý bài viết dựa trên nội dung những bài người dùng đã đọc.

Luồng: lịch sử đã đọc → hồ sơ sở thích (trung bình có trọng số các vector TF-IDF)
→ ứng viên là các bài chưa đọc → xếp hạng theo độ tương đồng cosine → bài gợi ý.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from src.text import normalize_text

POPULAR_REASON = "Được nhiều người đọc"

# Trọng số giảm một nửa sau mỗi 3 bài đọc, tính ngược từ bài mới nhất.
# Chọn theo `python -m src.evaluate`: cho mọi bài như nhau thì người đổi sở thích
# chỉ trúng 10%; giảm quá nhanh (1 bài) thì hồ sơ quá ít dữ liệu, kết quả dao động.
HALF_LIFE_READS = 3


def profile_weights(n_reads: int) -> np.ndarray:
    """Trọng số của từng bài đã đọc khi dựng hồ sơ sở thích.

    Bài thứ i trong lịch sử (0 là cũ nhất, n_reads - 1 là mới nhất) nhận
    trọng số thứ i. Chỉ tỷ lệ giữa các trọng số là quan trọng, vì hồ sơ
    được chuẩn hóa lại sau khi cộng.
    """
    reads_ago = n_reads - 1 - np.arange(n_reads)  # 0 với bài mới nhất
    return 0.5 ** (reads_ago / HALF_LIFE_READS)


class ArticleRecommender:
    def __init__(self, articles: pd.DataFrame, history: pd.DataFrame | None = None):
        self.articles = articles.reset_index(drop=True)
        self._row = {article_id: i for i, article_id in enumerate(self.articles["article_id"])}

        text = (self.articles["title"] + ". " + self.articles["tags"].str.replace(";", ", ")
                + ". " + self.articles["summary"])
        vectorizer = TfidfVectorizer(preprocessor=normalize_text, ngram_range=(1, 2), sublinear_tf=True)
        # Mỗi dòng đã được chuẩn hóa L2, nên tích vô hướng chính là độ tương đồng cosine.
        self._matrix = vectorizer.fit_transform(text)

        counts = history["article_id"].value_counts() if history is not None else pd.Series(dtype=int)
        self._popularity = counts.reindex(self.articles["article_id"], fill_value=0).to_numpy()

    def recommend(self, read_ids: list[str], k: int = 5,
                  weighting: Callable[[int], np.ndarray] | None = None) -> pd.DataFrame:
        """Top-k bài chưa đọc, kèm điểm và lý do gợi ý.

        read_ids xếp từ cũ đến mới. Người chưa đọc gì thì nhận bài phổ biến.
        """
        rows = [self._row[a] for a in read_ids if a in self._row]
        if not rows:
            return self.popular(read_ids, k)

        weights = np.asarray((weighting or profile_weights)(len(rows)), dtype=float)
        profile = self._matrix[rows].T @ weights
        norm = np.linalg.norm(profile)
        if norm == 0:
            return self.popular(read_ids, k)
        profile /= norm

        scores = self._matrix @ profile
        scores[rows] = -np.inf
        top = np.argsort(-scores, kind="stable")[:k]

        # Lý do: bài đã đọc giống bài được gợi ý nhất.
        similarity = (self._matrix[top] @ self._matrix[rows].T).toarray()
        closest = [rows[j] for j in similarity.argmax(axis=1)]
        reasons = [f"Vì bạn đã đọc: {self.articles.at[r, 'title']}" for r in closest]
        return self._result(top, scores[top], reasons)

    def popular(self, read_ids: list[str], k: int = 5) -> pd.DataFrame:
        """Bài được đọc nhiều nhất mà người dùng chưa đọc. Điểm là tỷ lệ lượt đọc."""
        read = {self._row[a] for a in read_ids if a in self._row}
        order = [i for i in np.argsort(-self._popularity, kind="stable") if i not in read][:k]
        share = self._popularity[order] / max(self._popularity.sum(), 1)
        return self._result(np.array(order), share, [POPULAR_REASON] * len(order))

    def _result(self, rows: np.ndarray, scores: np.ndarray, reasons: list[str]) -> pd.DataFrame:
        result = self.articles.loc[rows, ["article_id", "title", "topic"]].reset_index(drop=True)
        result["score"] = np.round(scores, 3)
        result["reason"] = reasons
        return result
