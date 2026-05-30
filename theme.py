"""
PixUp - Theme system
ธีมสีแบบเทาเข้ม (Lightroom-style) + เลือกสี accent ได้
build_palette(theme_name, accent_hex) -> dict สีครบสำหรับใช้ทั้งแอป
"""

# ฐานสีของแต่ละธีม (โทนเทาเข้ม) — ไม่รวม accent (accent เลือกแยก)
THEMES = {
    "graphite": {  # เทาเข้มกลาง (ค่าเริ่มต้น)
        "bg": "#1e1e22", "bg_alt": "#252529", "panel": "#28282d",
        "card": "#2d2d33", "card_hi": "#36363d", "border": "#3a3a42",
        "text": "#f0f1f3", "text_dim": "#a8acb4", "text_mute": "#6b6f78",
        "input_bg": "#171719",
    },
    "midnight": {  # ดำอมน้ำเงิน คลีน/พรีเมียม (ค่าเริ่มต้นใหม่)
        "bg": "#0d1017", "bg_alt": "#121620", "panel": "#141925",
        "card": "#1a2030", "card_hi": "#222a3d", "border": "#283143",
        "text": "#f2f5fa", "text_dim": "#9ba6ba", "text_mute": "#5e6a80",
        "input_bg": "#0a0d14",
    },
    "slate": {  # เทาอ่อนกว่าเล็กน้อย
        "bg": "#262629", "bg_alt": "#2e2e32", "panel": "#323237",
        "card": "#37373c", "card_hi": "#414148", "border": "#46464e",
        "text": "#f4f4f6", "text_dim": "#b2b5bc", "text_mute": "#787c84",
        "input_bg": "#1d1d20",
    },
}

# สี accent สำเร็จรูป (ชื่อ -> hex)
ACCENT_PRESETS = {
    "teal": "#00c2a8",
    "blue": "#4a90e2",
    "purple": "#a779ff",
    "amber": "#f5a623",
    "rose": "#ff5d73",
    "green": "#3ecf8e",
}

DEFAULT_THEME = "midnight"
DEFAULT_ACCENT = "#00c2a8"

# สีสถานะ (คงที่ ไม่ขึ้นกับธีม)
_STATUS = {
    "success": "#3ecf8e", "error": "#ff5d6c", "warning": "#f5b942",
    "info": "#e6e8ec",
}


def _clamp(v):
    return max(0, min(255, int(v)))


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (0, 194, 168)


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(_clamp(c) for c in rgb)


def lighten(hex_color, amount=0.18):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount))


def darken(hex_color, amount=0.30):
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((r * (1 - amount), g * (1 - amount), b * (1 - amount)))


def contrast_text(hex_color):
    """คืนสีตัวอักษร (ดำ/ขาว) ที่อ่านง่ายบนพื้น hex_color"""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0c0c0e" if luminance > 0.6 else "#ffffff"


def build_palette(theme_name=DEFAULT_THEME, accent_hex=DEFAULT_ACCENT):
    """รวมฐานธีม + accent → dict สีครบสำหรับทั้งแอป"""
    base = dict(THEMES.get(theme_name, THEMES[DEFAULT_THEME]))
    accent = accent_hex or DEFAULT_ACCENT
    palette = dict(base)
    palette.update(_STATUS)
    palette["accent"] = accent
    palette["accent_hi"] = lighten(accent, 0.20)
    palette["accent_hover"] = lighten(accent, 0.12)
    palette["accent_dim"] = darken(accent, 0.45)
    palette["on_accent"] = contrast_text(accent)
    # ปุ่มทั่วไป
    palette["btn_default"] = base["card_hi"]
    palette["btn_hover"] = lighten(base["card_hi"], 0.10)
    # ชื่อย่อสำหรับ highlight (ใช้ accent โทนน้ำเงินคงที่ในบาง log)
    palette["highlight"] = ACCENT_PRESETS["blue"]
    palette["purple"] = ACCENT_PRESETS["purple"]
    palette["orange"] = ACCENT_PRESETS["amber"]
    return palette
