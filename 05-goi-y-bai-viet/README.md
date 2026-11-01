# 05 · Gợi ý bài viết

Đề xuất nội dung từ lịch sử tương tác.

**Trạng thái:** 🚧 Chưa làm

## Bài toán

Người đọc dễ bỏ đi khi không thấy bài nào hợp gu. Dự án học sở thích từ những bài đã đọc và gợi ý các bài tiếp theo.

## Luồng xử lý

1. **Lịch sử đã đọc** của người dùng.
2. Tổng hợp thành **hồ sơ sở thích**, ví dụ: Công nghệ, Lập trình, Sản phẩm.
3. Chọn **ứng viên** từ kho bài viết.
4. **Xếp hạng** ứng viên theo mức độ phù hợp.
5. Trả về **bài viết gợi ý**.

Hướng tiếp cận dự kiến: TF-IDF kết hợp cosine similarity. Có thể thay bằng embedding nếu cần chất lượng cao hơn.

## Công nghệ

Python · Pandas · scikit-learn

## Dữ liệu mẫu

Đặt trong `data/`. Dùng bài viết và lịch sử đọc tự tạo.

## Cách chạy

Sẽ bổ sung khi có mã nguồn. Cài thư viện trong `.venv` riêng của thư mục này:

```bash
pip install -r requirements.txt
```
