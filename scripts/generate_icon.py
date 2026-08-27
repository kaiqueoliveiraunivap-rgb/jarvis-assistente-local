from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def create_icon(size: int = 512) -> Image.Image:
    image = Image.new("RGBA", (size, size), (4, 13, 23, 255))
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    painter = ImageDraw.Draw(glow)
    center = size // 2
    for width, alpha in ((72, 40), (42, 90), (18, 220)):
        inset = size * 0.18
        painter.ellipse((inset, inset, size - inset, size - inset), outline=(72, 229, 255, alpha), width=width)
    glow = glow.filter(ImageFilter.GaussianBlur(size // 60))
    image.alpha_composite(glow)
    painter = ImageDraw.Draw(image)
    cyan = (72, 229, 255, 255)
    dark = (7, 22, 34, 255)
    painter.ellipse((94, 94, size - 94, size - 94), fill=dark, outline=cyan, width=14)
    painter.ellipse((164, 164, size - 164, size - 164), fill=(9, 42, 59, 255), outline=(185, 249, 255, 255), width=8)
    painter.polygon(((center, 202), (304, 310), (268, 310), (247, 265), (226, 310), (190, 310)), fill=cyan)
    for angle_box in ((54, 230, 124, 282), (388, 230, 458, 282), (230, 54, 282, 124), (230, 388, 282, 458)):
        painter.rounded_rectangle(angle_box, radius=12, fill=(23, 100, 125, 255))
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image = create_icon()
    image.save(ASSETS / "jarvis.png", "PNG")
    image.save(
        ASSETS / "jarvis.ico",
        "ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
