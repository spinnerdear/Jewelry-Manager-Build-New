"""
PixUp - Config & persistence (ไม่พึ่ง Tkinter)
รวมการโหลด/บันทึก settings + manifest (import memory) ไว้ที่เดียว
"""
import os
import json

CONFIG_VERSION = 3

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pixup")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config_v2_1.json")
HISTORY_LOG = os.path.join(CONFIG_DIR, "history_log.txt")
MANIFEST_FILE = os.path.join(CONFIG_DIR, "imported_manifest.json")

DEFAULT_TYPES = {'R': 'Ring', 'N': 'Necklace', 'E': 'Earring',
                 'P': 'Pendant', 'B': 'Bracelet', 'S': 'Sets'}

DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "photo1": "", "photo2": "", "archive": "",
    "camera_source": "", "chatgpt_url": "", "chrome_profile_dir": "",
    "theme": "graphite", "accent": "#00c2a8",
    "types": DEFAULT_TYPES,
    "sound_enabled": True,
}


def ensure_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def load_settings():
    """คืน dict การตั้งค่า (เติมค่า default ให้ครบ)"""
    ensure_dir()
    data = dict(DEFAULTS)
    data["types"] = dict(DEFAULT_TYPES)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                data[k] = v
            if not data.get("types"):
                data["types"] = dict(DEFAULT_TYPES)
        except Exception as e:
            print(f"Failed to load settings: {e}")
    data["config_version"] = CONFIG_VERSION
    return data


def save_settings(data):
    ensure_dir()
    out = dict(data)
    out["config_version"] = CONFIG_VERSION
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=4)


def load_manifest():
    """set ของ signature ไฟล์ที่เคย import"""
    try:
        if os.path.exists(MANIFEST_FILE):
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        print(f"Failed to load manifest: {e}")
    return set()


def save_manifest(manifest):
    ensure_dir()
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(manifest), f, ensure_ascii=False)


def reset_manifest():
    if os.path.exists(MANIFEST_FILE):
        os.remove(MANIFEST_FILE)


def append_history(line):
    try:
        ensure_dir()
        with open(HISTORY_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"Failed to write history log: {e}")
