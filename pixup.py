import sys
import os

# --- Standardize output for Windows no-console mode ---
class NullWriter:
    def write(self, s): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

import customtkinter as ctk

import config
import theme as theme_mod
import pixup_workflow as workflow  # ชื่อไฟล์ workflow.py ชนกับ hook ของ PyInstaller จึงเปลี่ยนเป็น pixup_workflow
import dialogs

# Drag & drop (optional)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv')

VERSION = "2.4 Beta 1"

FONT = "Segoe UI"


def resource_path(rel):
    """หาเส้นทางไฟล์ทรัพยากร — รองรับทั้งรันสด และไฟล์ .exe (PyInstaller bundle)"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


class PixUpApp:
    def __init__(self, root):
        self.root = root
        # literal เพื่อให้ .github/workflows/build.yml grep เวอร์ชันได้ (อย่าเปลี่ยนเป็นตัวแปร)
        self.version = "2.4 Beta 1"
        self.root.title(f"PixUp v{self.version}")
        self.root.geometry("1140x800")
        self.root.minsize(980, 680)
        self._set_window_icon()

        self.error_codes = {
            "E001": "เส้นทางไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงไฟล์ (Permission Denied)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อ (Drive Offline)",
            "E007": "เกิดปัญหาขณะคัดลอก/ย้ายไฟล์",
            "E999": "เกิดข้อผิดพลาดภายในระบบ",
        }

        # โหลดการตั้งค่า
        self.settings = config.load_settings()
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar(value=self.settings.get("photo1", ""))
        self.photo2_dir = tk.StringVar(value=self.settings.get("photo2", ""))
        self.archive_dir = tk.StringVar(value=self.settings.get("archive", ""))
        self.camera_source = tk.StringVar(value=self.settings.get("camera_source", ""))
        self.chatgpt_url = tk.StringVar(value=self.settings.get("chatgpt_url", ""))
        self.chrome_profile_dir = tk.StringVar(value=self.settings.get("chrome_profile_dir", ""))
        self.type_mapping = dict(self.settings.get("types", config.DEFAULT_TYPES))
        self.sound_enabled = tk.BooleanVar(value=self.settings.get("sound_enabled", True))

        # ธีม (คงที่ ธีมเดียว — midnight + teal)
        self.theme_name = theme_mod.DEFAULT_THEME
        self.accent = theme_mod.DEFAULT_ACCENT
        self.colors = theme_mod.build_palette(self.theme_name, self.accent)

        # state
        self.ai_tasks = {}
        self.ai_cancel_event = threading.Event()
        self.is_running = {}
        self.completed_steps = set()
        self.current_step = "import"
        self.anim_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.anim_idx = 0
        self.count_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.log_visible = True
        self.ai_btn = None
        self._progress_max = 100

        # นิยามขั้นตอน
        self.steps = [
            {"id": "import", "no": "1", "emoji": "📥", "title": "นำเข้ารูปใหม่", "sub": "Import",
             "desc": "ดึงรูป/วิดีโอใหม่จากโฟลเดอร์กล้องอัตโนมัติ (เลือกโหมดได้) แล้วคัดลอกแยกตามรหัส 4 หลัก โดยไม่ลบต้นฉบับ",
             "action": lambda: workflow.phase_import(self)},
            {"id": "merge", "no": "2", "emoji": "🔗", "title": "รวมรูปต่างหู", "sub": "Merge",
             "desc": "เลือก 2 รูป/โฟลเดอร์ (หน้า/ข้าง) รวมเป็นรูปเดียวก่อน เพื่อส่งเข้า AI แค่รูปเดียว (ประหยัดโควต้า)",
             "action": lambda: workflow.phase_merge(self)},
            {"id": "crop", "no": "3", "emoji": "✂️", "title": "ครอบตัด", "sub": "Crop",
             "desc": "เลือกรูปแล้วครอบตัด/จัดตำแหน่งก่อนส่ง AI จะได้รีทัชเฉพาะส่วนที่จำเป็น",
             "action": lambda: workflow.phase_crop(self)},
            {"id": "ai", "no": "4", "emoji": "🤖", "title": "รีทัชด้วย AI", "sub": "AI Retouch",
             "desc": "เลือกรูป (ที่รวม/ครอปแล้ว) ส่งเข้า ChatGPT รีทัชอัตโนมัติ ดาวน์โหลดกลับเป็นไฟล์ _AI และขยายเท่าต้นฉบับ",
             "action": lambda: workflow.phase_ai(self)},
            {"id": "rename", "no": "5", "emoji": "🏷", "title": "เปลี่ยนชื่อ + เลือกรูปหลัก", "sub": "Rename",
             "desc": "ตั้งชื่อโฟลเดอร์เป็นรหัสสินค้าจริงก่อน แล้วเลือกรูปหลัก (ไฮไลต์รูป AI) ระบบจะเปลี่ยนชื่อไฟล์ทั้งหมดตามรหัสโฟลเดอร์",
             "action": lambda: workflow.phase_rename(self)},
            {"id": "collect", "no": "6", "emoji": "💾", "title": "เก็บเข้าฐานข้อมูล", "sub": "Collect",
             "desc": "พรีวิวทีละสินค้า เห็นรูปต้นทาง+ปลายทาง แล้วคัดลอกเฉพาะรูปหลักไป Photo 1/Photo 2 (ไม่สร้างโฟลเดอร์มั่ว)",
             "action": lambda: workflow.phase_collect(self)},
            {"id": "archive", "no": "7", "emoji": "📦", "title": "ย้ายเข้าคลัง", "sub": "Archive",
             "desc": "ย้ายทุกโฟลเดอร์ใน Workspace เข้าคลังเก็บประวัติ จัดเรียงตามปี/เดือน/วัน",
             "action": lambda: workflow.phase_archive(self)},
        ]
        for s in self.steps:
            self.is_running[s["id"]] = False
        self.step_widgets = {}

        self.build_ui()
        if HAS_DND:
            self._setup_dnd()
        self.root.after(120, self._animation_loop)
        self.root.after(800, self._auto_detect_downloads)

    # ===================== persistence wrappers =====================
    def _gather_settings(self):
        return {
            "photo1": self.photo1_dir.get(), "photo2": self.photo2_dir.get(),
            "archive": self.archive_dir.get(), "camera_source": self.camera_source.get(),
            "chatgpt_url": self.chatgpt_url.get(), "chrome_profile_dir": self.chrome_profile_dir.get(),
            "theme": self.theme_name, "accent": self.accent, "types": self.type_mapping,
            "sound_enabled": self.sound_enabled.get(),
        }

    def save_settings(self):
        config.save_settings(self._gather_settings())

    def load_manifest(self):
        return config.load_manifest()

    def save_manifest(self, m):
        config.save_manifest(m)

    # ===================== media helpers =====================
    def is_image_file(self, f):
        return f.lower().endswith(IMAGE_EXTENSIONS)

    def is_video_file(self, f):
        return f.lower().endswith(VIDEO_EXTENSIONS)

    def is_media_file(self, f):
        return self.is_image_file(f) or self.is_video_file(f)

    # ===================== logging =====================
    def log(self, message, category="info", code=None):
        ts = datetime.now().strftime("%H:%M:%S")
        tag = "info"; prefix = "• "
        if category == "error":
            tag = "error"; prefix = "✖ "
            if code and code in self.error_codes:
                message = f"[{code}] {message} -> {self.error_codes[code]}"
        elif category == "success" or "สำเร็จ" in message:
            tag = "success"; prefix = "✔ "
        elif category == "warning" or "ข้าม" in message:
            tag = "warning"; prefix = "⚠ "
        elif category == "highlight":
            tag = "highlight"; prefix = "✨ "
        try:
            tb = self.log_box
            tb.configure(state='normal')
            tb.insert(tk.END, f"[{ts}] ", "time")
            tb.insert(tk.END, f"{prefix}{message}\n", tag)
            tb.configure(state='disabled'); tb.see(tk.END)
        except (tk.TclError, AttributeError):
            pass
        config.append_history(f"[{ts}] {prefix}{message}\n")

    def log_threadsafe(self, message, category="info", code=None):
        self.root.after(0, lambda: self.log(message, category, code))

    def error(self, message, code=None):
        """แจ้ง error ทั้ง log + messagebox (เรียกจาก main thread)"""
        self.log(message, "error", code)
        messagebox.showerror("Error", message if not code else f"[{code}] {message}")

    def confirm(self, title, message):
        return messagebox.askyesno(title, message)

    # ===================== progress / running state =====================
    def set_progress_threadsafe(self, value, maximum=None):
        def upd():
            try:
                if maximum is not None:
                    self._progress_max = maximum if maximum else 100
                frac = value / self._progress_max if self._progress_max else 0.0
                self.progress.set(max(0.0, min(1.0, frac)))
            except (tk.TclError, AttributeError):
                pass
        self.root.after(0, upd)

    def set_count_threadsafe(self, cur, total):
        def upd():
            self.count_var.set(f"กำลังทำ {cur} จาก {total}" if total else "")
        self.root.after(0, upd)

    def set_running(self, phase, running):
        self.root.after(0, lambda: self.is_running.__setitem__(phase, running))

    def mark_completed(self, step_id):
        self.root.after(0, lambda: self.completed_steps.add(step_id))

    # ===================== AI button state =====================
    def ai_set_cancel_ui(self):
        def _do():
            try:
                if self.ai_btn and self.ai_btn.winfo_exists():
                    self.ai_btn.configure(text="■ ยกเลิก AI", fg_color=self.colors["error"],
                                          hover_color=self.colors["error"], text_color="#ffffff",
                                          command=self.cancel_ai, state="normal")
            except tk.TclError:
                pass
        self.root.after(0, _do)

    def ai_restore_ui(self):
        def _do():
            try:
                if self.ai_btn and self.ai_btn.winfo_exists():
                    st = next(s for s in self.steps if s["id"] == "ai")
                    self.ai_btn.configure(text=f"{st['emoji']}  เริ่ม{st['title']}",
                                          fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
                                          text_color=self.colors["on_accent"], command=st["action"], state="normal")
            except (tk.TclError, StopIteration):
                pass
        self.root.after(0, _do)

    def cancel_ai(self):
        self.ai_cancel_event.set()
        self.log("กำลังยกเลิก AI... จะหยุดหลังรูปปัจจุบันเสร็จ", "warning")
        try:
            if self.ai_btn and self.ai_btn.winfo_exists():
                self.ai_btn.configure(text="⌛ กำลังยกเลิก...", state="disabled")
        except tk.TclError:
            pass

    # ===================== UI build =====================
    def build_ui(self):
        c = self.colors
        self.root.configure(fg_color=c["bg"])

        self._build_header()
        # body: 3 คอลัมน์
        body = ctk.CTkFrame(self.root, fg_color=c["bg"], corner_radius=0)
        body.pack(fill="both", expand=True)
        self.left = ctk.CTkFrame(body, fg_color=c["panel"], width=210, corner_radius=0)
        self.left.pack(side="left", fill="y"); self.left.pack_propagate(False)
        self.right = ctk.CTkFrame(body, fg_color=c["panel"], width=258, corner_radius=0)
        self.right.pack(side="right", fill="y"); self.right.pack_propagate(False)
        self.center = ctk.CTkFrame(body, fg_color=c["bg"], corner_radius=0)
        self.center.pack(side="left", fill="both", expand=True)

        self._build_steps_column()
        self._build_footer()
        self.show_step(self.current_step)

    def _build_header(self):
        c = self.colors
        h = ctk.CTkFrame(self.root, fg_color=c["bg_alt"], height=64, corner_radius=0)
        h.pack(fill="x"); h.pack_propagate(False)

        brand = ctk.CTkFrame(h, fg_color="transparent")
        brand.pack(side="left", padx=(20, 0))
        try:
            from PIL import Image
            self._hdr_logo = ctk.CTkImage(Image.open(resource_path("logo.png")), size=(36, 36))
            ctk.CTkLabel(brand, image=self._hdr_logo, text="").pack(side="left", padx=(0, 11), pady=14)
        except Exception:
            pass
        wm = ctk.CTkFrame(brand, fg_color="transparent"); wm.pack(side="left")
        ctk.CTkLabel(wm, text="PixUp", text_color=c["text"],
                     font=(FONT, 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(wm, text=f"v{self.version}", text_color=c["text_mute"],
                     font=(FONT, 11)).pack(anchor="w", pady=(0, 2))

        ctk.CTkButton(h, text="⚙  ตั้งค่า", command=self.open_settings, width=90, height=34,
                      fg_color=c["card"], hover_color=c["card_hi"], text_color=c["text"],
                      corner_radius=8, font=(FONT, 12)).pack(side="right", padx=(8, 18))

    def _build_steps_column(self):
        c = self.colors
        ws = ctk.CTkFrame(self.left, fg_color="transparent")
        ws.pack(fill="x", padx=14, pady=(16, 8))
        ctk.CTkLabel(ws, text="WORKSPACE", text_color=c["text_mute"],
                     font=(FONT, 10, "bold")).pack(anchor="w")
        self.source_entry = ctk.CTkEntry(ws, textvariable=self.source_dir, font=("Consolas", 11),
                                         fg_color=c["input_bg"], border_width=0, height=32)
        self.source_entry.pack(fill="x", pady=(6, 6))
        ctk.CTkButton(ws, text="เลือกโฟลเดอร์", command=lambda: self.browse_dir(self.source_dir, False),
                      fg_color=c["card"], hover_color=c["card_hi"], text_color=c["text"],
                      height=30, corner_radius=8, font=(FONT, 12)).pack(fill="x")

        ctk.CTkLabel(self.left, text="ขั้นตอน", text_color=c["text_mute"],
                     font=(FONT, 10, "bold")).pack(anchor="w", padx=18, pady=(14, 6))
        for s in self.steps:
            btn = ctk.CTkButton(self.left, text=f"  {s['no']}   {s['emoji']} {s['title']}",
                                anchor="w", fg_color="transparent", text_color=c["text_dim"],
                                hover_color=c["card_hi"], corner_radius=8, height=40,
                                font=(FONT, 13), command=lambda sid=s["id"]: self.show_step(sid))
            btn.pack(fill="x", padx=10, pady=2)
            self.step_widgets[s["id"]] = btn

    def _build_footer(self):
        c = self.colors
        wrap = ctk.CTkFrame(self.root, fg_color=c["bg"], corner_radius=0)
        wrap.pack(side="bottom", fill="x")
        prow = ctk.CTkFrame(wrap, fg_color="transparent")
        prow.pack(fill="x", padx=18, pady=(8, 2))
        self.progress = ctk.CTkProgressBar(prow, progress_color=c["accent"], fg_color=c["card"],
                                           height=10, corner_radius=5)
        self.progress.set(0)
        self.progress.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(prow, textvariable=self.count_var, text_color=c["accent"],
                     font=(FONT, 12, "bold"), width=150, anchor="e").pack(side="right", padx=(8, 0))

        head = ctk.CTkFrame(wrap, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(2, 0))
        ctk.CTkLabel(head, text="ACTIVITY LOG", text_color=c["text_mute"],
                     font=(FONT, 10, "bold")).pack(side="left")
        self.log_toggle = ctk.CTkButton(head, text="▾ ซ่อน", command=self.toggle_log,
                                        fg_color="transparent", hover_color=c["card"], text_color=c["text_dim"],
                                        width=70, height=24, font=(FONT, 11))
        self.log_toggle.pack(side="right")
        self.log_area = ctk.CTkTextbox(wrap, height=210, fg_color=c["input_bg"], text_color=c["text_dim"],
                                       font=("Consolas", 12), corner_radius=8, border_width=0)
        self.log_area.pack(fill="both", expand=True, padx=18, pady=(6, 12))
        self.log_box = self.log_area._textbox
        self.log_box.tag_config("time", foreground=c["text_mute"])
        self.log_box.tag_config("success", foreground=c["success"])
        self.log_box.tag_config("error", foreground=c["error"])
        self.log_box.tag_config("warning", foreground=c["warning"])
        self.log_box.tag_config("highlight", foreground=c["highlight"])
        self.log_box.tag_config("info", foreground=c["text"])
        self.log_box.configure(state='disabled')

    def toggle_log(self):
        if self.log_visible:
            self.log_area.pack_forget(); self.log_toggle.configure(text="▸ แสดง")
        else:
            self.log_area.pack(fill="both", expand=True, padx=18, pady=(6, 12))
            self.log_toggle.configure(text="▾ ซ่อน")
        self.log_visible = not self.log_visible

    # ===================== step navigation =====================
    def show_step(self, step_id):
        self.current_step = step_id
        self._render_steps_state()
        self._render_center(step_id)
        self._render_panel(step_id)

    def _render_steps_state(self):
        c = self.colors
        for s in self.steps:
            btn = self.step_widgets.get(s["id"])
            if not btn:
                continue
            active = (s["id"] == self.current_step)
            done = (s["id"] in self.completed_steps)
            mark = "✓" if done else s["no"]
            text = f"  {mark}   {s['emoji']} {s['title']}"
            if active:
                btn.configure(text=text, fg_color=c["accent"], text_color=c["on_accent"],
                              hover_color=c["accent_hover"])
            else:
                tcol = c["text"] if done else c["text_dim"]
                btn.configure(text=text, fg_color="transparent", text_color=tcol,
                              hover_color=c["card_hi"])

    def _render_center(self, step_id):
        c = self.colors
        for w in self.center.winfo_children():
            w.destroy()
        s = next(x for x in self.steps if x["id"] == step_id)
        card = ctk.CTkFrame(self.center, fg_color=c["card"], corner_radius=14,
                            border_width=1, border_color=c["border"])
        card.pack(fill="both", expand=True, padx=22, pady=20)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=34, pady=30)

        head = ctk.CTkFrame(inner, fg_color="transparent"); head.pack(anchor="w", fill="x")
        ctk.CTkLabel(head, text=f" ขั้นที่ {s['no']} ", fg_color=c["accent"], text_color=c["on_accent"],
                     font=(FONT, 12, "bold"), corner_radius=6).pack(side="left", ipady=1)
        ctk.CTkLabel(head, text=s["sub"].upper(), text_color=c["text_mute"],
                     font=(FONT, 11, "bold")).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(inner, text=f"{s['emoji']}  {s['title']}", text_color=c["text"],
                     font=(FONT, 24, "bold")).pack(anchor="w", pady=(14, 0))
        ctk.CTkLabel(inner, text=s["desc"], text_color=c["text_dim"], font=(FONT, 13),
                     wraplength=540, justify="left").pack(anchor="w", pady=(10, 0))

        btn = ctk.CTkButton(inner, text=f"{s['emoji']}  เริ่ม{s['title']}", command=s["action"],
                            fg_color=c["accent"], hover_color=c["accent_hover"], text_color=c["on_accent"],
                            height=48, corner_radius=10, font=(FONT, 15, "bold"))
        btn.pack(fill="x", pady=(26, 0))
        if step_id == "ai":
            self.ai_btn = btn

        ctk.CTkLabel(inner, textvariable=self.status_var, text_color=c["accent"],
                     font=("Consolas", 13, "bold")).pack(anchor="w", pady=(14, 0))

        nav = ctk.CTkFrame(inner, fg_color="transparent"); nav.pack(side="bottom", fill="x", pady=(18, 0))
        ids = [x["id"] for x in self.steps]; i = ids.index(step_id)
        if i > 0:
            ctk.CTkButton(nav, text="‹ ก่อนหน้า", command=lambda: self.show_step(ids[i - 1]),
                          fg_color=c["card_hi"], hover_color=c["btn_hover"], text_color=c["text"],
                          width=110, height=34, corner_radius=8, font=(FONT, 12)).pack(side="left")
        if i < len(ids) - 1:
            ctk.CTkButton(nav, text="ถัดไป ›", command=lambda: self.show_step(ids[i + 1]),
                          fg_color=c["card_hi"], hover_color=c["btn_hover"], text_color=c["text"],
                          width=110, height=34, corner_radius=8, font=(FONT, 12)).pack(side="right")

    def _render_panel(self, step_id):
        c = self.colors
        for w in self.right.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.right, text="ตัวเลือก", text_color=c["text_mute"],
                     font=(FONT, 10, "bold")).pack(anchor="w", padx=18, pady=(18, 6))

        def panel_card(title):
            f = ctk.CTkFrame(self.right, fg_color=c["card"], corner_radius=12)
            f.pack(fill="x", padx=14, pady=6)
            ctk.CTkLabel(f, text=title, text_color=c["text_dim"],
                         font=(FONT, 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            return f

        def pbtn(parent, text, cmd):
            ctk.CTkButton(parent, text=text, command=cmd, fg_color=c["btn_default"],
                          hover_color=c["btn_hover"], text_color=c["text"], anchor="w",
                          height=32, corner_radius=8, font=(FONT, 12)).pack(fill="x", padx=10, pady=3)

        acts = panel_card("เปิดโฟลเดอร์ & เครื่องมือ")
        if step_id == "import":
            pbtn(acts, "📷  เปิดโฟลเดอร์กล้อง", lambda: self.open_folder(self.camera_source.get()))
            pbtn(acts, "📂  เปิด Workspace", lambda: self.open_folder(self.source_dir.get()))
            pbtn(acts, "🗂  จัดกลุ่มตามรหัส", lambda: workflow.phase_group(self))
            pbtn(acts, "🧹  ล้างความจำการนำเข้า", self.reset_import_memory)
        elif step_id == "collect":
            pbtn(acts, "🗄  เปิด Photo 1", lambda: self.open_folder(self.photo1_dir.get()))
            pbtn(acts, "🗄  เปิด Photo 2", lambda: self.open_folder(self.photo2_dir.get()))
            pbtn(acts, "📂  เปิด Workspace", lambda: self.open_folder(self.source_dir.get()))
        elif step_id == "ai":
            pbtn(acts, "📂  เปิด Workspace", lambda: self.open_folder(self.source_dir.get()))
            pbtn(acts, "⚙  ตั้งค่า ChatGPT", self.open_settings)
        elif step_id == "archive":
            pbtn(acts, "📦  เปิดคลัง", lambda: self.open_folder(self.archive_dir.get()))
            pbtn(acts, "📂  เปิด Workspace", lambda: self.open_folder(self.source_dir.get()))
        else:  # merge, crop, rename
            pbtn(acts, "📂  เปิด Workspace", lambda: self.open_folder(self.source_dir.get()))
        ctk.CTkFrame(acts, fg_color="transparent", height=4).pack()  # ระยะล่าง

        info = panel_card("คำแนะนำ")
        tips = {
            "import": "ตั้งโฟลเดอร์กล้องในหน้า ⚙ ก่อน • โหมด 'ดึงเฉพาะใหม่' จะไม่ดึงซ้ำ • จัดกลุ่มตามรหัส = แยกไฟล์หลวมเข้าโฟลเดอร์",
            "merge": "เลือก 2 รูปต่อโฟลเดอร์ • ลาก/ซูมในกรอบ • ส่วนเกินกรอบถูกครอป",
            "crop": "เลือกได้หลายรูป • ลากเพื่อย้าย ล้อเมาส์เพื่อซูม",
            "ai": "ควรรวม/ครอปก่อน • ล็อกอิน ChatGPT ครั้งเดียว • กดปุ่มอีกครั้งเพื่อยกเลิกระหว่างทำ",
            "rename": "ตั้งชื่อโฟลเดอร์เป็นรหัสสินค้าจริงก่อน • รูปกรอบเขียว = ผ่าน AI แนะนำเลือกเป็นรูปหลัก",
            "collect": "พรีวิวทีละสินค้า เห็นรูปปลายทาง • เลือกแทน/ไม่แทน/ข้าม • ไม่พบหมวด=ข้าม",
            "archive": "ย้าย (ไม่ใช่คัดลอก) ทุกโฟลเดอร์เข้าคลังตามวันที่",
        }
        ctk.CTkLabel(info, text=tips.get(step_id, ""), text_color=c["text_dim"],
                     font=(FONT, 12), wraplength=205, justify="left").pack(anchor="w", padx=12, pady=(0, 12))

    # ===================== animation =====================
    def _animation_loop(self):
        self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
        spin = self.anim_chars[self.anim_idx]
        running_now = False
        for s in self.steps:
            btn = self.step_widgets.get(s["id"])
            if not btn:
                continue
            if self.is_running.get(s["id"]):
                running_now = True
                try:
                    btn.configure(text=f"  {spin}   {s['emoji']} {s['title']}",
                                  fg_color=self.colors["accent"], text_color=self.colors["on_accent"])
                except tk.TclError:
                    pass
        if running_now:
            self.status_var.set(f"{spin}  กำลังทำงาน...")
        else:
            self.status_var.set("")
            self._render_steps_state()
        self.root.after(120, self._animation_loop)

    # ===================== window icon =====================
    def _set_window_icon(self):
        """ตั้งไอคอนหน้าต่าง (title bar + taskbar) — รองรับทั้งรันสดและ .exe"""
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KHCreation.PixUp")
            except Exception:
                pass
            # CTk รีเซ็ต iconbitmap ตอนเริ่ม → ตั้งหลัง delay ให้ชนะ
            self.root.after(280, lambda: self._try(lambda: self.root.iconbitmap(resource_path("app_icon.ico"))))
        try:
            from PIL import Image, ImageTk
            self._icon_img = ImageTk.PhotoImage(Image.open(resource_path("logo.png")))
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    @staticmethod
    def _try(fn):
        try:
            fn()
        except Exception:
            pass

    # ===================== sound notification =====================
    def play_done_sound(self):
        """เล่นเสียงแจ้งเตือนเมื่อขั้นที่ใช้เวลานานเสร็จ (เรียกจาก thread ไหนก็ได้)"""
        try:
            if not self.sound_enabled.get():
                return
        except tk.TclError:
            return

        def _play():
            try:
                if sys.platform == "darwin":
                    os.system('afplay /System/Library/Sounds/Glass.aiff >/dev/null 2>&1')
                elif sys.platform.startswith("win"):
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    self.root.after(0, self.root.bell)
            except Exception:
                try:
                    self.root.after(0, self.root.bell)
                except Exception:
                    pass
        threading.Thread(target=_play, daemon=True).start()

    # ===================== misc actions =====================
    def open_folder(self, path):
        if not path or not os.path.exists(path):
            self.log("ไม่พบโฟลเดอร์ที่จะเปิด", "warning"); return
        try:
            if sys.platform == "darwin":
                os.system(f'open "{path}"')
            elif sys.platform.startswith("win"):
                os.startfile(path)  # noqa
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self.log(f"เปิดโฟลเดอร์ไม่ได้: {e}", "error")

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d:
            var.set(os.path.normpath(d))
        if is_config:
            self.save_settings()

    def _setup_dnd(self):
        try:
            w = getattr(self.source_entry, "_entry", self.source_entry)
            w.drop_target_register(DND_FILES)
            w.dnd_bind('<<Drop>>', self._handle_drop)
        except Exception:
            pass

    def _handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"Drag & Drop: {path}", "success")

    def _auto_detect_downloads(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads):
            return
        cands = [d for d in os.listdir(downloads)
                 if os.path.isdir(os.path.join(downloads, d)) and d.lower().startswith("media -")]
        if not cands:
            return
        cands.sort(key=lambda x: os.path.getctime(os.path.join(downloads, x)), reverse=True)
        latest = os.path.join(downloads, cands[0])
        if latest != self.source_dir.get():
            if messagebox.askyesno("New Workspace", f"ใช้โฟลเดอร์ล่าสุดนี้เป็น Workspace?\n{cands[0]}"):
                self.source_dir.set(latest)

    def reset_import_memory(self):
        if messagebox.askyesno("ยืนยัน", "ล้างความจำการนำเข้าทั้งหมด?\nครั้งหน้าโหมด 'ดึงเฉพาะใหม่' จะดึงรูปเก่ามาใหม่"):
            try:
                config.reset_manifest()
                self.log("ล้างความจำการนำเข้าแล้ว", "success")
            except Exception as e:
                self.log(f"ล้างไม่สำเร็จ: {e}", "error")

    # ===================== settings window =====================
    def open_settings(self):
        c = self.colors
        win = ctk.CTkToplevel(self.root); win.title("ตั้งค่า / Settings")
        win.geometry("640x720"); win.configure(fg_color=c["bg"])
        win.after(120, win.grab_set)
        ctk.CTkLabel(win, text="⚙  SETTINGS", text_color=c["accent"],
                     font=(FONT, 18, "bold")).pack(anchor="w", padx=24, pady=(20, 8))

        def save_close():
            self.save_settings(); win.destroy(); self.log("บันทึกการตั้งค่าแล้ว", "success")
        ctk.CTkButton(win, text="บันทึก & ปิด", command=save_close, fg_color=c["accent"],
                      hover_color=c["accent_hover"], text_color=c["on_accent"], height=44,
                      corner_radius=10, font=(FONT, 14, "bold")).pack(side="bottom", fill="x", padx=24, pady=16)

        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18)

        self._path_card(body, "PHOTO 1 — MAIN DATABASE", self.photo1_dir)
        self._path_card(body, "PHOTO 2 — BACKUP DATABASE", self.photo2_dir)
        self._path_card(body, "ARCHIVE — คลังเก็บประวัติ", self.archive_dir)
        self._path_card(body, "โฟลเดอร์กล้อง (Camera Source)", self.camera_source)
        self._path_card(body, "CHROME PROFILE (ขั้นสูง · เว้นว่าง = โปรไฟล์ PixUp)", self.chrome_profile_dir)

        cg = ctk.CTkFrame(body, fg_color=c["card"], corner_radius=12); cg.pack(fill="x", pady=6)
        ctk.CTkLabel(cg, text="CHATGPT CUSTOM GPT URL (เว้นว่าง = chatgpt.com ปกติ)", text_color=c["highlight"],
                     font=(FONT, 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkEntry(cg, textvariable=self.chatgpt_url, font=("Consolas", 12), fg_color=c["input_bg"],
                     border_width=0, height=34).pack(fill="x", padx=12, pady=(0, 12))

        snd = ctk.CTkFrame(body, fg_color=c["card"], corner_radius=12); snd.pack(fill="x", pady=6)
        ctk.CTkSwitch(snd, text="🔔  เปิดเสียงแจ้งเตือนเมื่อขั้นที่ใช้เวลานานเสร็จ", variable=self.sound_enabled,
                      onvalue=True, offvalue=False, command=self.save_settings,
                      progress_color=c["accent"], font=(FONT, 12)).pack(anchor="w", padx=14, pady=14)

        tools = ctk.CTkFrame(body, fg_color=c["card"], corner_radius=12); tools.pack(fill="x", pady=6)
        ctk.CTkLabel(tools, text="🛠  เครื่องมือ", text_color=c["text_dim"],
                     font=(FONT, 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        def tool(text, cmd):
            ctk.CTkButton(tools, text=text, command=cmd, fg_color=c["btn_default"], hover_color=c["btn_hover"],
                          text_color=c["text"], anchor="w", height=32, corner_radius=8,
                          font=(FONT, 12)).pack(fill="x", padx=10, pady=3)
        tool("🏷  จัดการหมวดหมู่สินค้า (R/N/E ...)", lambda: [win.destroy(), self.open_category_manager()])
        tool("🧹  ล้างความจำการนำเข้า", self.reset_import_memory)
        tool("📜  เปิดโฟลเดอร์ Log", lambda: self.open_folder(config.CONFIG_DIR))
        ctk.CTkFrame(tools, fg_color="transparent", height=4).pack()

    def _path_card(self, parent, label, var):
        c = self.colors
        card = ctk.CTkFrame(parent, fg_color=c["card"], corner_radius=12); card.pack(fill="x", pady=5)
        ctk.CTkLabel(card, text=label, text_color=c["text_dim"],
                     font=(FONT, 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkEntry(row, textvariable=var, font=("Consolas", 12), fg_color=c["input_bg"],
                     border_width=0, height=34).pack(side="left", expand=True, fill="x")
        ctk.CTkButton(row, text="...", command=lambda: self.browse_dir(var, True), width=40, height=34,
                      fg_color=c["btn_default"], hover_color=c["btn_hover"], text_color=c["text"],
                      corner_radius=8).pack(side="right", padx=(8, 0))

    def open_category_manager(self):
        c = self.colors
        m = ctk.CTkToplevel(self.root); m.title("Categories"); m.geometry("520x600")
        m.configure(fg_color=c["bg"]); m.after(120, m.grab_set)
        ctk.CTkLabel(m, text="🏷  จัดการหมวดหมู่สินค้า", text_color=c["accent"],
                     font=(FONT, 16, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(m, text="ตัวอักษรนำหน้ารหัสโฟลเดอร์ → ประเภท (เช่น R = Ring)", text_color=c["text_dim"],
                     font=(FONT, 11)).pack(anchor="w", padx=20)

        # ตาราง (ttk.Treeview สไตล์เข้ม)
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("Cat.Treeview", background=c["input_bg"], fieldbackground=c["input_bg"],
                        foreground=c["text"], rowheight=28, borderwidth=0)
        style.configure("Cat.Treeview.Heading", background=c["card"], foreground=c["text_dim"], borderwidth=0)
        tree = ttk.Treeview(m, columns=("C", "N"), show="headings", height=12, style="Cat.Treeview")
        tree.heading("C", text="Code"); tree.heading("N", text="Name")
        tree.column("C", width=120); tree.column("N", width=320)
        tree.pack(padx=20, pady=10, fill="both", expand=True)

        def refresh():
            for i in tree.get_children():
                tree.delete(i)
            for code, name in sorted(self.type_mapping.items()):
                tree.insert("", "end", values=(code, name))
        refresh()

        ctrl = ctk.CTkFrame(m, fg_color="transparent"); ctrl.pack(fill="x", padx=20, pady=(0, 6))
        c_e = ctk.CTkEntry(ctrl, width=80, placeholder_text="Code", font=("Consolas", 12))
        c_e.pack(side="left")
        n_e = ctk.CTkEntry(ctrl, placeholder_text="ชื่อประเภท", font=(FONT, 12))
        n_e.pack(side="left", fill="x", expand=True, padx=8)

        def add():
            code, name = c_e.get().strip().upper(), n_e.get().strip()
            if code and name:
                self.type_mapping[code] = name; self.save_settings(); refresh()
                c_e.delete(0, 100); n_e.delete(0, 100)
        ctk.CTkButton(ctrl, text="เพิ่ม", command=add, width=64, fg_color=c["accent"],
                      hover_color=c["accent_hover"], text_color=c["on_accent"], font=(FONT, 12, "bold")).pack(side="right")

        def delete():
            sel = tree.selection()
            if sel:
                code = str(tree.item(sel[0])['values'][0])
                if messagebox.askyesno("Confirm", f"ลบ '{code}'?"):
                    self.type_mapping.pop(code, None); self.save_settings(); refresh()
        ctk.CTkButton(m, text="ลบที่เลือก", command=delete, fg_color=c["error"], hover_color=c["error"],
                      text_color="#ffffff", height=38, corner_radius=8,
                      font=(FONT, 13, "bold")).pack(fill="x", padx=20, pady=(4, 16))


def make_root():
    """สร้างหน้าต่างหลัก CustomTkinter + รองรับ Drag&Drop ถ้ามี"""
    ctk.set_appearance_mode("dark")
    if HAS_DND:
        try:
            class _Root(ctk.CTk, TkinterDnD.DnDWrapper):
                def __init__(self):
                    super().__init__()
                    self.TkdndVersion = TkinterDnD._require(self)
            return _Root()
        except Exception:
            pass
    return ctk.CTk()


if __name__ == "__main__":
    root = make_root()
    app = PixUpApp(root)
    root.mainloop()
