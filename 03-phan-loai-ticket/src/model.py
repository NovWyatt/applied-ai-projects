"""Mô hình phân loại ticket và quy tắc chọn nhóm tiếp nhận."""

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from src.text import normalize_text

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "ticket_router.joblib"
NEEDS_REVIEW = "Cần kiểm tra"

# Chọn theo đánh giá 5-fold trong `python -m src.train`: tự chuyển ~70% ticket, đúng ~99%.
MIN_CONFIDENCE = 0.50  # nhóm đứng đầu phải chiếm ít nhất một nửa xác suất
MIN_MARGIN = 0.20      # và bỏ xa nhóm thứ hai, để bắt ca phân vân giữa hai nhóm


def build_pipeline() -> Pipeline:
    """TF-IDF theo từ và theo cụm ký tự, rồi hồi quy logistic.

    - Theo từ (1-2 từ): bắt được cụm có nghĩa như "dang nhap", "hoan tien".
    - Theo cụm ký tự (2-5 ký tự): chịu được lỗi gõ như "dang nhaap", "tru tienn".
    Hồi quy logistic trả về xác suất, cần cho quyết định "Cần kiểm tra".
    """
    features = FeatureUnion([
        ("word", TfidfVectorizer(preprocessor=normalize_text, ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(preprocessor=normalize_text, analyzer="char_wb", ngram_range=(2, 5),
                                 sublinear_tf=True)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def rank_groups(pipeline: Pipeline, text: str) -> list[tuple[str, float]]:
    """Trả về [(nhóm, xác suất), ...] xếp từ cao xuống thấp."""
    probabilities = pipeline.predict_proba([text])[0]
    ranked = sorted(zip(pipeline.classes_, probabilities), key=lambda pair: pair[1], reverse=True)
    return [(str(group), float(p)) for group, p in ranked]


def choose_group(ranked: list[tuple[str, float]]) -> str:
    """Chọn nhóm tiếp nhận từ kết quả của rank_groups.

    Trả về tên nhóm khi đủ tin cậy để tự chuyển, ngược lại trả về NEEDS_REVIEW
    để người xử lý quyết định.
    """
    best_group, best_p = ranked[0]
    second_p = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_p >= MIN_CONFIDENCE and best_p - second_p >= MIN_MARGIN:
        return best_group
    return NEEDS_REVIEW
