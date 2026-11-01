# 02 · Tìm sản phẩm bằng ảnh

Tìm hình tương tự trong danh mục.

**Trạng thái:** 🚧 Chưa làm

## Bài toán

Khách thường không biết tên sản phẩm nhưng có sẵn một tấm ảnh. Dự án nhận ảnh cần tìm và trả về các sản phẩm giống nhất trong danh mục.

## Luồng xử lý

1. Tạo **embedding** cho từng ảnh trong danh mục và lưu vào cơ sở dữ liệu vector (Qdrant).
2. Nhận **ảnh cần tìm**, tạo embedding bằng cùng một mô hình.
3. **Tìm kiếm** các vector gần nhất trong danh mục.
4. Trả về **kết quả sản phẩm tương tự**.

## Công nghệ

PyTorch · Hugging Face · Qdrant

`qdrant-client` có chế độ chạy cục bộ (in-memory hoặc lưu vào thư mục), nên lúc đầu chưa cần dựng server riêng.

## Dữ liệu mẫu

Đặt trong `data/`. Dùng ảnh có giấy phép cho phép chia sẻ lại, hoặc ảnh tự chụp.

## Cách chạy

Sẽ bổ sung khi có mã nguồn. Cài thư viện trong `.venv` riêng của thư mục này:

```bash
pip install -r requirements.txt
```
