"""Giao diện tìm sản phẩm bằng ảnh.

Chạy từ thư mục 02-tim-san-pham-bang-anh (sau `python -m src.build_index`):

    streamlit run app.py

Qdrant chạy theo thư mục chỉ cho một tiến trình mở cùng lúc: tắt giao diện trước
khi chạy build_index hay evaluate.
"""

import streamlit as st
from PIL import Image

from src.data import load_queries, open_image
from src.index import CatalogIndex
from src.make_catalog import CATEGORIES, DATA_DIR
from src.search import ProductSearch

st.set_page_config(page_title="Tìm sản phẩm bằng ảnh", page_icon="🔎", layout="wide")


@st.cache_resource(show_spinner="Đang nạp DINOv2 và CLIP...")
def get_searcher() -> ProductSearch:
    return ProductSearch(CatalogIndex())


st.title("🔎 Tìm sản phẩm bằng ảnh")
st.caption("DINOv2 lấy 10 sản phẩm có dáng giống nhất trong danh mục (Qdrant), "
           "rồi chấm lại kết hợp CLIP để phân biệt màu.")

queries = load_queries().set_index("file")
left, right = st.columns([1, 2], gap="large")
with left:
    upload = st.file_uploader("Ảnh sản phẩm cần tìm", type=["jpg", "jpeg", "png", "webp"])
    sample = st.selectbox("...hoặc chọn một ảnh khách chụp mẫu", queries.index,
                          format_func=lambda f: queries.at[f, "ten"], disabled=upload is not None)
    category = st.selectbox("Chỉ tìm trong loại", ["Tất cả", *CATEGORIES])
    image = Image.open(upload).convert("RGB") if upload else open_image(sample)
    st.image(image, caption="Ảnh cần tìm", width="stretch")

answer = None if upload else queries.at[sample, "sku"]
with right:
    results = get_searcher().search(image, k=5, category=None if category == "Tất cả" else category)
    st.subheader("Sản phẩm giống nhất")
    for column, (rank, (candidate, score)) in zip(st.columns(5), enumerate(results, 1)):
        column.image(str(DATA_DIR / candidate.payload["file"]), width="stretch")
        mark = " ✅" if candidate.sku == answer else ""
        column.markdown(f"**{rank}. {candidate.payload['ten']}**{mark}")
        column.caption(f"{candidate.sku} · điểm {score:.3f}")
        column.caption(f"DINOv2 {candidate.dino:.2f} · CLIP {candidate.clip:.2f}")
    if answer:
        st.caption("✅ là sản phẩm đúng của ảnh mẫu.")
