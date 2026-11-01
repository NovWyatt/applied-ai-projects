# 04 · Tóm tắt cuộc họp

Từ bản ghi âm tới danh sách đầu việc.

**Trạng thái:** 🚧 Chưa làm

## Bài toán

Sau cuộc họp, việc ghi lại ai làm gì, khi nào thường bị quên hoặc ghi thiếu. Dự án biến bản ghi âm thành văn bản có mốc thời gian, rồi rút ra danh sách đầu việc.

## Luồng xử lý

1. Nhận **bản ghi âm**.
2. **Chuyển thành văn bản**, kèm mốc thời gian, ví dụ `[02:15] Cần hoàn thiện giao diện ...`.
3. Dùng mô hình ngôn ngữ để rút ra **danh sách đầu việc**: Việc · Phụ trách · Hạn.

Quy tắc: **không có thông tin thì để trống.** Không tự suy ra người phụ trách hay hạn chót khi cuộc họp không nhắc tới.

## Công nghệ

Python · OpenAI API

Cần khóa API và có phí theo lượt gọi. Sao chép `.env.example` thành `.env` rồi điền khóa của bạn. Không commit file `.env`.

## Dữ liệu mẫu

Đặt trong `data/`. Chỉ dùng bản ghi âm tự thu hoặc kịch bản tự viết, không dùng cuộc họp thật.

## Cách chạy

Sẽ bổ sung khi có mã nguồn. Cài thư viện trong `.venv` riêng của thư mục này:

```bash
pip install -r requirements.txt
```
