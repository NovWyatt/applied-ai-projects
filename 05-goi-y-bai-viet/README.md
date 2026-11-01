# 05 · Gợi ý bài viết

Đề xuất nội dung từ lịch sử tương tác, và theo kịp khi sở thích của người đọc thay đổi.

**Trạng thái:** ✅ Chạy được · Hit@5 = 54% trên dữ liệu mẫu (chọn ngẫu nhiên khoảng 10%)

## Bài toán

Người đọc dễ bỏ đi khi không thấy bài nào hợp gu. Dự án học sở thích từ những bài đã đọc và gợi ý các bài tiếp theo, kèm lý do vì sao gợi ý.

## Luồng xử lý

1. **Lịch sử đã đọc** của người dùng, xếp từ cũ đến mới.
2. Tổng hợp thành **hồ sơ sở thích**: trung bình có trọng số các vector TF-IDF của những bài đã đọc, bài càng gần đây càng nặng.
3. Chọn **ứng viên**: các bài người dùng chưa đọc.
4. **Xếp hạng** ứng viên theo độ tương đồng cosine với hồ sơ.
5. Trả về **bài viết gợi ý**, mỗi bài kèm lý do "Vì bạn đã đọc: …" (bài đã đọc giống nó nhất).

Người chưa đọc bài nào nhận các bài được đọc nhiều nhất.

## Quyết định chính: bài cũ và bài mới nặng nhẹ ra sao

Trọng số của một bài đã đọc giảm một nửa sau mỗi 3 bài đọc tiếp theo ([src/recommender.py](src/recommender.py)). Con số này được chọn bằng đánh giá chứ không theo cảm tính:

| Cách gán trọng số | Hit@3 | Hit@5 | Người ổn định | Người đổi sở thích |
|---|---|---|---|---|
| Bài phổ biến nhất (mốc so sánh) | 4% | 8% | 7% | 10% |
| Mọi bài như nhau | 21% | 38% | 57% | **10%** |
| Giảm nửa sau 6 bài | 33% | 50% | 50% | 50% |
| **Giảm nửa sau 3 bài** (đang dùng) | **33%** | **54%** | **57%** | **50%** |
| Giảm nửa sau 1 bài | 38% | 46% | 50% | 40% |
| Chỉ bài mới nhất | 25% | 33% | 43% | 20% |

- **Mọi bài như nhau** không theo kịp người đổi sở thích: 6 bài Công nghệ cũ lấn át 3 bài Lập trình mới, kết quả chỉ ngang chọn ngẫu nhiên.
- **Chỉ nhìn bài mới nhất** thì hồ sơ quá ít chữ, dễ lệch vì một từ ngẫu nhiên.
- Thêm mức sàn cho bài cũ (giữ sở thích lâu dài) không cải thiện thêm trên dữ liệu này.

**Cách đánh giá:** với mỗi người dùng, giấu 2 bài đọc cuối cùng, dựng hồ sơ từ phần còn lại, rồi xem bài bị giấu có nằm trong top-k gợi ý không (HitRate@k). Độ phổ biến cũng chỉ tính trên phần không bị giấu để tránh lộ đáp án.

> Dữ liệu mẫu nhỏ (24 bài bị giấu), nên chênh lệch vài phần trăm giữa các dòng chưa đủ ý nghĩa thống kê. Chênh lệch giữa "mọi bài như nhau" và các cách ưu tiên bài gần đây thì đủ rõ.

## Hạn chế

TF-IDF so khớp theo **chữ**, không theo **nghĩa**. Ví dụ người đọc "Cấu trúc dữ liệu cần biết khi đi phỏng vấn" (phỏng vấn xin việc) được gợi ý "Phỏng vấn người dùng" (nghiên cứu sản phẩm) chỉ vì trùng chữ "phỏng vấn". Thay TF-IDF bằng embedding từ mô hình ngôn ngữ sẽ phân biệt được hai nghĩa này, đổi lại cần tải mô hình và chạy chậm hơn.

## Dữ liệu mẫu

- [data/articles.csv](data/articles.csv): 60 bài tự viết thuộc 6 chủ đề (Công nghệ, Lập trình, Sản phẩm, Kinh doanh, Sức khỏe, Du lịch), có tiêu đề, thẻ và tóm tắt.
- [data/history.csv](data/history.csv): 125 lượt đọc của 12 người dùng giả lập, sinh bằng [src/sample_data.py](src/sample_data.py). Năm người đổi sở thích giữa chừng, ví dụ đang đọc Công nghệ thì chuyển sang Lập trình.

## Cách chạy

Từ thư mục `05-goi-y-bai-viet`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

python -m src.recommend u04     # gợi ý cho người dùng u04
python -m src.evaluate          # bảng đánh giá ở trên
pytest                          # chạy test
python -m src.sample_data       # sinh lại data/history.csv (không bắt buộc)
```

Ví dụ với u04, người chuyển từ đọc Công nghệ sang Lập trình:

```
u04 đã đọc 11 bài. 5 bài gần nhất:
  [Lập trình] Docker cho lập trình viên: đóng gói ứng dụng
  [Lập trình] Dùng trợ lý AI để viết code an toàn
  [Lập trình] Async trong Python: khi nào nên dùng
  [Lập trình] Cấu trúc dữ liệu cần biết khi đi phỏng vấn
  [Lập trình] TypeScript cho người viết JavaScript

Gợi ý:
                                     title     topic  score                                              reason
          Đọc code của người khác hiệu quả Lập trình  0.157  Vì bạn đã đọc: Dùng trợ lý AI để viết code an toàn
Viết test với pytest cho người mới bắt đầu Lập trình  0.124  Vì bạn đã đọc: Dùng trợ lý AI để viết code an toàn
  Phỏng vấn người dùng: hỏi gì để không... Sản phẩm   0.120  Vì bạn đã đọc: Cấu trúc dữ liệu cần biết khi đi phỏng vấn
...
```

## Cấu trúc

```
05-goi-y-bai-viet/
├── data/
│   ├── articles.csv        kho bài viết
│   └── history.csv         lịch sử đọc giả lập
├── src/
│   ├── text.py             chuẩn hóa tiếng Việt
│   ├── data.py             đọc dữ liệu
│   ├── recommender.py      hồ sơ sở thích, xếp hạng, lý do gợi ý
│   ├── evaluate.py         đánh giá giấu bài cuối
│   ├── recommend.py        CLI
│   └── sample_data.py      sinh lịch sử đọc
└── tests/                  pytest
```

## Công nghệ

Python 3.12 · Pandas · scikit-learn · pytest
