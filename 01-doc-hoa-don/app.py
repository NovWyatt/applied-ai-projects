"""Giao diện kiểm tra: đọc ảnh hóa đơn, sửa ô sai, tải CSV.

Chạy từ thư mục 01-doc-hoa-don:

    streamlit run app.py
"""

import io

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from src.fields import extract_fields
from src.make_receipts import RECEIPTS_DIR
from src.ocr import OcrLine, read_lines

st.set_page_config(page_title="Đọc hóa đơn", page_icon="🧾", layout="wide")


@st.cache_resource(show_spinner="Đang nạp mô hình OCR...")
def warm_up() -> None:
    from src.ocr import get_engine
    get_engine()


@st.cache_data(show_spinner=False)
def ocr_image(image_bytes: bytes) -> list[OcrLine]:
    rgb = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    return read_lines(np.ascontiguousarray(rgb[:, :, ::-1]))  # PaddleOCR nhận ảnh BGR như OpenCV


st.title("🧾 Đọc hóa đơn")
st.caption("Ảnh hóa đơn → OCR → bảng có thể sửa → CSV. Ô nào máy không chắc được ghi ở cột "
           "**Cần kiểm tra**; máy để trống chứ không đoán khi không tìm thấy.")

uploads = st.file_uploader("Chọn ảnh hóa đơn", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
use_samples = st.toggle("Dùng 8 hóa đơn mẫu", value=not uploads)

files = [(upload.name, upload.getvalue()) for upload in uploads or []]
if use_samples:
    files += [(path.name, path.read_bytes()) for path in sorted(RECEIPTS_DIR.glob("*.jpg"))]
if not files:
    st.info("Chọn ảnh hóa đơn hoặc bật hóa đơn mẫu để bắt đầu.")
    st.stop()

warm_up()
progress = st.progress(0.0, text="Đang đọc hóa đơn...")
results = []
for i, (name, data) in enumerate(files):
    lines = ocr_image(data)
    results.append((name, data, lines, extract_fields(lines)))
    progress.progress((i + 1) / len(files), text=f"Đã đọc {i + 1}/{len(files)} hóa đơn")
progress.empty()

table = pd.DataFrame([{
    "Tệp": name,
    "Ngày": pd.to_datetime(fields.ngay).date() if fields.ngay else None,
    "Đơn vị": fields.don_vi,
    "Tổng tiền": fields.tong_tien,
    "Cần kiểm tra": ", ".join(fields.can_kiem_tra),
    "Đã xem": False,
} for name, _, _, fields in results]).astype({"Tổng tiền": "Int64"})

flagged = int((table["Cần kiểm tra"] != "").sum())
left, right = st.columns(2)
left.metric("Hóa đơn", len(table))
right.metric("Có ô cần kiểm tra", flagged)

st.subheader("1. Kiểm tra và sửa")
edited = st.data_editor(
    table,
    hide_index=True,
    width="stretch",
    disabled=["Tệp", "Cần kiểm tra"],
    column_config={
        "Ngày": st.column_config.DateColumn(format="DD/MM/YYYY"),
        "Tổng tiền": st.column_config.NumberColumn(format="localized", min_value=0, step=1),
        "Cần kiểm tra": st.column_config.TextColumn(help="Ô máy không chắc, nên so với ảnh"),
        "Đã xem": st.column_config.CheckboxColumn(help="Đánh dấu khi đã so với ảnh"),
    },
)

st.download_button(
    "⬇️ Tải CSV",
    edited.to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig để Excel mở đúng tiếng Việt
    file_name="hoa_don.csv",
    mime="text/csv",
    type="primary",
)

st.subheader("2. So với ảnh gốc")
for name, data, lines, fields in results:
    mark = "⚠️ " if fields.can_kiem_tra else "✅ "
    with st.expander(mark + name, expanded=bool(fields.can_kiem_tra)):
        image_col, text_col = st.columns([3, 2])
        image_col.image(data, width="stretch")
        text_col.markdown("**Chữ máy đọc được** (độ tin cậy)")
        text_col.code("\n".join(f"{line.score:.2f}  {line.text}" for line in lines), language=None)
