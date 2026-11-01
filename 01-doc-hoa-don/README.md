# 01 · Đọc hóa đơn

Chuyển ảnh hóa đơn thành bảng có thể sửa.

**Trạng thái:** 🚧 Chưa làm

## Bài toán

Nhập tay thông tin từ hóa đơn giấy tốn thời gian và dễ sai. Dự án đọc ảnh hóa đơn, lấy ra các trường chính và xuất thành bảng để người dùng kiểm tra rồi lưu.

## Luồng xử lý

1. Nhận ảnh hóa đơn.
2. OCR để lấy văn bản (PaddleOCR).
3. Tách các trường: **Ngày**, **Đơn vị** (tên cửa hàng), **Tổng tiền**.
4. Gom nhiều hóa đơn vào một bảng (Pandas).
5. **Kiểm tra**: người dùng xem và sửa các ô OCR đọc sai.
6. **Xuất CSV**.

## Công nghệ

Python · PaddleOCR · Pandas

## Dữ liệu mẫu

Đặt trong `data/`. Chỉ dùng hóa đơn tự tạo, không dùng hóa đơn thật.

## Cách chạy

Sẽ bổ sung khi có mã nguồn. Cài thư viện trong `.venv` riêng của thư mục này:

```bash
pip install -r requirements.txt
```
