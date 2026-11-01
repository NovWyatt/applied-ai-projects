# 03 · Phân loại ticket

Gợi ý đúng nhóm tiếp nhận, và biết lúc nào nên để người quyết định.

**Trạng thái:** ✅ Chạy được · đúng 85% trên dữ liệu mẫu (5-fold), tự chuyển 70% ticket với độ chính xác 99%

## Bài toán

Ticket hỗ trợ đến từ nhiều kênh và thường bị chuyển nhầm nhóm. Dự án đọc nội dung ticket mới và gợi ý nhóm tiếp nhận phù hợp.

| Ticket mới | Nhóm tiếp nhận |
|------------|----------------|
| Không đăng nhập | Tài khoản |
| Lỗi thanh toán | Thanh toán |
| Ứng dụng treo | Kỹ thuật |

Khi mô hình **không đủ tin cậy**, ticket không bị đoán bừa mà chuyển sang trạng thái **Cần kiểm tra** để người xử lý quyết định.

## Cách làm

```
văn bản ─► bỏ dấu, chữ thường ─► TF-IDF theo từ + theo cụm ký tự ─► hồi quy logistic ─► xác suất từng nhóm ─► quy tắc chọn nhóm
```

- **Bỏ dấu tiếng Việt** ([src/text.py](src/text.py)): người dùng hay gõ không dấu, nên "đăng nhập" và "dang nhap" được đưa về cùng một từ. Chữ "đ" phải đổi riêng vì Unicode không coi nó là "d" cộng dấu.
- **Hai loại đặc trưng** ([src/model.py](src/model.py)): TF-IDF theo 1-2 từ bắt cụm có nghĩa như "hoan tien"; TF-IDF theo cụm 2-5 ký tự chịu được lỗi gõ.
- **Hồi quy logistic** vì nó trả về xác suất, thứ cần cho quyết định "Cần kiểm tra".
- **Quy tắc chọn nhóm**: chỉ tự chuyển khi nhóm đứng đầu có xác suất ≥ 0.50 **và** hơn nhóm thứ hai ≥ 0.20. Điều kiện thứ hai bắt những ca phân vân giữa hai nhóm, ví dụ "App bị treo khi bấm nút thanh toán".

## Kết quả

Đánh giá bằng 5-fold cross-validation trên 144 ticket mẫu (mỗi ticket được chấm bởi mô hình chưa thấy nó):

| | Precision | Recall |
|---|---|---|
| Kỹ thuật | 0.81 | 0.88 |
| Thanh toán | 0.88 | 0.88 |
| Tài khoản | 0.89 | 0.81 |
| **Chung** | | **0.85** |

Đánh đổi giữa tự động hóa và độ chính xác:

| Quy tắc | Tự chuyển | Đúng trong số tự chuyển | Chuyển nhầm |
|---|---|---|---|
| Luôn chọn nhóm cao nhất | 100% | 85% | 21 |
| Xác suất ≥ 0.50 | 73% | 97% | 3 |
| **Xác suất ≥ 0.50 và hơn nhóm thứ hai ≥ 0.20** (đang dùng) | **70%** | **99%** | **1** |

Ngưỡng được chọn từ số liệu chứ không theo cảm tính: với 3 nhóm và ít dữ liệu, xác suất cao nhất hiếm khi vượt 0.7, nên ngưỡng "80%" sẽ đẩy 94% ticket sang người kiểm tra. Chạy `python -m src.train` để xem bảng đầy đủ.

> Dữ liệu mẫu nhỏ và tự viết, nên các con số trên dùng để minh họa cách đánh giá, không đại diện cho dữ liệu thật.

## Dữ liệu mẫu

[data/tickets.csv](data/tickets.csv): 144 ticket tự viết, mỗi nhóm 48, gồm câu có dấu, không dấu, tiếng Anh và vài câu cố tình mơ hồ. Không dùng nội dung ticket thật.

## Cách chạy

Từ thư mục `03-phan-loai-ticket`:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

python -m src.train             # đánh giá và lưu mô hình vào models/
uvicorn src.api:app --reload    # chạy API ở http://127.0.0.1:8000
pytest                          # chạy test
```

Mở http://127.0.0.1:8000/docs để thử trên trình duyệt, hoặc gọi trực tiếp:

```bash
curl -X POST http://127.0.0.1:8000/tickets/route \
  -H "Content-Type: application/json" \
  -d '{"text": "Hôm qua tôi bị trừ tiền 2 lần khi mua gói năm"}'
```

```json
{
  "group": "Thanh toán",
  "needs_review": false,
  "confidence": 0.7006,
  "scores": [
    {"group": "Thanh toán", "probability": 0.7006},
    {"group": "Kỹ thuật", "probability": 0.1549},
    {"group": "Tài khoản", "probability": 0.1445}
  ]
}
```

Câu không đủ thông tin như "Cho mình hỏi chút" sẽ trả về `"group": "Cần kiểm tra"`, `"needs_review": true`.

## Cấu trúc

```
03-phan-loai-ticket/
├── data/tickets.csv        dữ liệu mẫu
├── src/
│   ├── text.py             chuẩn hóa tiếng Việt
│   ├── model.py            pipeline và quy tắc chọn nhóm
│   ├── train.py            đánh giá 5-fold, lưu mô hình
│   └── api.py              FastAPI
└── tests/                  pytest
```

## Công nghệ

Python 3.12 · scikit-learn · FastAPI · pytest
