# 03 · Phân loại ticket

Gợi ý đúng nhóm tiếp nhận.

**Trạng thái:** 🚧 Chưa làm

## Bài toán

Ticket hỗ trợ đến từ nhiều kênh và thường bị chuyển nhầm nhóm. Dự án đọc nội dung ticket mới và gợi ý nhóm tiếp nhận phù hợp.

## Luồng xử lý

| Ticket mới | Nhóm tiếp nhận |
|------------|----------------|
| Không đăng nhập | Tài khoản |
| Lỗi thanh toán | Thanh toán |
| Ứng dụng treo | Kỹ thuật |

Khi mô hình **không đủ tin cậy**, ticket không bị đoán bừa mà chuyển sang trạng thái **Cần kiểm tra** để người xử lý quyết định.

## Công nghệ

scikit-learn (mô hình phân loại văn bản) · FastAPI (API nhận ticket, trả nhóm và độ tin cậy)

## Dữ liệu mẫu

Đặt trong `data/`. Chỉ dùng ticket tự tạo, không dùng nội dung ticket thật.

## Cách chạy

Sẽ bổ sung khi có mã nguồn. Cài thư viện trong `.venv` riêng của thư mục này:

```bash
pip install -r requirements.txt
```
