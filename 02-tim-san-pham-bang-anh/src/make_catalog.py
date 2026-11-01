"""Sinh danh mục sản phẩm mẫu và ảnh "khách chụp" để thử tìm kiếm.

- data/catalog/: 48 sản phẩm (6 loại x 8 mẫu màu/hoa văn) trên nền trắng, căn giữa,
  giống ảnh trên trang bán hàng.
- data/queries/: mỗi sản phẩm một ảnh như khách tự chụp: nền bàn gỗ, vải hoặc màu
  bất kỳ, đặt lệch, xoay nghiêng, ánh sáng ám vàng hoặc ám xanh.

Danh mục cố ý có nhiều cặp dễ nhầm: cùng loại cùng màu nhưng khác hoa văn, hoặc
cùng màu cùng hoa văn nhưng khác loại.

    python -m src.make_catalog
"""

import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageChops, ImageDraw, ImageFilter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOG_DIR = DATA_DIR / "catalog"
QUERIES_DIR = DATA_DIR / "queries"
CATALOG_CSV = DATA_DIR / "catalog.csv"
QUERIES_CSV = DATA_DIR / "queries.csv"

S = 256  # kích thước khung vẽ một sản phẩm
CATEGORIES = ["Áo thun", "Cốc", "Chai nước", "Túi xách", "Mũ lưỡi trai", "Giày"]
COLORS = {
    "Đỏ": (205, 45, 45), "Xanh dương": (45, 90, 200), "Xanh lá": (50, 150, 80),
    "Vàng": (235, 195, 50), "Đen": (40, 40, 45), "Trắng": (238, 238, 235),
}
PATTERNS = ["Trơn", "Sọc", "Chấm bi"]
SKUS_PER_CATEGORY = 8


def shape_mask(category: str) -> Image.Image:
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    if category == "Áo thun":
        d.polygon([(78, 40), (108, 30), (128, 48), (148, 30), (178, 40), (230, 85), (205, 115), (182, 98),
                   (182, 226), (74, 226), (74, 98), (51, 115), (26, 85)], fill=255)
    elif category == "Cốc":
        d.rounded_rectangle((60, 60, 170, 215), radius=18, fill=255)
        d.ellipse((150, 95, 215, 175), outline=255, width=16)  # quai
    elif category == "Chai nước":
        d.rounded_rectangle((90, 85, 166, 232), radius=24, fill=255)
        d.rectangle((110, 45, 146, 90), fill=255)  # cổ chai
        d.rounded_rectangle((104, 24, 152, 50), radius=6, fill=255)  # nắp
    elif category == "Túi xách":
        d.polygon([(52, 105), (204, 105), (224, 228), (32, 228)], fill=255)
        d.arc((84, 40, 172, 170), start=180, end=360, fill=255, width=12)  # quai
    elif category == "Mũ lưỡi trai":
        d.chord((52, 70, 204, 220), start=180, end=360, fill=255)  # đỉnh mũ
        d.ellipse((120, 128, 240, 168), fill=255)  # lưỡi trai
    elif category == "Giày":
        d.polygon([(28, 150), (70, 96), (118, 92), (140, 120), (200, 140), (232, 168), (232, 190), (28, 190)],
                  fill=255)
        d.rounded_rectangle((22, 186, 238, 212), radius=10, fill=255)  # đế
    return mask


def product(category: str, color: str, pattern: str) -> Image.Image:
    """Sản phẩm trên nền trong suốt (RGBA)."""
    base = COLORS[color]
    layer = Image.new("RGB", (S, S), base)
    d = ImageDraw.Draw(layer)
    accent = (250, 250, 250) if sum(base) < 450 else (60, 60, 60)
    if pattern == "Sọc":
        for y in range(0, S, 22):
            d.rectangle((0, y, S, y + 9), fill=accent)
    elif pattern == "Chấm bi":
        for row, y in enumerate(range(8, S, 26)):
            for x in range(8 + (row % 2) * 13, S, 26):
                d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=accent)
    # Sáng ở trên, tối dần xuống dưới cho có khối.
    shade = Image.linear_gradient("L").resize((S, S)).point(lambda v: int(255 - v * 0.35))
    layer = ImageChops.multiply(layer, Image.merge("RGB", [shade] * 3))

    mask = shape_mask(category)
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    layer.paste((55, 55, 55), mask=edge)
    layer.putalpha(mask)
    return layer


def with_shadow(canvas: Image.Image, item: Image.Image, xy: tuple[int, int], strength: float = 0.35) -> None:
    shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
    shadow.putalpha(item.getchannel("A").point(lambda a: int(a * strength)).filter(ImageFilter.GaussianBlur(6)))
    canvas.paste(shadow, (xy[0] + 6, xy[1] + 10), shadow)
    canvas.paste(item, xy, item)


def catalog_photo(item: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (320, 320), (250, 250, 250))
    with_shadow(canvas, item, (32, 32))
    return canvas


def background(rng: random.Random, size: tuple[int, int]) -> Image.Image:
    w, h = size
    kind = rng.choice(["go", "vai", "mau", "chuyen-mau"])
    if kind == "go":  # mặt bàn gỗ
        base = np.array([rng.randint(120, 170), rng.randint(80, 110), rng.randint(40, 70)], dtype=float)
        rows = base + 18 * np.sin(np.arange(h) / rng.uniform(3, 7))[:, None]
        img = np.repeat(rows[:, None, :], w, axis=1)
    elif kind == "vai":  # khăn trải bàn ca rô
        c1 = np.array([rng.randint(150, 230) for _ in range(3)], dtype=float)
        c2 = c1 * 0.8
        yy, xx = np.mgrid[0:h, 0:w]
        img = np.where((((yy // 16) + (xx // 16)) % 2 == 0)[..., None], c1, c2)
    elif kind == "mau":
        img = np.full((h, w, 3), [rng.randint(60, 230) for _ in range(3)], dtype=float)
    else:
        top = np.array([rng.randint(60, 230) for _ in range(3)], dtype=float)
        bottom = np.array([rng.randint(60, 230) for _ in range(3)], dtype=float)
        t = np.linspace(0, 1, h)[:, None, None]
        img = np.repeat(top * (1 - t) + bottom * t, w, axis=1)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def customer_photo(item: Image.Image, rng: random.Random) -> Image.Image:
    """Ảnh như khách tự chụp: khổ 4:3, nền lạ, đặt lệch, nghiêng, ánh sáng ám màu."""
    w, h = 400, 300
    canvas = background(rng, (w, h)).convert("RGBA")
    size = int(h * rng.uniform(0.5, 0.75))
    placed = item.resize((size, size), Image.LANCZOS).rotate(rng.uniform(-20, 20), Image.BICUBIC, expand=True)
    x, y = rng.randint(0, w - placed.width), rng.randint(0, max(0, h - placed.height))
    with_shadow(canvas, placed, (x, y), strength=0.45)

    pixels = np.asarray(canvas.convert("RGB"), dtype=float)
    white_balance = np.array([1 + rng.uniform(-0.12, 0.12) for _ in range(3)])  # ám vàng / ám xanh
    pixels = pixels * white_balance * rng.uniform(0.8, 1.15)
    pixels += np.random.default_rng(rng.randint(0, 10_000)).normal(0, 5, pixels.shape)
    photo = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    return photo.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.0)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(3)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)

    catalog, queries = [], []
    combos = [(color, pattern) for color in COLORS for pattern in PATTERNS]
    for category in CATEGORIES:
        for color, pattern in sorted(rng.sample(combos, SKUS_PER_CATEGORY)):
            sku = f"SP{len(catalog) + 1:02d}"
            item = product(category, color, pattern)
            catalog_photo(item).save(CATALOG_DIR / f"{sku}.png")
            customer_photo(item, rng).save(QUERIES_DIR / f"{sku}_khach.jpg", quality=80)
            name = f"{category} {color.lower()}" + ("" if pattern == "Trơn" else f" {pattern.lower()}")
            catalog.append({"sku": sku, "ten": name, "loai": category, "mau": color, "hoa_van": pattern,
                            "file": f"catalog/{sku}.png"})
            queries.append({"file": f"queries/{sku}_khach.jpg", "sku": sku})

    pd.DataFrame(catalog).to_csv(CATALOG_CSV, index=False)
    pd.DataFrame(queries).to_csv(QUERIES_CSV, index=False)
    print(f"Đã sinh {len(catalog)} ảnh danh mục và {len(queries)} ảnh khách chụp vào {DATA_DIR}")


if __name__ == "__main__":
    main()
