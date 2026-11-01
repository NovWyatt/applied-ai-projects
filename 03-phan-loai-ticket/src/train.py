"""Huấn luyện mô hình phân loại ticket, đánh giá và lưu ra models/.

Chạy từ thư mục 03-phan-loai-ticket:

    python -m src.train
"""

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from src.model import (DEFAULT_MODEL_PATH, MIN_CONFIDENCE, MIN_MARGIN, NEEDS_REVIEW, build_pipeline,
                       choose_group)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "tickets.csv"
THRESHOLDS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]


def load_tickets(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["text"] = df["text"].str.strip()
    return df.dropna().drop_duplicates(subset="text").reset_index(drop=True)


def out_of_fold_probabilities(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Xác suất của từng ticket, do mô hình CHƯA được học ticket đó chấm.

    Dữ liệu ít nên dùng 5-fold thay vì tách một tập test cố định: mọi ticket
    đều được chấm đúng một lần mà vẫn không bị lộ đáp án.
    """
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    proba = cross_val_predict(build_pipeline(), df["text"], df["group"], cv=cv, method="predict_proba")
    # Cột của predict_proba theo thứ tự nhóm đã sắp xếp, giống np.unique.
    return np.unique(df["group"]), proba


def threshold_table(y_true: np.ndarray, predicted: np.ndarray, confidence: np.ndarray) -> pd.DataFrame:
    rows = []
    for threshold in THRESHOLDS:
        auto = confidence >= threshold
        correct = predicted[auto] == y_true[auto]
        rows.append({
            "Ngưỡng": f"{threshold:.2f}",
            "Tự chuyển": f"{auto.mean():.0%}",
            "Đúng trong số tự chuyển": f"{correct.mean():.0%}" if auto.any() else "-",
            "Chuyển nhầm": int((~correct).sum()),
            "Cần kiểm tra": int((~auto).sum()),
        })
    return pd.DataFrame(rows)


def routing_summary(classes: np.ndarray, proba: np.ndarray, y_true: np.ndarray) -> str:
    """Kết quả của quy tắc choose_group đang dùng, trên xác suất 5-fold."""
    routed = np.array([
        choose_group(sorted(zip(classes, row), key=lambda pair: pair[1], reverse=True))
        for row in proba
    ])
    auto = routed != NEEDS_REVIEW
    correct = routed[auto] == y_true[auto]
    return (f"Tự chuyển {auto.mean():.0%} ({auto.sum()} ticket), đúng {correct.mean():.0%}, "
            f"chuyển nhầm {(~correct).sum()}, cần kiểm tra {(~auto).sum()}")


def main() -> None:
    # Khi chuyển hướng ra file, console Windows có thể không dùng UTF-8.
    sys.stdout.reconfigure(encoding="utf-8")

    df = load_tickets()
    print(f"Dữ liệu: {len(df)} ticket")
    print(df["group"].value_counts().to_string(), "\n")

    classes, proba = out_of_fold_probabilities(df)
    y_true = df["group"].to_numpy()
    predicted = classes[proba.argmax(axis=1)]
    confidence = proba.max(axis=1)

    print("== Đánh giá 5-fold ==")
    print(classification_report(y_true, predicted, digits=3, zero_division=0))
    print(pd.crosstab(pd.Series(y_true, name="Thực tế"), pd.Series(predicted, name="Dự đoán")).to_string(), "\n")

    print("== Nếu chỉ tự chuyển khi xác suất cao nhất >= ngưỡng ==")
    print(threshold_table(y_true, predicted, confidence).to_string(index=False), "\n")

    print(f"== Quy tắc đang dùng (MIN_CONFIDENCE={MIN_CONFIDENCE}, MIN_MARGIN={MIN_MARGIN}) ==")
    print(routing_summary(classes, proba, y_true), "\n")

    wrong = df.assign(predicted=predicted, confidence=confidence.round(2))[predicted != y_true]
    print("== Ticket bị đoán sai (tự tin nhất trước) ==")
    print(wrong.sort_values("confidence", ascending=False).head(10).to_string(index=False), "\n")

    pipeline = build_pipeline().fit(df["text"], df["group"])
    DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, DEFAULT_MODEL_PATH)
    print(f"Đã lưu mô hình: {DEFAULT_MODEL_PATH}")


if __name__ == "__main__":
    main()
