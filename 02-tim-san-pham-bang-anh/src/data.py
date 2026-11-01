"""Đọc danh mục và ảnh khách chụp."""

import pandas as pd
from PIL import Image

from src.make_catalog import CATALOG_CSV, DATA_DIR, QUERIES_CSV


def load_catalog() -> pd.DataFrame:
    return pd.read_csv(CATALOG_CSV)


def load_queries() -> pd.DataFrame:
    """Ảnh khách chụp kèm thông tin đúng của sản phẩm trong ảnh."""
    return pd.read_csv(QUERIES_CSV).merge(load_catalog().drop(columns="file"), on="sku")


def open_image(relative_path: str) -> Image.Image:
    with Image.open(DATA_DIR / relative_path) as image:
        return image.convert("RGB")
