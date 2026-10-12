"""Rebuild the README GIF from the project's public preview images."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SIZE = (960, 540)
NAVY = (9, 17, 31)
GOLD = (231, 190, 120)
IVORY = (245, 241, 231)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def cover(image: Image.Image, title: str, subtitle: str) -> Image.Image:
    canvas = Image.new("RGB", SIZE, NAVY)
    ratio = max(SIZE[0] / image.width, SIZE[1] / image.height)
    image = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (image.width - SIZE[0]) // 2
    top = (image.height - SIZE[1]) // 2
    canvas.paste(image.crop((left, top, left + SIZE[0], top + SIZE[1])))
    shade = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shade)
    draw.rectangle((0, 0, 620, SIZE[1]), fill=(6, 13, 26, 190))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shade)
    draw = ImageDraw.Draw(canvas)
    draw.text((65, 125), "ZODERISE / HORIZON", fill=GOLD, font=font(24, bold=True))
    draw.multiline_text((65, 205), title, fill=IVORY, font=font(51, bold=True), spacing=9)
    draw.multiline_text((67, 379), subtitle, fill=(198, 212, 225), font=font(21), spacing=6)
    draw.rounded_rectangle((65, 474, 248, 480), radius=3, fill=GOLD)
    return canvas.convert("RGB")


def screenshot_frame(image: Image.Image, label: str) -> Image.Image:
    canvas = Image.new("RGB", SIZE, NAVY)
    image.thumbnail((870, 438), Image.Resampling.LANCZOS)
    x = (SIZE[0] - image.width) // 2
    y = 50 + (438 - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x - 2, y - 2, x + image.width + 1, y + image.height + 1), radius=5, outline=GOLD, width=2)
    draw.text((45, 501), label, fill=IVORY, font=font(21, bold=True))
    return canvas


def mobile_frame(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", SIZE, NAVY)
    image.thumbnail((244, 480), Image.Resampling.LANCZOS)
    x, y = 93, (SIZE[1] - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x - 3, y - 3, x + image.width + 2, y + image.height + 2), radius=15, outline=GOLD, width=3)
    draw.text((425, 165), "One host laptop.", fill=IVORY, font=font(39, bold=True))
    draw.text((425, 226), "Many ways to connect.", fill=IVORY, font=font(35, bold=True))
    draw.multiline_text((427, 314), "Open in a browser or the Windows app.\nEach person signs in to an approved account.", fill=(198, 212, 225), font=font(22), spacing=12)
    draw.rounded_rectangle((426, 430, 604, 436), radius=3, fill=GOLD)
    return canvas


def main() -> None:
    hero = Image.open(ROOT / "assets/horizon-hero.png").convert("RGB")
    workspace = Image.open(ROOT / "assets/customization-preview.png").convert("RGB")
    phone = Image.open(ROOT / "assets/mobile-preview.png").convert("RGB")
    knowledge = Image.open(ROOT / "assets/knowledge-studio.webp").convert("RGB")
    scenes = [
        cover(hero, "A private AI space\nfor real work.", "Learn, draft, research, and create.\nRun locally or share from one trusted host."),
        screenshot_frame(workspace, "A workspace shaped around your work"),
        mobile_frame(phone),
        cover(knowledge, "Research with\nlocal evidence.", "Search uploaded documents and inspect\nthe retrieved passages before you rely on an answer."),
    ]
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index, scene in enumerate(scenes):
        frames.append(scene)
        durations.append(1100)
        if index < len(scenes) - 1:
            for step in range(1, 6):
                frames.append(Image.blend(scene, scenes[index + 1], step / 6))
                durations.append(65)
    frames[0].save(HERE / "zoderise-demo.gif", save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=2)
    print(f"Created {HERE / 'zoderise-demo.gif'}")


if __name__ == "__main__":
    main()
