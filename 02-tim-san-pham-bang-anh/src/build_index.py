"""Tạo chỉ mục Qdrant cho danh mục, với vector của mọi mô hình.

Chạy từ thư mục 02-tim-san-pham-bang-anh:

    python -m src.build_index

Lần đầu sẽ tải DINOv2-small (~90 MB) và CLIP ViT-B/32 (~600 MB) vào models/.
"""

import sys
import time

from src.data import load_catalog, open_image
from src.embedders import MODELS, get_embedder
from src.index import INDEX_DIR, CatalogIndex


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    catalog = load_catalog()
    images = [open_image(path) for path in catalog["file"]]

    vectors = {}
    for name in MODELS:
        embedder = get_embedder(name)
        start = time.perf_counter()
        vectors[name] = embedder.embed(images)
        print(f"{embedder.label}: {vectors[name].shape[1]} chiều, "
              f"{(time.perf_counter() - start) / len(images) * 1000:.0f} ms/ảnh")

    index = CatalogIndex()
    index.build(vectors, catalog.to_dict("records"))
    index.close()
    print(f"Đã ghi {len(catalog)} sản phẩm vào {INDEX_DIR}")


if __name__ == "__main__":
    main()
