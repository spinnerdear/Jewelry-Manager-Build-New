import sys
import os

# --- CRITICAL FIX: Standardize Output for Windows No-Console Mode ---
class NullWriter:
    def write(self, s): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

import re
import shutil
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# ChatGPT retouch module (in-process; Playwright imported lazily inside the module).
# Top-level import so PyInstaller bundles it into the frozen exe.
try:
    import chatgpt_retouch
    HAS_CHATGPT = True
except Exception:
    HAS_CHATGPT = False


class PixUpApp:
    def __init__(self, root):
        self.root = root
        self.version = "2.2 Beta 3"
        self.root.title(f"PixUp v{self.version}")
        self.root.geometry("1240x960")

        # Memory for AI retouch tasks: folder_path -> {"files": [...], "is_earring": bool}
        self.ai_tasks = {}

        # Centralized Error Codes
        self.error_codes = {
            "E001": "เส้นทางที่ระบุไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในโฟลเดอร์ต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงไฟล์ (Permission Denied)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อ (Drive Offline)",
            "E007": "เกิดปัญหาขณะก๊อปปี้ไฟล์",
            "E999": "เกิดข้อผิดพลาดภายในระบบ",
        }

        # Config & memory files
        self.config_dir = os.path.join(os.path.expanduser("~"), ".pixup")
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "config_v2_1.json")
        self.history_log = os.path.join(self.config_dir, "history_log.txt")
        self.manifest_file = os.path.join(self.config_dir, "imported_manifest.json")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()
        self.camera_source = tk.StringVar()
        self.chatgpt_url = tk.StringVar()
        self.chrome_profile_dir = tk.StringVar()
        self.type_mapping = {}

        # Running state per phase (drives stepper spinner)
        self.is_running = {
            "phase0": False, "phase1": False, "phase1_5": False,
            "phase1_6": False, "phase1_7": False, "phase2": False,
            "phase3": False, "phase4": False,
        }
        self.anim_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.anim_idx = 0

        # Modern dark palette
        self.colors = {
            "bg": "#0b0b10", "bg_alt": "#12121a", "card": "#191922", "card_hi": "#21212c",
            "border": "#2b2b3a", "accent": "#00d1b2", "accent_hi": "#00f2d3",
            "accent_hover": "#00f2d3", "accent_dim": "#0c7d6e",
            "text": "#f4f5f7", "text_dim": "#9aa0ab", "text_mute": "#5a6070",
            "btn_default": "#23232f", "btn_hover": "#2f2f3d",
            "success": "#2ee6a6", "error": "#ff4d6d", "warning": "#ffd166",
            "highlight": "#5b8def", "purple": "#a779ff", "orange": "#ff9f43",
        }

        # Workflow definition — single source of truth for stepper + content
        self.steps = [
            {"id": "0", "key": "phase0", "emoji": "📥", "title": "นำเข้ารูปใหม่", "subtitle": "Import New",
             "desc": "ดึงรูปใหม่จากโฟลเดอร์กล้องอัตโนมัติ (จำไฟล์ที่เคยดึงไปแล้ว จะไม่ดึงซ้ำ) แล้วคัดลอกแยกตามรหัส 4 หลักเข้าสู่ Workspace โดยไม่ลบต้นฉบับ",
             "btn": "📥  นำเข้ารูปใหม่", "action": self.run_phase_0_import, "color": "accent", "beta": True},
            {"id": "1", "key": "phase1", "emoji": "🗂", "title": "จัดกลุ่มตามรหัส", "subtitle": "Group by Code",
             "desc": "แยกรูปที่อยู่ใน Workspace เข้ากลุ่มโฟลเดอร์ตามรหัส 4 หลักที่พบในชื่อไฟล์",
             "btn": "🗂  จัดกลุ่มตามรหัส", "action": self.run_phase_1, "color": "highlight"},
            {"id": "1.5", "key": "phase1_5", "emoji": "🤖", "title": "รีทัชด้วย AI", "subtitle": "AI Retouch · ChatGPT",
             "desc": "เลือกรูป (สูงสุด 2 รูป/โฟลเดอร์) แล้วส่งเข้า ChatGPT รีทัชอัตโนมัติผ่านเบราว์เซอร์ และดาวน์โหลดผลกลับมาเป็นไฟล์ _AI",
             "btn": "🤖  เริ่มรีทัช AI", "action": self.run_phase_ai_retouch, "color": "highlight"},
            {"id": "1.6", "key": "phase1_6", "emoji": "🔗", "title": "รวมรูปต่างหู", "subtitle": "Merge",
             "desc": "เลือก 2 รูปต่อโฟลเดอร์ (หน้า/ข้าง) แล้วเข้าหน้าจัดวาง ปรับขนาด/สลับ/บันทึก เป็นภาพเดียวบนพื้นหลังขาว",
             "btn": "🔗  เลือกรูปแล้วรวม", "action": self.run_phase_merge, "color": "purple"},
            {"id": "1.7", "key": "phase1_7", "emoji": "✂️", "title": "ครอบตัดรูป", "subtitle": "Crop",
             "desc": "เลือกรูปที่ต้องการครอบตัด (เลือกได้หลายรูป) แล้วระบบจะดึงมาให้ปรับ zoom/ตำแหน่ง ทีละรูป",
             "btn": "✂️  เลือกรูปแล้วครอบตัด", "action": self.run_phase_crop, "color": "orange"},
            {"id": "2", "key": "phase2", "emoji": "🏷", "title": "เปลี่ยนชื่อ + เลือกรูปหลัก", "subtitle": "Rename & Primary",
             "desc": "เลือกรูปหลักของแต่ละชุด แล้วเปลี่ยนชื่อไฟล์ทั้งหมดตามรหัสโฟลเดอร์ (รูปหลัก = รหัส, รูปอื่น = รหัส-2, -3 ...)",
             "btn": "🏷  เปลี่ยนชื่อ & เลือกรูปหลัก", "action": self.run_phase_rename, "color": "highlight"},
            {"id": "3", "key": "phase3", "emoji": "💾", "title": "เก็บเข้าฐานข้อมูล", "subtitle": "Collect to DB",
             "desc": "ก๊อปปี้ไฟล์ที่ตั้งชื่อแล้วไปยัง Photo 1 (Main) และ Photo 2 (Backup) พร้อมกัน จัดวางตามหมวดหมู่และช่วงรหัส",
             "btn": "💾  เก็บเข้าฐานข้อมูล", "action": self.run_phase_backup, "color": "highlight"},
            {"id": "4", "key": "phase4", "emoji": "📦", "title": "ย้ายเข้าคลัง", "subtitle": "Archive",
             "desc": "ย้ายโฟลเดอร์ทั้งหมดใน Workspace เข้าคลังเก็บประวัติ จัดเรียงตามปี/เดือน/วันที่",
             "btn": "📦  ย้ายเข้าคลัง", "action": self.run_phase_archive, "color": "highlight"},
        ]
        self.step_widgets = {}
        self.current_step = "0"
        self.completed_steps = set()
        self.status_var = tk.StringVar(value="")
        self.ai_btn = None
        self.ai_btn_default_text = "🤖  เริ่มรีทัช AI"
        self.ai_cancel_event = threading.Event()
        self.log_visible = True

        self.load_settings()
        self.create_widgets()
        if HAS_DND:
            self.setup_dnd()
        self.root.after(120, self.start_animation_loop)
        self.root.after(1000, self.auto_detect_downloads)

    # ----------------------------- Settings / Memory -----------------------------
    def load_settings(self):
        default_types = {'R': 'Ring', 'N': 'Necklace', 'E': 'Earring', 'P': 'Pendant', 'B': 'Bracelet', 'S': 'Sets'}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.photo1_dir.set(data.get('photo1', ''))
                    self.photo2_dir.set(data.get('photo2', ''))
                    self.archive_dir.set(data.get('archive', ''))
                    self.camera_source.set(data.get('camera_source', ''))
                    if data.get('chatgpt_url'):
                        self.chatgpt_url.set(data.get('chatgpt_url'))
                    self.chrome_profile_dir.set(data.get('chrome_profile_dir', ''))
                    self.type_mapping = data.get('types', default_types)
            except Exception as e:
                self.type_mapping = default_types
                print(f"Failed to load settings: {e}")
        else:
            self.type_mapping = default_types

    def save_settings(self):
        data = {
            'photo1': self.photo1_dir.get(), 'photo2': self.photo2_dir.get(),
            'archive': self.archive_dir.get(), 'camera_source': self.camera_source.get(),
            'chatgpt_url': self.chatgpt_url.get(), 'chrome_profile_dir': self.chrome_profile_dir.get(),
            'types': self.type_mapping,
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_manifest(self):
        try:
            if os.path.exists(self.manifest_file):
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            print(f"Failed to load manifest: {e}")
        return set()

    def save_manifest(self, manifest):
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(manifest), f, ensure_ascii=False)
        except Exception as e:
            self.log_threadsafe(f"บันทึก manifest ไม่สำเร็จ: {e}", "error")

    def reset_manifest(self):
        if messagebox.askyesno("ยืนยัน", "ล้างความจำการนำเข้าทั้งหมด?\nครั้งหน้าขั้นตอนที่ 0 จะดึงรูปเก่าออกมาใหม่ทั้งหมด"):
            try:
                if os.path.exists(self.manifest_file):
                    os.remove(self.manifest_file)
                self.log("ล้างความจำการนำเข้าแล้ว", "success")
            except Exception as e:
                self.log(f"ล้างความจำไม่สำเร็จ: {e}", "error")

    # ----------------------------- Logging / threadsafe helpers -----------------------------
    def log(self, message, category="info", code=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        tag = "info"; prefix = "• "
        if category == "error":
            tag = "error"; prefix = "✖ "
            if code and code in self.error_codes:
                message = f"[{code}] {message} -> {self.error_codes[code]}"
        elif "สำเร็จ" in message or "Success" in message:
            tag = "success"; prefix = "✔ "
        elif "ข้าม" in message or "Skipped" in message:
            tag = "warning"; prefix = "⚠ "
        elif "ตรวจพบ" in message or "AI" in message:
            tag = "highlight"; prefix = "✨ "

        msg_line = f"[{timestamp}] {prefix}{message}\n"
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled'); self.log_area.see(tk.END)
        try:
            with open(self.history_log, "a", encoding="utf-8") as f:
                f.write(msg_line)
        except Exception as e:
            print(f"Failed to write history log: {e}")

    def log_threadsafe(self, message, category="info", code=None):
        self.root.after(0, lambda: self.log(message, category, code))

    def set_progress_threadsafe(self, value, maximum=None):
        def update():
            if maximum is not None:
                self.progress['maximum'] = maximum
            self.progress['value'] = value
        self.root.after(0, update)

    def set_running(self, phase, running):
        self.root.after(0, lambda: self.is_running.__setitem__(phase, running))

    def mark_completed(self, step_id):
        self.root.after(0, lambda: self.completed_steps.add(step_id))

    def is_image_file(self, filename):
        return filename.lower().endswith(IMAGE_EXTENSIONS)

    def current_step_key(self):
        for s in self.steps:
            if s["id"] == self.current_step:
                return s["key"]
        return ""

    # ----------------------------- Animation -----------------------------
    def start_animation_loop(self):
        self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
        spin = self.anim_chars[self.anim_idx]
        for step in self.steps:
            key = step["key"]; sid = step["id"]
            w = self.step_widgets.get(key)
            if not w:
                continue
            badge, name = w["badge"], w["name"]
            try:
                if self.is_running.get(key):
                    badge.config(text=spin, bg=self.colors["accent"], fg="#08120f")
                    name.config(fg=self.colors["accent"])
                elif sid in self.completed_steps:
                    badge.config(text="✓", bg=self.colors["accent_dim"], fg=self.colors["text"])
                    name.config(fg=self.colors["text_dim"])
                elif sid == self.current_step:
                    pulse = self.colors["accent"] if (self.anim_idx // 3) % 2 == 0 else self.colors["accent_hi"]
                    badge.config(text=sid, bg=pulse, fg="#08120f")
                    name.config(fg=self.colors["text"])
                else:
                    badge.config(text=sid, bg=self.colors["card"], fg=self.colors["text_dim"])
                    name.config(fg=self.colors["text_mute"])
            except tk.TclError:
                pass

        if self.is_running.get(self.current_step_key(), False):
            self.status_var.set(f"{spin}  กำลังทำงาน...")
        else:
            self.status_var.set("")
        self.root.after(120, self.start_animation_loop)

    # ----------------------------- Drag & Drop -----------------------------
    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"Drag & Drop: {path}", "success")

    def auto_detect_downloads(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads):
            return
        candidates = [d for d in os.listdir(downloads)
                      if os.path.isdir(os.path.join(downloads, d)) and d.lower().startswith("media -")]
        if not candidates:
            return
        candidates.sort(key=lambda x: os.path.getctime(os.path.join(downloads, x)), reverse=True)
        if os.path.join(downloads, candidates[0]) != self.source_dir.get():
            if messagebox.askyesno("New Workspace", f"ใช้โฟลเดอร์ล่าสุดนี้เป็น Workspace?\n{candidates[0]}"):
                self.source_dir.set(os.path.join(downloads, candidates[0]))

    # ----------------------------- UI: shell -----------------------------
    def create_widgets(self):
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("PixUp.Horizontal.TProgressbar", troughcolor=self.colors["card"],
                        background=self.colors["accent"], thickness=12, borderwidth=0)

        self.build_header(self.root)
        self.build_workspace_bar(self.root)
        self.build_stepper(self.root)
        # Log bar pinned to bottom (packed before the expanding content so it never gets squeezed)
        self.build_log(self.root)
        self.content_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.content_frame.pack(fill="both", expand=True)
        self.show_step(self.current_step)

    def build_header(self, parent):
        h = tk.Frame(parent, bg=self.colors["bg_alt"], height=92)
        h.pack(fill="x"); h.pack_propagate(False)
        left = tk.Frame(h, bg=self.colors["bg_alt"]); left.pack(side="left", padx=30)
        tk.Label(left, text="PIXUP", bg=self.colors["bg_alt"], fg=self.colors["accent"],
                 font=("Segoe UI", 26, "bold")).pack(anchor="w", pady=(18, 0))
        tk.Label(left, text=f"KH CREATION STUDIO  ·  v{self.version}", bg=self.colors["bg_alt"],
                 fg=self.colors["text_mute"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        gear = tk.Button(h, text="⚙", command=self.open_settings, bg=self.colors["bg_alt"],
                         fg=self.colors["text_dim"], relief="flat", font=("Segoe UI", 20),
                         activebackground=self.colors["bg_alt"], activeforeground=self.colors["accent"],
                         cursor="hand2")
        gear.pack(side="right", padx=28)

    def build_workspace_bar(self, parent):
        bar = tk.Frame(parent, bg=self.colors["bg"]); bar.pack(fill="x", padx=30, pady=(14, 0))
        card = tk.Frame(bar, bg=self.colors["card"], padx=16, pady=12,
                        highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill="x")
        tk.Label(card, text="📂 WORKSPACE", bg=self.colors["card"], fg=self.colors["text_dim"],
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 12))
        self.source_entry = tk.Entry(card, textvariable=self.source_dir, font=("Consolas", 10),
                                     bg=self.colors["bg"], fg=self.colors["text"], relief="flat",
                                     insertbackground="white")
        self.source_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 12))
        tk.Button(card, text="เลือกโฟลเดอร์", command=lambda: self.browse_dir(self.source_dir, False),
                  bg=self.colors["accent"], fg="#08120f", relief="flat",
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")

    def build_stepper(self, parent):
        bar = tk.Frame(parent, bg=self.colors["bg_alt"]); bar.pack(fill="x", padx=30, pady=(14, 0))
        inner = tk.Frame(bar, bg=self.colors["bg_alt"]); inner.pack(fill="x", pady=16)
        self.step_widgets = {}
        for i, step in enumerate(self.steps):
            inner.columnconfigure(i, weight=1, uniform="steps")
            cell = tk.Frame(inner, bg=self.colors["bg_alt"])
            cell.grid(row=0, column=i, sticky="nsew")
            badge = tk.Label(cell, text=step["id"], width=4, height=2, bg=self.colors["card"],
                             fg=self.colors["text_dim"], font=("Segoe UI", 12, "bold"), cursor="hand2")
            badge.pack()
            name = tk.Label(cell, text=step["subtitle"], bg=self.colors["bg_alt"],
                            fg=self.colors["text_mute"], font=("Segoe UI", 7), cursor="hand2",
                            wraplength=120, justify="center")
            name.pack(pady=(5, 0))
            for wdg in (badge, name):
                wdg.bind("<Button-1>", lambda e, sid=step["id"]: self.show_step(sid))
            self.step_widgets[step["key"]] = {"badge": badge, "name": name, "step": step}

    def build_content(self, step_id):
        step = next((s for s in self.steps if s["id"] == step_id), self.steps[0])
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.ai_btn = None

        card = tk.Frame(self.content_frame, bg=self.colors["card"], padx=40, pady=34,
                        highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(fill="both", expand=True, padx=30, pady=18)

        title_row = tk.Frame(card, bg=self.colors["card"]); title_row.pack(fill="x", anchor="w")
        tk.Label(title_row, text=f"{step['emoji']}  {step['title']}", bg=self.colors["card"],
                 fg=self.colors["text"], font=("Segoe UI", 20, "bold")).pack(side="left", anchor="w")
        if step.get("beta"):
            tk.Label(title_row, text=" BETA ", bg=self.colors["warning"], fg="#1a1a1a",
                     font=("Segoe UI", 8, "bold")).pack(side="left", padx=10, pady=6)
        tk.Label(card, text=step["subtitle"].upper(), bg=self.colors["card"],
                 fg=self.colors.get(step.get("color", "accent")), font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(card, text=step["desc"], bg=self.colors["card"], fg=self.colors["text_dim"],
                 font=("Segoe UI", 11), wraplength=720, justify="left").pack(anchor="w", pady=(18, 0))

        btn = self.create_styled_button(card, step["btn"], step["action"],
                                        self.colors.get(step.get("color", "accent")), "#08120f")
        btn.pack(fill="x", pady=(28, 0), ipady=6)
        if step_id == "1.5":
            self.ai_btn = btn

        tk.Label(card, textvariable=self.status_var, bg=self.colors["card"], fg=self.colors["accent"],
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(16, 0))

        nav = tk.Frame(card, bg=self.colors["card"]); nav.pack(fill="x", side="bottom", pady=(20, 0))
        ids = [s["id"] for s in self.steps]
        idx = ids.index(step_id)
        if idx > 0:
            tk.Button(nav, text="‹ ก่อนหน้า", command=lambda: self.show_step(ids[idx - 1]),
                      bg=self.colors["btn_default"], fg=self.colors["text"], relief="flat",
                      font=("Segoe UI", 9), cursor="hand2", padx=10, pady=4).pack(side="left")
        if idx < len(ids) - 1:
            tk.Button(nav, text="ถัดไป ›", command=lambda: self.show_step(ids[idx + 1]),
                      bg=self.colors["btn_default"], fg=self.colors["text"], relief="flat",
                      font=("Segoe UI", 9), cursor="hand2", padx=10, pady=4).pack(side="right")

    def show_step(self, step_id):
        self.current_step = step_id
        self.build_content(step_id)

    def build_log(self, parent):
        wrap = tk.Frame(parent, bg=self.colors["bg"]); wrap.pack(side="bottom", fill="x", padx=30, pady=(0, 16))
        self.progress = ttk.Progressbar(wrap, orient="horizontal", mode="determinate",
                                        style="PixUp.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 8))
        head = tk.Frame(wrap, bg=self.colors["bg"]); head.pack(fill="x")
        tk.Label(head, text="ACTIVITY LOG", bg=self.colors["bg"], fg=self.colors["text_dim"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.log_toggle_btn = tk.Button(head, text="▾ ซ่อน", command=self.toggle_log,
                                        bg=self.colors["bg"], fg=self.colors["text_dim"], relief="flat",
                                        font=("Segoe UI", 8), cursor="hand2", activebackground=self.colors["bg"])
        self.log_toggle_btn.pack(side="right")
        self.log_area = scrolledtext.ScrolledText(wrap, height=9, bg="#08080c", fg="#bbb",
                                                  font=("Consolas", 9), relief="flat", padx=14, pady=10)
        self.log_area.pack(fill="both", expand=True, pady=(6, 0))
        self.log_area.tag_config("time", foreground="#444")
        self.log_area.tag_config("success", foreground=self.colors["success"])
        self.log_area.tag_config("error", foreground=self.colors["error"])
        self.log_area.tag_config("warning", foreground=self.colors["warning"])
        self.log_area.tag_config("highlight", foreground=self.colors["highlight"])
        self.log_area.tag_config("info", foreground="#dddddd")
        self.log_area.configure(state='disabled')

    def toggle_log(self):
        if self.log_visible:
            self.log_area.pack_forget()
            self.log_toggle_btn.config(text="▸ แสดง")
        else:
            self.log_area.pack(fill="both", expand=True, pady=(6, 0))
            self.log_toggle_btn.config(text="▾ ซ่อน")
        self.log_visible = not self.log_visible

    def create_styled_button(self, parent, text, cmd, bg, fg):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=("Segoe UI", 11, "bold"),
                      relief="flat", height=2, cursor="hand2", activebackground=self.colors["btn_hover"])
        b.bind("<Enter>", lambda e: b.config(bg=self.colors["accent_hover"] if bg == self.colors["accent"] else self.colors["btn_hover"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d:
            var.set(os.path.normpath(d))
        if is_config:
            self.save_settings()

    def add_path_card(self, parent, label, var):
        c = tk.Frame(parent, bg=self.colors["card"], padx=16, pady=12,
                     highlightthickness=1, highlightbackground=self.colors["border"])
        c.pack(fill="x", pady=6)
        tk.Label(c, text=label, fg=self.colors["text_dim"], bg=self.colors["card"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(c, bg=self.colors["card"]); row.pack(fill="x", pady=(8, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg=self.colors["bg"], fg=self.colors["text"],
                 relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=6)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, True), bg=self.colors["btn_default"],
                  fg=self.colors["text"], relief="flat", width=4, cursor="hand2").pack(side="right", padx=(8, 0))

    # ----------------------------- Settings window -----------------------------
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("ตั้งค่า / Settings"); win.geometry("580x760"); win.configure(bg=self.colors["bg"]); win.grab_set()
        tk.Label(win, text="⚙  SETTINGS", bg=self.colors["bg"], fg=self.colors["accent"],
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=24, pady=(20, 10))
        body = tk.Frame(win, bg=self.colors["bg"]); body.pack(fill="both", expand=True, padx=24)

        self.add_path_card(body, "PHOTO 1 — MAIN DATABASE DRIVE", self.photo1_dir)
        self.add_path_card(body, "PHOTO 2 — BACKUP DATABASE DRIVE", self.photo2_dir)
        self.add_path_card(body, "ARCHIVE — HISTORY STORAGE", self.archive_dir)
        self.add_path_card(body, "CAMERA SOURCE — โฟลเดอร์กล้องสำหรับขั้นตอนที่ 0 (เช่น D:/gemlight box)", self.camera_source)

        cg = tk.Frame(body, bg=self.colors["card"], padx=16, pady=12,
                      highlightthickness=1, highlightbackground=self.colors["border"])
        cg.pack(fill="x", pady=6)
        tk.Label(cg, text="CHATGPT CUSTOM GPT URL  (เว้นว่าง = ใช้ chatgpt.com ปกติ)", bg=self.colors["card"],
                 fg=self.colors["highlight"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(cg, textvariable=self.chatgpt_url, font=("Consolas", 9), bg=self.colors["bg"],
                 fg=self.colors["text"], relief="flat", insertbackground="white").pack(fill="x", pady=(8, 0), ipady=6)

        self.add_path_card(body, "CHROME PROFILE (ขั้นสูง · เว้นว่าง = โปรไฟล์ของ PixUp ล็อกอินครั้งเดียว)", self.chrome_profile_dir)

        self.create_styled_button(body, "⚙  จัดการหมวดหมู่ (Categories)", self.open_category_manager,
                                  self.colors["btn_default"], self.colors["text"]).pack(fill="x", pady=(14, 6))
        self.create_styled_button(body, "🗑  ล้างความจำการนำเข้า (Reset Import Memory)", self.reset_manifest,
                                  self.colors["btn_default"], self.colors["warning"]).pack(fill="x", pady=6)

        def save_close():
            self.save_settings(); win.destroy(); self.log("บันทึกการตั้งค่าแล้ว", "success")
        self.create_styled_button(win, "บันทึก & ปิด", save_close, self.colors["accent"], "#08120f").pack(
            fill="x", padx=24, pady=18)

    def open_category_manager(self):
        m = tk.Toplevel(self.root); m.title("Categories"); m.geometry("500x650")
        m.configure(bg=self.colors["card"]); m.grab_set()
        tree = ttk.Treeview(m, columns=("C", "N"), show="headings", height=15)
        tree.heading("C", text="Code"); tree.heading("N", text="Name")
        tree.pack(padx=20, pady=10, fill="both", expand=True)

        def refresh():
            for i in tree.get_children():
                tree.delete(i)
            for c, n in sorted(self.type_mapping.items()):
                tree.insert("", "end", values=(c, n))
        refresh()
        ctrl = tk.Frame(m, bg=self.colors["card"], pady=10); ctrl.pack(fill="x", padx=20)
        c_e = tk.Entry(ctrl, width=5); c_e.grid(row=0, column=0)
        n_e = tk.Entry(ctrl, width=15); n_e.grid(row=0, column=1, padx=5)

        def add():
            c, n = c_e.get().strip().upper(), n_e.get().strip()
            if c and n:
                self.type_mapping[c] = n; self.save_settings(); refresh()
                c_e.delete(0, 100); n_e.delete(0, 100)
        self.create_styled_button(ctrl, "ADD", add, self.colors["accent"], "#08120f").grid(row=0, column=2)

        def delete():
            s = tree.selection()
            if s:
                code = tree.item(s[0])['values'][0]
                if messagebox.askyesno("Confirm", f"Delete '{code}'?"):
                    del self.type_mapping[str(code)]; self.save_settings(); refresh()
        self.create_styled_button(m, "DELETE", delete, self.colors["error"], "#fff").pack(fill="x", padx=20, pady=20)

    # ----------------------------- Image selector (shared) -----------------------------
    def open_image_selector(self, folder_paths, max_per_folder, title, subtitle=""):
        """Per-folder thumbnail selector. Returns {folder_path: [files]} or None if cancelled."""
        win = tk.Toplevel(self.root); win.title(title); win.geometry("1120x860")
        win.grab_set(); win.configure(bg=self.colors["bg"])

        # Header (top)
        head = tk.Frame(win, bg=self.colors["bg"]); head.pack(fill="x", padx=20, pady=(16, 2))
        tk.Label(head, text=title, bg=self.colors["bg"], fg=self.colors["accent"],
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, bg=self.colors["bg"], fg=self.colors["text_dim"],
                     font=("Segoe UI", 9)).pack(anchor="w")

        sel = {}
        photo_refs = {}
        count_var = tk.StringVar(value="เลือกแล้ว 0 รูป")

        def update_count():
            n = sum(len(v) for v in sel.values())
            count_var.set(f"เลือกแล้ว {n} รูป")

        # Bottom action bar — packed BEFORE the scroll area so it always stays visible
        btns = tk.Frame(win, bg=self.colors["bg_alt"]); btns.pack(fill="x", side="bottom")
        btns_in = tk.Frame(btns, bg=self.colors["bg_alt"]); btns_in.pack(fill="x", padx=20, pady=14)
        tk.Label(btns_in, textvariable=count_var, bg=self.colors["bg_alt"], fg=self.colors["text"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        confirmed = {"ok": False}

        def on_ok():
            final = {k: v for k, v in sel.items() if v}
            if not final:
                messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกอย่างน้อย 1 รูป", parent=win)
                return
            confirmed["ok"] = True
            sel.clear(); sel.update(final)
            win.destroy()

        tk.Button(btns_in, text="ยืนยัน ✓", command=on_ok, bg=self.colors["accent"], fg="#08120f",
                  font=("Segoe UI", 11, "bold"), padx=28, pady=8, relief="flat", cursor="hand2").pack(side="right")
        tk.Button(btns_in, text="ยกเลิก", command=win.destroy, bg=self.colors["btn_default"],
                  fg=self.colors["text"], relief="flat", font=("Segoe UI", 10, "bold"), padx=20, pady=8,
                  cursor="hand2").pack(side="right", padx=(0, 10))

        # Scroll area (fills remaining space)
        container = tk.Frame(win, bg=self.colors["bg"]); container.pack(fill="both", expand=True, padx=20, pady=10)
        canvas = tk.Canvas(container, bg=self.colors["bg"], highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview); scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        scroll_f = tk.Frame(canvas, bg=self.colors["bg"]); canvas.create_window((0, 0), window=scroll_f, anchor="nw")
        scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        any_image = False
        for f_path in folder_paths:
            f_name = os.path.basename(f_path)
            row = tk.Frame(scroll_f, bg=self.colors["card"], pady=10, padx=10,
                           highlightthickness=1, highlightbackground=self.colors["border"])
            row.pack(fill="x", pady=5)
            tk.Label(row, text=f_name, bg=self.colors["card"], fg=self.colors["text_dim"],
                     font=("Consolas", 10, "bold"), width=14, anchor="w").pack(side="left", padx=8)
            img_container = tk.Frame(row, bg=self.colors["card"]); img_container.pack(side="left", fill="x", expand=True)
            try:
                files = sorted([f for f in os.listdir(f_path) if self.is_image_file(f)])
            except Exception:
                files = []
            sel[f_path] = []
            if not files:
                tk.Label(img_container, text="(ไม่มีรูปในโฟลเดอร์นี้)", bg=self.colors["card"],
                         fg=self.colors["text_mute"], font=("Segoe UI", 9)).pack(side="left", padx=8)
            for f in files:
                try:
                    full_p = os.path.join(f_path, f)
                    img = Image.open(full_p); img.thumbnail((110, 110)); ph = ImageTk.PhotoImage(img)
                    photo_refs[full_p] = ph
                    any_image = True
                    cell = tk.Frame(img_container, bg=self.colors["card"]); cell.pack(side="left", padx=4)
                    lbl = tk.Label(cell, image=ph, bg=self.colors["card"], borderwidth=3,
                                   relief="flat", cursor="hand2",
                                   highlightthickness=3, highlightbackground=self.colors["card"])
                    lbl.pack()

                    def toggle(f_p=f_path, fn=f, b=lbl):
                        if fn in sel[f_p]:
                            sel[f_p].remove(fn)
                            b.config(relief="flat", highlightbackground=self.colors["card"], highlightcolor=self.colors["card"])
                        else:
                            if max_per_folder is not None and len(sel[f_p]) >= max_per_folder:
                                messagebox.showwarning("จำกัด", f"เลือกได้สูงสุด {max_per_folder} รูป/โฟลเดอร์", parent=win)
                                return
                            sel[f_p].append(fn)
                            b.config(relief="solid", highlightbackground=self.colors["accent"], highlightcolor=self.colors["accent"])
                        update_count()
                    lbl.bind("<Button-1>", lambda e, f_p=f_path, fn=f, b=lbl: toggle(f_p, fn, b))
                except Exception:
                    pass

        if not any_image:
            self.log("ไม่พบรูปในโฟลเดอร์ที่เลือก", "warning")

        self.root.wait_window(win)
        try:
            canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        return dict(sel) if confirmed["ok"] else None

    # ----------------------------- Phase 0: Import New -----------------------------
    def run_phase_0_import(self):
        cam = self.camera_source.get()
        dst = self.source_dir.get()
        if not cam or not os.path.exists(cam):
            messagebox.showerror("Error", f"{self.error_codes['E001']}\n\nกรุณาตั้งค่า 'Camera Source' ในหน้า Settings (⚙)")
            return
        if not dst:
            messagebox.showerror("Error", "ยังไม่ได้เลือกโฟลเดอร์ Workspace ปลายทาง")
            return
        if not os.path.exists(dst):
            try:
                os.makedirs(dst)
            except Exception as e:
                messagebox.showerror("Error", str(e)); return

        def task():
            self.set_running("phase0", True)
            self.set_progress_threadsafe(0, 100)
            manifest = self.load_manifest()
            try:
                all_files = [f for f in os.listdir(cam)
                             if os.path.isfile(os.path.join(cam, f)) and self.is_image_file(f)]
            except Exception as e:
                self.log_threadsafe(f"อ่านโฟลเดอร์กล้องไม่ได้: {e}", "error", "E003")
                self.set_running("phase0", False); return

            new_files = []
            for f in all_files:
                full = os.path.join(cam, f)
                try:
                    st = os.stat(full)
                    sig = f"{f}|{st.st_size}|{int(st.st_mtime)}"
                except Exception:
                    continue
                if sig not in manifest:
                    new_files.append((f, full, sig))

            if not new_files:
                self.log_threadsafe("ไม่มีรูปใหม่ — ดึงไปแล้วทั้งหมด (จำได้จากครั้งก่อน)", "warning")
                self.set_running("phase0", False); return

            self.log_threadsafe(f"พบรูปใหม่ {len(new_files)} ไฟล์ กำลังนำเข้า...", "highlight")
            copied = 0
            for i, (f, full, sig) in enumerate(new_files):
                m = re.search(r'(\d{4})', f)
                code = m.group(1) if m else "_ungrouped"
                target_dir = os.path.join(dst, code)
                try:
                    os.makedirs(target_dir, exist_ok=True)
                    dest = os.path.join(target_dir, f)
                    if os.path.exists(dest):
                        name, ext = os.path.splitext(f)
                        dest = os.path.join(target_dir, f"{name}_dup{ext}")
                    shutil.copy2(full, dest)
                    manifest.add(sig); copied += 1
                except Exception as e:
                    self.log_threadsafe(f"คัดลอกไม่สำเร็จ {f}: {e}", "error", "E007")
                self.set_progress_threadsafe((i + 1) / len(new_files) * 100)

            self.save_manifest(manifest)
            self.log_threadsafe(f"นำเข้าสำเร็จ {copied} ไฟล์ — ต้นฉบับยังอยู่ที่เดิม", "success")
            self.mark_completed("0")
            self.set_running("phase0", False)
        threading.Thread(target=task, daemon=True).start()

    # ----------------------------- Phase 1: Group by Code -----------------------------
    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        if not files:
            messagebox.showinfo("Info", self.error_codes["E002"]); return

        def task():
            self.set_running("phase1", True); moved = 0
            for i, f in enumerate(files):
                m = re.search(r'(\d{4})', f)
                if m:
                    c = m.group(1); t = os.path.join(src, c)
                    if not os.path.exists(t):
                        os.makedirs(t)
                    try:
                        shutil.move(os.path.join(src, f), os.path.join(t, f)); moved += 1
                    except Exception as e:
                        self.log_threadsafe(f"Move failed for {f}: {e}", "error", "E007")
                self.set_progress_threadsafe((i + 1) / len(files) * 100)
            self.log_threadsafe(f"ขั้นตอนที่ 1: จัดกลุ่ม {moved} ไฟล์สำเร็จ", "success")
            self.mark_completed("1")
            self.set_running("phase1", False)
        threading.Thread(target=task, daemon=True).start()

    # ----------------------------- Phase 1.5: AI Retouch (ChatGPT) -----------------------------
    def run_phase_ai_retouch(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return

        folders = sorted([os.path.join(src, d) for d in os.listdir(src)
                          if os.path.isdir(os.path.join(src, d)) and d not in ("ai_retouched",)])
        if not folders:
            self.log("ขั้นตอน 1.5: ไม่พบโฟลเดอร์ ลองทำขั้นตอน 0 หรือ 1 ก่อน", "warning")
            messagebox.showinfo("Info", "ยังไม่มีโฟลเดอร์ กรุณาทำขั้นตอนที่ 0 หรือ 1 ก่อน")
            return

        sel = self.open_image_selector(folders, 2, "เลือกรูปสำหรับรีทัช AI (สูงสุด 2 รูป/โฟลเดอร์)",
                                       "ติ๊กเลือกรูปที่จะส่งเข้า ChatGPT แล้วกดยืนยัน")
        if not sel:
            self.log("ขั้นตอน 1.5: ยกเลิกการเลือก", "warning")
            return
        self.ai_tasks = {k: {"files": v, "is_earring": len(v) == 2} for k, v in sel.items() if v}
        if not self.ai_tasks:
            return

        total = sum(len(v["files"]) for v in self.ai_tasks.values())
        self.log(f"ขั้นตอน 1.5: เริ่มรีทัช {total} รูป ใน {len(self.ai_tasks)} โฟลเดอร์...", "highlight")
        self.ai_cancel_event.clear()
        self.set_running("phase1_5", True)
        self._set_ai_btn_cancel()
        threading.Thread(target=self.chatgpt_agent_process, daemon=True).start()

    def _set_ai_btn_cancel(self):
        try:
            if self.ai_btn is not None and self.ai_btn.winfo_exists():
                self.ai_btn.config(text="■ ยกเลิก", bg=self.colors["error"], fg="#ffffff",
                                   command=self.cancel_ai, state="normal")
        except tk.TclError:
            pass

    def cancel_ai(self):
        self.ai_cancel_event.set()
        self.log("กำลังยกเลิก... จะหยุดหลังรูปปัจจุบันเสร็จ", "warning")
        try:
            if self.ai_btn is not None and self.ai_btn.winfo_exists():
                self.ai_btn.config(text="⌛ กำลังยกเลิก...", state="disabled")
        except tk.TclError:
            pass

    def chatgpt_agent_process(self):
        gpt_url = self.chatgpt_url.get().strip()
        self.log_threadsafe("ขั้นตอน 1.5: กำลังเปิดเบราว์เซอร์ ChatGPT...", "highlight")

        if not HAS_CHATGPT:
            self.log_threadsafe("โหลดโมดูล chatgpt_retouch ไม่ได้ (ตรวจว่ามีไฟล์ chatgpt_retouch.py)", "error")
            self.stop_ai_vis(); return

        def on_log(msg, level="info"):
            self.log_threadsafe(msg, level)

        def on_result(fname, success, error=""):
            if success:
                self.log_threadsafe(f"  > ChatGPT รีทัชสำเร็จ: {fname}", "success")
            else:
                self.log_threadsafe(f"  > ล้มเหลว {fname}: {error}", "error")

        try:
            chatgpt_retouch.run_retouch_blocking(self.ai_tasks, gpt_url, on_log, on_result,
                                                 should_cancel=self.ai_cancel_event.is_set,
                                                 profile_dir=self.chrome_profile_dir.get())
        except Exception as e:
            self.log_threadsafe(f"ChatGPT automation error: {e}", "error")

        if self.ai_cancel_event.is_set():
            self.log_threadsafe("ขั้นตอน 1.5: ยกเลิกแล้ว", "warning")
        else:
            self.log_threadsafe("ขั้นตอน 1.5: รีทัช AI เสร็จสิ้น", "highlight")
            self.mark_completed("1.5")
        self.stop_ai_vis()

    def stop_ai_vis(self):
        self.set_running("phase1_5", False)

        def _restore():
            try:
                if self.ai_btn is not None and self.ai_btn.winfo_exists():
                    self.ai_btn.config(text=self.ai_btn_default_text, bg=self.colors["highlight"],
                                       fg="#08120f", command=self.run_phase_ai_retouch, state="normal")
            except tk.TclError:
                pass
        self.root.after(0, _restore)

    # ----------------------------- Phase 1.6: Merge (manual selection) -----------------------------
    def run_phase_merge(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return
        folders = sorted([os.path.join(src, d) for d in os.listdir(src)
                          if os.path.isdir(os.path.join(src, d)) and d not in ("ai_retouched",)])
        if not folders:
            messagebox.showinfo("Info", "ยังไม่มีโฟลเดอร์ กรุณาทำขั้นตอนที่ 0 หรือ 1 ก่อน")
            return

        sel = self.open_image_selector(folders, 2, "เลือก 2 รูปต่อโฟลเดอร์เพื่อรวม (Merge)",
                                       "เลือกรูปหน้า/ข้าง ในแต่ละโฟลเดอร์ที่ต้องการรวม (2 รูป/โฟลเดอร์) แล้วกดยืนยัน")
        if not sel:
            self.log("ขั้นตอน 1.6: ยกเลิกการเลือก", "warning")
            return
        merge_list = [(k, v) for k, v in sel.items() if len(v) == 2]
        if not merge_list:
            messagebox.showinfo("Info", "ต้องเลือกครบ 2 รูปในโฟลเดอร์ที่จะรวม")
            return

        def task():
            self.set_running("phase1_6", True)
            self.log_threadsafe(f"ขั้นตอน 1.6: เริ่มรวมรูป {len(merge_list)} โฟลเดอร์...", "highlight")
            for i, (f_path, files) in enumerate(merge_list):
                f_n = os.path.basename(f_path)
                paths = [os.path.join(f_path, f) for f in files]
                self.log_threadsafe(f"รวมรูป: {f_n} ({i + 1}/{len(merge_list)})", "info")
                self.merge_done_event = threading.Event()
                self.root.after(0, lambda p=paths, d=f_path, n=f_n, idx=i + 1, total=len(merge_list):
                                self.open_interactive_merge_ui(p, d, n, idx, total))
                self.merge_done_event.wait()
            self.set_running("phase1_6", False)
            self.mark_completed("1.6")
            self.log_threadsafe("รวมรูปเสร็จสิ้น", "success")
        threading.Thread(target=task, daemon=True).start()

    def open_interactive_merge_ui(self, ai_paths, out_dir, folder_name, current, total):
        win = tk.Toplevel(self.root); win.title(f"MERGE: {folder_name} ({current}/{total})")
        win.geometry("860x880"); win.grab_set(); win.configure(bg=self.colors["bg"])
        COMP, PV = 2000, 640

        try:
            base_imgs = [Image.open(p).convert("RGBA") for p in ai_paths]
        except Exception as e:
            messagebox.showerror("Error", f"เปิดรูปไม่ได้: {e}", parent=win)
            win.destroy(); self.merge_done_event.set(); return

        state = [{"scale": 1.0, "cx": COMP * 0.27, "cy": COMP * 0.5},
                 {"scale": 1.0, "cx": COMP * 0.73, "cy": COMP * 0.5}]
        active = {"i": 0}
        boxes = [None, None]
        MID = COMP / 2

        tk.Label(win, text=f"รวมรูปต่างหู — {folder_name}", bg=self.colors["bg"], fg=self.colors["accent"],
                 font=("Segoe UI", 13, "bold")).pack(pady=(12, 0))
        tk.Label(win, text="คลิกเลือกรูป → ลากเพื่อย้าย · ล้อเมาส์เพื่อย่อ/ขยาย",
                 bg=self.colors["bg"], fg=self.colors["text_dim"], font=("Segoe UI", 9)).pack(pady=(0, 6))

        # Bottom action bar (pinned first so it never gets clipped)
        bar = tk.Frame(win, bg=self.colors["bg_alt"]); bar.pack(side="bottom", fill="x")
        barin = tk.Frame(bar, bg=self.colors["bg_alt"]); barin.pack(fill="x", padx=20, pady=12)
        # Control row (also bottom-pinned, above the action bar)
        ctrl = tk.Frame(win, bg=self.colors["bg"]); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 6))

        canvas = tk.Canvas(win, width=PV, height=PV, bg="white", highlightthickness=1,
                           highlightbackground=self.colors["border"], cursor="fleur")
        canvas.pack(pady=8)

        def comp_size(i):
            """ขนาดรูป i ในพิกัด composite (longest side = 900*scale)"""
            im = base_imgs[i]
            longest = max(10.0, 900 * state[i]["scale"])
            bw, bh = im.size
            if bw >= bh:
                return longest, longest * bh / bw
            return longest * bw / bh, longest

        def clamp(i):
            """กันไม่ให้รูปข้ามเส้นกลาง และไม่ให้หลุดขอบ"""
            cw, ch = comp_size(i)
            hw, hh = cw / 2, ch / 2
            if i == 0:   # ซ้าย: ขอบขวาไม่เกินเส้นกลาง
                state[i]["cx"] = min(max(state[i]["cx"], hw), MID - hw)
            else:        # ขวา: ขอบซ้ายไม่ต่ำกว่าเส้นกลาง
                state[i]["cx"] = min(max(state[i]["cx"], MID + hw), COMP - hw)
            state[i]["cy"] = min(max(state[i]["cy"], hh), COMP - hh)

        def build(size):
            s = size / COMP
            comp = Image.new('RGB', (size, size), (255, 255, 255))
            bxs = []
            for i, im in enumerate(base_imgs):
                w = max(10, int(900 * state[i]["scale"] * s))
                t = im.copy(); t.thumbnail((w, w), Image.Resampling.LANCZOS)
                x = int(state[i]["cx"] * s - t.width / 2)
                y = int(state[i]["cy"] * s - t.height / 2)
                comp.paste(t, (x, y), t)
                bxs.append((x, y, t.width, t.height))
            return comp, bxs

        def refresh():
            clamp(0); clamp(1)
            canvas.delete("all")
            comp, bxs = build(PV)
            ph = ImageTk.PhotoImage(comp); canvas.image = ph
            canvas.create_image(0, 0, image=ph, anchor="nw")
            # เส้นแบ่งกลาง (เฉพาะบนจอ ไม่ถูกบันทึกลงไฟล์)
            canvas.create_line(PV / 2, 0, PV / 2, PV, fill=self.colors["highlight"], width=1, dash=(6, 4))
            for i, b in enumerate(bxs):
                boxes[i] = b
                color = self.colors["accent"] if i == active["i"] else self.colors["text_mute"]
                canvas.create_rectangle(b[0], b[1], b[0] + b[2], b[1] + b[3], outline=color, width=2)

        drag = {"x": 0, "y": 0}

        def on_press(e):
            for i in (1, 0):
                b = boxes[i]
                if b and b[0] <= e.x <= b[0] + b[2] and b[1] <= e.y <= b[1] + b[3]:
                    active["i"] = i; break
            drag["x"], drag["y"] = e.x, e.y
            refresh()

        def on_drag(e):
            f = COMP / PV
            state[active["i"]]["cx"] += (e.x - drag["x"]) * f
            state[active["i"]]["cy"] += (e.y - drag["y"]) * f
            drag["x"], drag["y"] = e.x, e.y
            refresh()

        def on_wheel(e):
            d = 1.1 if e.delta > 0 else 0.9
            state[active["i"]]["scale"] = max(0.1, min(3.0, state[active["i"]]["scale"] * d))
            refresh()

        canvas.bind("<Button-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<MouseWheel>", on_wheel)

        def set_active(i):
            active["i"] = i; refresh()
        tk.Button(ctrl, text="◧ ปรับรูปซ้าย", command=lambda: set_active(0), bg=self.colors["btn_default"],
                  fg=self.colors["text"], relief="flat", cursor="hand2", padx=10).pack(side="left")
        tk.Button(ctrl, text="ปรับรูปขวา ◨", command=lambda: set_active(1), bg=self.colors["btn_default"],
                  fg=self.colors["text"], relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(8, 0))

        def swap():
            base_imgs[0], base_imgs[1] = base_imgs[1], base_imgs[0]
            state[0], state[1] = state[1], state[0]
            refresh()
        tk.Button(ctrl, text="⇄ สลับซ้าย-ขวา", command=swap, bg=self.colors["btn_default"],
                  fg=self.colors["text"], relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(8, 0))

        def save_and_next():
            comp, _ = build(COMP)
            comp.save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95, optimize=True)
            win.destroy(); self.merge_done_event.set()
        tk.Button(barin, text="บันทึก & ถัดไป →", command=save_and_next, bg=self.colors["success"], fg="#000",
                  font=("Segoe UI", 12, "bold"), padx=24, pady=8, relief="flat", cursor="hand2").pack(side="right")
        tk.Button(barin, text="ข้าม", command=lambda: [win.destroy(), self.merge_done_event.set()],
                  bg=self.colors["btn_default"], fg=self.colors["text"], relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=18, pady=8, cursor="hand2").pack(side="right", padx=(0, 10))

        win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), self.merge_done_event.set()])
        refresh()

    # ----------------------------- Phase 1.7: Crop (manual selection) -----------------------------
    def run_phase_crop(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return
        folders = sorted([os.path.join(src, d) for d in os.listdir(src)
                          if os.path.isdir(os.path.join(src, d)) and d not in ("ai_retouched",)])
        if not folders:
            messagebox.showinfo("Info", "ยังไม่มีโฟลเดอร์ กรุณาทำขั้นตอนที่ 0 หรือ 1 ก่อน")
            return

        sel = self.open_image_selector(folders, None, "เลือกรูปที่จะครอบตัด (เลือกได้หลายรูป)",
                                       "ติ๊กเลือกรูปที่ต้องการครอบตัด แล้วกดยืนยัน — ระบบจะดึงมาให้ครอบตัดทีละรูป")
        if not sel:
            self.log("ขั้นตอน 1.7: ยกเลิกการเลือก", "warning")
            return
        crop_list = []
        for f_path, files in sel.items():
            for f in files:
                crop_list.append((os.path.join(f_path, f), f_path, f))
        if not crop_list:
            return

        def task():
            self.set_running("phase1_7", True)
            self.log_threadsafe(f"ขั้นตอน 1.7: เริ่มครอบตัด {len(crop_list)} รูป...", "highlight")
            for i, (img_path, out_dir, filename) in enumerate(crop_list):
                self.log_threadsafe(f"ครอบตัด: {filename} ({i + 1}/{len(crop_list)})", "info")
                self.crop_done_event = threading.Event()
                self.root.after(0, lambda p=img_path, d=out_dir, n=filename, idx=i + 1, total=len(crop_list):
                                self.open_interactive_crop_ui(p, d, n, idx, total))
                self.crop_done_event.wait()
            self.set_running("phase1_7", False)
            self.mark_completed("1.7")
            self.log_threadsafe("ครอบตัดเสร็จสิ้น", "success")
        threading.Thread(target=task, daemon=True).start()

    def open_interactive_crop_ui(self, img_path, out_dir, filename, current, total):
        win = tk.Toplevel(self.root); win.title(f"CROP: {filename} ({current}/{total})")
        win.geometry("860x880"); win.grab_set(); win.configure(bg=self.colors["bg"])
        COMP, PV = 2000, 640

        try:
            base = Image.open(img_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"เปิดรูปไม่ได้: {e}", parent=win)
            win.destroy(); self.crop_done_event.set(); return

        st = {"scale": 1.0, "cx": COMP / 2, "cy": COMP / 2}
        scale_var = tk.DoubleVar(value=1.0)

        tk.Label(win, text=f"ครอบตัด & จัดตำแหน่ง — {filename}", bg=self.colors["bg"], fg=self.colors["accent"],
                 font=("Segoe UI", 13, "bold")).pack(pady=(12, 0))
        tk.Label(win, text="ลากเพื่อย้ายรูป · ล้อเมาส์หรือแถบเลื่อนเพื่อซูมเข้า/ออก",
                 bg=self.colors["bg"], fg=self.colors["text_dim"], font=("Segoe UI", 9)).pack(pady=(0, 6))

        bar = tk.Frame(win, bg=self.colors["bg_alt"]); bar.pack(side="bottom", fill="x")
        barin = tk.Frame(bar, bg=self.colors["bg_alt"]); barin.pack(fill="x", padx=20, pady=12)
        ctrl = tk.Frame(win, bg=self.colors["bg"]); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 6))

        canvas = tk.Canvas(win, width=PV, height=PV, bg="white", highlightthickness=1,
                           highlightbackground=self.colors["border"], cursor="fleur")
        canvas.pack(pady=8)

        bw, bh = base.size

        def build(size):
            s = size / COMP
            comp = Image.new('RGB', (size, size), (255, 255, 255))
            # COVER: ที่ scale=1 ด้านสั้นเต็มกรอบ ส่วนเกินถูกครอปออกจริง (ไม่เหลือขอบขาว)
            target = max(10.0, COMP * st["scale"] * s)
            r = target / min(bw, bh)
            nw, nh = max(1, int(bw * r)), max(1, int(bh * r))
            t = base.resize((nw, nh), Image.Resampling.LANCZOS)
            x = int(st["cx"] * s - nw / 2)
            y = int(st["cy"] * s - nh / 2)
            comp.paste(t, (x, y), t)
            return comp

        def refresh():
            canvas.delete("all")
            comp = build(PV)
            ph = ImageTk.PhotoImage(comp); canvas.image = ph
            canvas.create_image(0, 0, image=ph, anchor="nw")

        drag = {"x": 0, "y": 0}

        def on_press(e):
            drag["x"], drag["y"] = e.x, e.y

        def on_drag(e):
            f = COMP / PV
            st["cx"] += (e.x - drag["x"]) * f
            st["cy"] += (e.y - drag["y"]) * f
            drag["x"], drag["y"] = e.x, e.y
            refresh()

        def apply_scale(v):
            st["scale"] = max(0.1, min(3.0, v))
            refresh()

        def on_wheel(e):
            d = 1.1 if e.delta > 0 else 0.9
            apply_scale(st["scale"] * d)
            scale_var.set(round(st["scale"], 2))

        canvas.bind("<Button-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<MouseWheel>", on_wheel)

        tk.Label(ctrl, text="ZOOM", bg=self.colors["bg"], fg=self.colors["text"], width=6, anchor="w").pack(side="left")
        tk.Scale(ctrl, from_=0.1, to=3.0, resolution=0.05, variable=scale_var, orient="horizontal",
                 bg=self.colors["bg"], fg=self.colors["text"], highlightthickness=0,
                 troughcolor=self.colors["card"], command=lambda e: apply_scale(scale_var.get())).pack(
            side="left", fill="x", expand=True)

        def reset():
            st["scale"] = 1.0; st["cx"] = COMP / 2; st["cy"] = COMP / 2
            scale_var.set(1.0); refresh()
        tk.Button(ctrl, text="รีเซ็ต", command=reset, bg=self.colors["btn_default"], fg=self.colors["text"],
                  relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(10, 0))

        def save_and_next():
            build(COMP).save(img_path, "JPEG", quality=95, optimize=True)
            win.destroy(); self.crop_done_event.set()
        tk.Button(barin, text="บันทึก & ถัดไป →", command=save_and_next, bg=self.colors["success"], fg="#000",
                  font=("Segoe UI", 12, "bold"), padx=24, pady=8, relief="flat", cursor="hand2").pack(side="right")
        tk.Button(barin, text="ข้าม", command=lambda: [win.destroy(), self.crop_done_event.set()],
                  bg=self.colors["btn_default"], fg=self.colors["text"], relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=18, pady=8, cursor="hand2").pack(side="right", padx=(0, 10))

        win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), self.crop_done_event.set()])
        refresh()

    # ----------------------------- Phase 2: Rename & Primary -----------------------------
    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
        if not folders:
            messagebox.showinfo("Info", "ไม่พบโฟลเดอร์ กรุณาทำขั้นตอนที่ 0 หรือ 1 ก่อน")
            return

        def task():
            self.set_running("phase2", True)
            for i, folder_name in enumerate(folders):
                base_path = os.path.join(src, folder_name)
                files = sorted([f for f in os.listdir(base_path) if self.is_image_file(f)])
                if files:
                    self.root.after(0, lambda f=files, n=folder_name, b=base_path: self.process_rename_visual(b, f, n, b))
                self.set_progress_threadsafe((i + 1) / len(folders) * 100)
            self.mark_completed("2")
            self.set_running("phase2", False)
        threading.Thread(target=task, daemon=True).start()

    def process_rename_visual(self, work_dir, files, folder_name, base_path):
        main_file = self.choose_main_file_visual(work_dir, files, folder_name)
        if not main_file:
            return
        temp_dir = os.path.join(base_path, "_rename_temp")
        if os.path.exists(temp_dir):
            self.log(f"พบโฟลเดอร์ _rename_temp ของ {folder_name} อยู่แล้ว ข้ามเพื่อกันไฟล์กู้คืนถูกเขียนทับ", "error", "E007")
            return
        try:
            os.makedirs(temp_dir)
            planned_names = {}
            counter = 2
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                final = f"{folder_name}{ext}" if f == main_file else f"{folder_name}-{counter}{ext}"
                if f != main_file:
                    counter += 1
                planned_names[f] = final
            for f in files:
                shutil.move(os.path.join(base_path, f), os.path.join(temp_dir, f))
            for original, final in planned_names.items():
                final_path = os.path.join(base_path, final)
                if os.path.exists(final_path):
                    os.replace(final_path, os.path.join(temp_dir, f"existing_{final}"))
                shutil.copy2(os.path.join(temp_dir, original), final_path)
            shutil.rmtree(temp_dir)
            self.log(f"เปลี่ยนชื่อสำเร็จ: {folder_name}", "success")
        except Exception as e:
            self.log(f"เปลี่ยนชื่อไม่สำเร็จ {folder_name}: {e}. ไฟล์กู้คืนอยู่ใน _rename_temp", "error", "E007")

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1:
            return files[0]
        win = tk.Toplevel(self.root); win.title(f"เลือกรูปหลัก: {folder_name}")
        win.geometry("1000x750"); win.grab_set(); win.configure(bg=self.colors["bg"])
        res = tk.StringVar()
        tk.Label(win, text="เลือกรูปหลัก (PRIMARY PHOTO)", bg=self.colors["bg"], fg=self.colors["accent"],
                 font=("Segoe UI", 12, "bold")).pack(pady=10)
        can = tk.Canvas(win, bg=self.colors["bg"], highlightthickness=0); can.pack(side="left", fill="both", expand=True)
        gal = tk.Frame(can, bg=self.colors["bg"]); can.create_window((0, 0), window=gal, anchor="nw")
        photo_refs = []
        for i, f in enumerate(files):
            try:
                img = Image.open(os.path.join(folder_path, f)); img.thumbnail((160, 160))
                ph = ImageTk.PhotoImage(img); photo_refs.append(ph)
                lbl = tk.Label(gal, image=ph, bg=self.colors["card"], cursor="hand2")
                lbl.grid(row=i // 5, column=i % 5, padx=8, pady=8)
                lbl.bind("<Button-1>", lambda e, f=f: [res.set(f), win.destroy()])
            except Exception as e:
                self.log(f"ข้ามตัวอย่าง {f}: {e}", "warning")
        self.root.wait_window(win)
        return res.get() if res.get() else files[0]

    # ----------------------------- Phase 3: Collect to Database -----------------------------
    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start:03d}-{start + 199:03d}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]):
            messagebox.showwarning("Warning", "กรุณาตั้งค่า Photo 1 และ Photo 2 ในหน้า Settings")
            return
        missing = [p for p in [src, p1, p2] if not os.path.exists(p)]
        if missing:
            messagebox.showerror("Error", f"{self.error_codes['E005']}\n" + "\n".join(missing))
            return

        def task():
            self.set_running("phase3", True); s_c = 0
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
            for i, f_n in enumerate(folders):
                f_p = os.path.join(src, f_n)
                files_to_copy = [f for f in os.listdir(f_p) if f.startswith(f_n) and self.is_image_file(f)]
                if not files_to_copy:
                    continue
                p_t = self.type_mapping.get(f_n[0].upper(), "Other")
                m = re.search(r'(\d+)', f_n); r_v = int(m.group(1)) if m else 0
                t_r = os.path.join("Vincentio", p_t) if "-VN-" in f_n.upper() else os.path.join(p_t, f"{p_t} {self.get_range(r_v)}")
                for dest_base in [p1, p2]:
                    t_dir = os.path.join(dest_base, t_r)
                    try:
                        os.makedirs(t_dir, exist_ok=True)
                        for f in files_to_copy:
                            shutil.copy2(os.path.join(f_p, f), os.path.join(t_dir, f)); s_c += 1
                    except Exception as e:
                        self.log_threadsafe(f"Copy failed for {f_n} to {t_dir}: {e}", "error", "E007")
                self.set_progress_threadsafe((i + 1) / len(folders) * 100)
            self.log_threadsafe(f"ขั้นตอนที่ 3: เก็บไฟล์เข้าฐานข้อมูล {s_c} ไฟล์สำเร็จ", "success")
            self.mark_completed("3")
            self.set_running("phase3", False)
        threading.Thread(target=task, daemon=True).start()

    # ----------------------------- Phase 4: Archive -----------------------------
    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]) or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"]); return

        def task():
            self.set_running("phase4", True)
            now = datetime.now()
            path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
            os.makedirs(path, exist_ok=True)
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
            for f_n in folders:
                try:
                    shutil.move(os.path.join(src, f_n), os.path.join(path, f_n))
                except Exception as e:
                    self.log_threadsafe(f"Archive failed for {f_n}: {e}", "error", "E007")
            self.log_threadsafe("ขั้นตอนที่ 4: ย้ายเข้าคลังสำเร็จ", "success")
            self.mark_completed("4")
            self.set_running("phase4", False)
        threading.Thread(target=task, daemon=True).start()


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PixUpApp(root)
    root.mainloop()
