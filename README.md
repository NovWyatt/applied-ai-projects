# applied-ai-projects

Bộ 5 dự án **AI ứng dụng** giải các bài toán nghiệp vụ quen thuộc: đọc hóa đơn, tìm sản phẩm bằng ảnh, phân loại ticket, tóm tắt cuộc họp và gợi ý bài viết.

> A collection of five small, self-contained applied-AI projects. Each one has its own dependencies and can be run on its own.

## Các dự án

| # | Dự án | Bài toán | Công nghệ chính | Trạng thái |
|---|-------|----------|-----------------|------------|
| 1 | [Đọc hóa đơn](01-doc-hoa-don/) | Chuyển ảnh hóa đơn thành bảng có thể sửa, xuất CSV | Python, PaddleOCR, Pandas | 🚧 Chưa làm |
| 2 | [Tìm sản phẩm bằng ảnh](02-tim-san-pham-bang-anh/) | Tìm hình tương tự trong danh mục | PyTorch, Hugging Face, Qdrant | 🚧 Chưa làm |
| 3 | [Phân loại ticket](03-phan-loai-ticket/) | Gợi ý đúng nhóm tiếp nhận cho ticket mới | scikit-learn, FastAPI | ✅ Xong |
| 4 | [Tóm tắt cuộc họp](04-tom-tat-cuoc-hop/) | Từ bản ghi âm tới danh sách đầu việc | Python, OpenAI | 🚧 Chưa làm |
| 5 | [Gợi ý bài viết](05-goi-y-bai-viet/) | Đề xuất nội dung từ lịch sử tương tác | Python, Pandas, scikit-learn | 🚧 Chưa làm |

## Cách chạy

Mỗi dự án có môi trường Python riêng, vì PaddlePaddle và PyTorch dễ xung đột phiên bản khi cài chung.

```bash
cd 03-phan-loai-ticket
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Cách chạy cụ thể nằm trong README của từng thư mục.

## Nguyên tắc chung

- **Dữ liệu mẫu là dữ liệu tự tạo.** Không có hóa đơn, ticket hay bản ghi âm thật trong repo.
- **Không chắc thì để người kiểm tra.** AI chỉ gợi ý; khi độ tin cậy thấp hoặc thiếu thông tin thì chuyển cho người xem hoặc để trống, không đoán bừa.
- **Không commit khóa API.** Sao chép `.env.example` thành `.env` rồi điền khóa của bạn.

## Ghi nguồn

Ý tưởng 5 bài toán lấy cảm hứng từ series infographic của Quang Huy (@quanghuyai). Mã nguồn và dữ liệu mẫu trong repo này được viết riêng.

## Giấy phép

[MIT](LICENSE)
