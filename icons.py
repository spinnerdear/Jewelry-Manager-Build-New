"""
PixUp - Icons (วาดไอคอนเส้นมินิมอลด้วย PIL ตอนรัน — ไม่ต้องมีไฟล์รูป, ปรับสีตามธีมได้)
get(name, color, px) -> PIL.Image (RGBA โปร่งใส) ขนาด px*px
วาดบนผืน 96px แล้วย่อ → ขอบเนียน. ใช้ผ่าน CTkImage ในฝั่ง UI
"""
from PIL import Image, ImageDraw

_S = 96          # ขนาดวาดจริง (ย่อทีหลังให้คม)
_W = 8           # ความหนาเส้น


def _new():
    img = Image.new("RGBA", (_S, _S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _line(d, pts, c, w=_W):
    d.line(pts, fill=c, width=w, joint="curve")
    # ปลายมน
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)


def _draw(name, c):
    img, d = _new()
    if name == "import":
        _line(d, [(48, 16), (48, 54)], c)
        _line(d, [(33, 40), (48, 56), (63, 40)], c)
        _line(d, [(22, 60), (22, 78), (74, 78), (74, 60)], c)
    elif name == "merge":
        d.rounded_rectangle([20, 24, 56, 60], radius=9, outline=c, width=_W)
        d.rounded_rectangle([40, 36, 76, 72], radius=9, outline=c, width=_W)
    elif name == "crop":
        _line(d, [(34, 12), (34, 70)], c)
        _line(d, [(26, 62), (84, 62)], c)
        _line(d, [(62, 26), (62, 84)], c)
        _line(d, [(12, 34), (70, 34)], c)
    elif name == "ai":
        d.polygon([(48, 14), (55, 41), (82, 48), (55, 55), (48, 82),
                   (41, 55), (14, 48), (41, 41)], fill=c)
        d.polygon([(76, 18), (79, 27), (88, 30), (79, 33), (76, 42),
                   (73, 33), (64, 30), (73, 27)], fill=c)
    elif name == "rename":
        d.polygon([(72, 28), (40, 28), (16, 52), (40, 76), (72, 76)],
                  outline=c, width=_W)
        d.ellipse([30, 47, 40, 57], fill=c)
    elif name == "collect":
        d.ellipse([22, 16, 74, 34], outline=c, width=_W)
        _line(d, [(22, 25), (22, 71)], c)
        _line(d, [(74, 25), (74, 71)], c)
        d.arc([22, 38, 74, 56], 5, 175, fill=c, width=_W)
        d.arc([22, 62, 74, 80], 5, 175, fill=c, width=_W)
    elif name == "archive":
        d.rounded_rectangle([16, 26, 80, 46], radius=6, outline=c, width=_W)
        _line(d, [(23, 46), (23, 78), (73, 78), (73, 46)], c)
        _line(d, [(40, 60), (56, 60)], c)
    elif name == "folder":
        _line(d, [(18, 36), (40, 36), (48, 44), (78, 44)], c)
        _line(d, [(18, 36), (18, 74), (78, 74), (78, 44)], c)
    elif name == "camera":
        d.rounded_rectangle([14, 34, 82, 78], radius=10, outline=c, width=_W)
        _line(d, [(34, 34), (40, 24), (56, 24), (62, 34)], c)
        d.ellipse([37, 46, 59, 68], outline=c, width=_W)
    elif name == "settings":
        _line(d, [(18, 36), (74, 36)], c)
        d.ellipse([34, 28, 50, 44], fill=c)
        _line(d, [(18, 62), (74, 62)], c)
        d.ellipse([52, 54, 68, 70], fill=c)
    elif name == "photo":
        d.rounded_rectangle([14, 22, 82, 74], radius=10, outline=c, width=_W)
        d.ellipse([26, 32, 40, 46], outline=c, width=_W)
        _line(d, [(20, 66), (40, 48), (52, 58), (66, 42), (82, 64)], c)
    elif name == "reset":
        d.arc([20, 20, 76, 76], 60, 340, fill=c, width=_W)
        d.polygon([(70, 16), (78, 30), (62, 30)], fill=c)
    elif name == "grid":
        for x, y in [(20, 20), (52, 20), (20, 52), (52, 52)]:
            d.rounded_rectangle([x, y, x + 24, y + 24], radius=5, outline=c, width=_W)
    else:
        d.ellipse([24, 24, 72, 72], outline=c, width=_W)
    return img


def get(name, color, px=18):
    """คืน PIL.Image ของไอคอน (วาดสด ย่อให้คม)"""
    img = _draw(name, color)
    return img.resize((px, px), Image.Resampling.LANCZOS)
