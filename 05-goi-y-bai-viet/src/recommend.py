"""Xem gợi ý cho một người dùng.

Chạy từ thư mục 05-goi-y-bai-viet:

    python -m src.recommend u04
    python -m src.recommend u04 -k 10
    python -m src.recommend khach-moi     # chưa có lịch sử: gợi ý bài phổ biến
"""

import argparse
import sys

from src.data import load_articles, load_history, reads_of
from src.recommender import ArticleRecommender

N_RECENT = 5


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Gợi ý bài viết cho một người dùng.")
    parser.add_argument("user_id", help="ví dụ u01 ... u12")
    parser.add_argument("-k", type=int, default=5, help="số bài gợi ý (mặc định 5)")
    args = parser.parse_args()

    articles, history = load_articles(), load_history()
    reads = reads_of(history, args.user_id)
    by_id = articles.set_index("article_id")

    if reads:
        print(f"{args.user_id} đã đọc {len(reads)} bài. {N_RECENT} bài gần nhất:")
        for article_id in reads[-N_RECENT:]:
            print(f"  [{by_id.at[article_id, 'topic']}] {by_id.at[article_id, 'title']}")
    else:
        print(f"{args.user_id} chưa đọc bài nào.")

    recommendations = ArticleRecommender(articles, history).recommend(reads, k=args.k)
    print(f"\nGợi ý:\n{recommendations.drop(columns='article_id').to_string(index=False)}")


if __name__ == "__main__":
    main()
