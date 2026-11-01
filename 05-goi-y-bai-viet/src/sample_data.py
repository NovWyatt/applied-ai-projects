"""Sinh lịch sử đọc giả lập và ghi ra data/history.csv.

Mỗi người dùng có một hồ sơ sở thích giả định. Năm trong mười hai người đổi sở
thích giữa chừng (ví dụ đang đọc Công nghệ thì chuyển sang Lập trình), để kiểm
tra bộ gợi ý có theo kịp sở thích mới hay không.

    python -m src.sample_data
"""

import random
import sys
from datetime import datetime, timedelta

import pandas as pd

from src.data import HISTORY_PATH, load_articles

# Mỗi giai đoạn: (tỷ trọng các chủ đề, số bài đọc). Giai đoạn sau nối tiếp giai đoạn trước.
PERSONAS: dict[str, list[tuple[dict[str, float], int]]] = {
    "u01": [({"Lập trình": 0.8, "Công nghệ": 0.2}, 11)],
    "u02": [({"Sản phẩm": 0.6, "Kinh doanh": 0.4}, 11)],
    "u03": [({"Sức khỏe": 0.6, "Du lịch": 0.4}, 10)],
    "u04": [({"Công nghệ": 1.0}, 6), ({"Lập trình": 1.0}, 5)],
    "u05": [({"Du lịch": 1.0}, 6), ({"Kinh doanh": 1.0}, 5)],
    "u06": [({"Công nghệ": 0.5, "Sản phẩm": 0.5}, 10)],
    "u07": [({"Kinh doanh": 0.85, "Sản phẩm": 0.15}, 10)],
    "u08": [({"Sức khỏe": 1.0}, 6), ({"Công nghệ": 1.0}, 5)],
    "u09": [({"Lập trình": 0.5, "Sản phẩm": 0.5}, 11)],
    "u10": [({"Du lịch": 0.8, "Sức khỏe": 0.2}, 9)],
    "u11": [({"Sản phẩm": 1.0}, 5), ({"Lập trình": 1.0}, 5)],
    "u12": [({"Kinh doanh": 1.0}, 5), ({"Sức khỏe": 1.0}, 5)],
}


def changes_interest(user_id: str) -> bool:
    return len(PERSONAS.get(user_id, [])) > 1


def generate(articles: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    by_topic = {topic: list(group["article_id"]) for topic, group in articles.groupby("topic")}
    # Vài bài "hot" được nhiều người đọc hơn hẳn, giống dữ liệu thật.
    appeal = {article_id: rng.paretovariate(1.5) for article_id in articles["article_id"]}

    rows = []
    for user_id, phases in PERSONAS.items():
        read: set[str] = set()
        clock = datetime(2026, 9, 1, 8) + timedelta(hours=rng.randint(0, 72))
        for topic_weights, n_reads in phases:
            for _ in range(n_reads):
                open_topics = {t: w for t, w in topic_weights.items() if set(by_topic[t]) - read}
                topic = rng.choices(list(open_topics), weights=list(open_topics.values()))[0]
                unread = [a for a in by_topic[topic] if a not in read]
                article_id = rng.choices(unread, weights=[appeal[a] for a in unread])[0]
                read.add(article_id)
                clock += timedelta(hours=rng.randint(3, 40), minutes=rng.randint(0, 59))
                rows.append({"user_id": user_id, "article_id": article_id,
                             "read_at": clock.isoformat(timespec="minutes")})
    return pd.DataFrame(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    history = generate(load_articles())
    history.to_csv(HISTORY_PATH, index=False)
    print(f"Đã ghi {len(history)} lượt đọc của {history['user_id'].nunique()} người dùng vào {HISTORY_PATH}")


if __name__ == "__main__":
    main()
