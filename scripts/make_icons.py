#!/usr/bin/env python3
"""홈 화면 아이콘 생성 (Pillow 필요: pip install pillow)

  python scripts/make_icons.py  →  icons/*.png, icons/icon.svg
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icons"
OUT.mkdir(exist_ok=True)

BG_TOP, BG_BOT = (16, 62, 74), (10, 38, 48)     # 짙은 청록
BAR = (234, 242, 238)                            # 건물 막대
BAR_DIM = (160, 196, 192)
GOLD = (232, 180, 76)                            # 상승선


def draw(size: int, safe: float) -> Image.Image:
    """safe: 그림이 들어갈 중앙 영역 비율 (maskable 아이콘은 0.62)."""
    S = size * 4                                  # 4배로 그린 뒤 축소(안티앨리어싱)
    img = Image.new("RGB", (S, S))
    px = ImageDraw.Draw(img)
    for y in range(S):                            # 세로 그라데이션 배경
        t = y / S
        px.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))
    d = ImageDraw.Draw(img)
    box = S * safe
    ox = oy = (S - box) / 2
    u = box / 10                                  # 격자 단위
    base = oy + u * 8.6
    # 세 동의 건물(막대) ― 높이가 차례로 높아짐
    bars = [(1.2, 5.2, BAR_DIM), (3.9, 3.6, BAR), (6.6, 2.0, BAR)]
    for x, top, col in bars:
        d.rounded_rectangle([ox + u * x, oy + u * top, ox + u * (x + 2.2), base], radius=u * 0.35, fill=col)
        # 창문
        for wy in range(int(top * 2) + 2, 16, 2):
            y0 = oy + u * wy / 2
            if y0 + u * 0.5 > base - u * 0.3:
                break
            d.rectangle([ox + u * (x + 0.55), y0, ox + u * (x + 1.65), y0 + u * 0.32],
                        fill=BG_BOT if col == BAR else (120, 160, 158))
    d.rounded_rectangle([ox + u * 0.6, base, ox + u * 9.4, base + u * 0.45], radius=u * 0.2, fill=BAR)
    # 상승 추세선과 끝점
    pts = [(ox + u * 0.9, oy + u * 5.0), (ox + u * 3.6, oy + u * 3.3),
           (ox + u * 5.8, oy + u * 3.9), (ox + u * 8.7, oy + u * 0.9)]
    d.line(pts, fill=GOLD, width=int(u * 0.55), joint="curve")
    for p in pts[:-1]:
        r = u * 0.28
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=GOLD)
    r = u * 0.62
    d.ellipse([pts[-1][0] - r, pts[-1][1] - r, pts[-1][0] + r, pts[-1][1] + r], fill=GOLD)
    return img.resize((size, size), Image.LANCZOS)


def rounded(img: Image.Image, radius_ratio=0.22) -> Image.Image:
    s = img.size[0]
    mask = Image.new("L", (s * 4, s * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s * 4, s * 4], radius=s * 4 * radius_ratio, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask.resize((s, s), Image.LANCZOS))
    return out


draw(512, 0.80).save(OUT / "icon-512.png")
draw(192, 0.80).save(OUT / "icon-192.png")
draw(512, 0.62).save(OUT / "icon-maskable-512.png")       # 안드로이드 모양 마스크용
draw(180, 0.78).save(OUT / "apple-touch-icon.png")         # iOS (모서리는 iOS가 둥글게 처리)
rounded(draw(64, 0.86)).resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png")
rounded(draw(1024, 0.80)).save(OUT / "icon-preview.png")
print("icons/ 생성 완료")
