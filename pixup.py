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
from tkinter import filedialog, messagebox, scrolledtext, ttk, colorchooser
from datetime import datetime

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

VERSION = "2.3 Beta 2"


class PixUpApp:
    def __init__(self, root):
        self.root = root
        # literal เพื่อให้ .github/workflows/build.yml grep เวอร์ชันได้ (อย่าเปลี่ยนเป็นตัวแปร)
        self.version = "2.3 Beta 2"
        self.root.title(f"PixUp v{self.version}")
        self.root.geometry("1320x900")
        self.root.minsize(1100, 720)

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

        # ธีม
        self.theme_name = self.settings.get("theme", theme_mod.DEFAULT_THEME)
        self.accent = self.settings.get("accent", theme_mod.DEFAULT_ACCENT)
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

        # นิยามขั้นตอน (ลำดับใหม่)
        self.steps = [
            {"id": "import", "no": "1", "emoji": "📥", "title": "นำเข้ารูปใหม่", "sub": "Import",
             "desc": "ดึงรูป/วิดีโอใหม่จากโฟลเดอร์กล้องอัตโนมัติ (เลือกโหมดได้) แล้วคัดลอกแยกตามรหัส 4 หลัก โดยไม่ลบต้นฉบับ",
             "action": lambda: workflow.phase_import(self), "color": "accent"},
            {"id": "merge", "no": "2", "emoji": "🔗", "title": "รวมรูปต่างหู", "sub": "Merge",
             "desc": "เลือก 2 รูป/โฟลเดอร์ (หน้า/ข้าง) รวมเป็นรูปเดียวก่อน เพื่อส่งเข้า AI แค่รูปเดียว (ประหยัดโควต้า)",
             "action": lambda: workflow.phase_merge(self), "color": "purple"},
            {"id": "crop", "no": "3", "emoji": "✂️", "title": "ครอบตัด", "sub": "Crop",
             "desc": "เลือกรูปแล้วครอบตัด/จัดตำแหน่งก่อนส่ง AI จะได้รีทัชเฉพาะส่วนที่จำเป็น",
             "action": lambda: workflow.phase_crop(self), "color": "orange"},
            {"id": "ai", "no": "4", "emoji": "🤖", "title": "รีทัชด้วย AI", "sub": "AI Retouch",
             "desc": "เลือกรูป (ที่รวม/ครอปแล้ว) ส่งเข้า ChatGPT รีทัชอัตโนมัติ ดาวน์โหลดกลับเป็นไฟล์ _AI และขยายเท่าต้นฉบับ",
             "action": lambda: workflow.phase_ai(self), "color": "highlight"},
            {"id": "rename", "no": "5", "emoji": "🏷", "title": "เปลี่ยนชื่อ + เลือกรูปหลัก", "sub": "Rename",
             "desc": "เลือกรูปหลัก (ไฮไลต์รูป AI) แล้วเปลี่ยนชื่อไฟล์ทั้งหมดตามรหัสโฟลเดอร์ (รวมวิดีโอ)",
             "action": lambda: workflow.phase_rename(self), "color": "highlight"},
            {"id": "collect", "no": "6", "emoji": "💾", "title": "เก็บเข้าฐานข้อมูล", "sub": "Collect",
             "desc": "พรีวิวรูปหลัก + ปลายทาง แล้วคัดลอกเฉพาะรูปหลักไป Photo 1/Photo 2 (ไม่สร้างโฟลเดอร์มั่ว)",
             "action": lambda: workflow.phase_collect(self), "color": "highlight"},
            {"id": "archive", "no": "7", "emoji": "📦", "title": "ย้ายเข้าคลัง", "sub": "Archive",
             "desc": "ย้ายทุกโฟลเดอร์ใน Workspace เข้าคลังเก็บประวัติ จัดเรียงตามปี/เดือน/วัน",
             "action": lambda: workflow.phase_archive(self), "color": "highlight"},
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
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"[{ts}] ", "time")
            self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
            self.log_area.configure(state='disabled'); self.log_area.see(tk.END)
        except tk.TclError:
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
                    self.progress['maximum'] = maximum if maximum else 100
                self.progress['value'] = value
            except tk.TclError:
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
                    self.ai_btn.config(text="■ ยกเลิก AI", bg=self.colors["error"], fg="#ffffff",
                                       command=self.cancel_ai, state="normal")
            except tk.TclError:
                pass
        self.root.after(0, _do)

    def ai_restore_ui(self):
        def _do():
            try:
                if self.ai_btn and self.ai_btn.winfo_exists():
                    st = next(s for s in self.steps if s["id"] == "ai")
                    self.ai_btn.config(text=f"{st['emoji']}  เริ่ม{st['title']}",
                                       bg=self.colors[st["color"]], fg=self.colors["on_accent"],
                                       command=st["action"], state="normal")
            except (tk.TclError, StopIteration):
                pass
        self.root.after(0, _do)

    def cancel_ai(self):
        self.ai_cancel_event.set()
        self.log("กำลังยกเลิก AI... จะหยุดหลังรูปปัจจุบันเสร็จ", "warning")
        try:
            if self.ai_btn and self.ai_btn.winfo_exists():
                self.ai_btn.config(text="⌛ กำลังยกเลิก...", state="disabled")
        except tk.TclError:
            pass

    # ===================== UI build =====================
    def build_ui(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("PixUp.Horizontal.TProgressbar", troughcolor=c["card"],
                        background=c["accent"], thickness=10, borderwidth=0)

        self._build_header()
        # body: 3 คอลัมน์
        body = tk.Frame(self.root, bg=c["bg"]); body.pack(fill="both", expand=True)
        self.left = tk.Frame(body, bg=c["panel"], width=230); self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        self.right = tk.Frame(body, bg=c["panel"], width=300); self.right.pack(side="right", fill="y")
        self.right.pack_propagate(False)
        self.center = tk.Frame(body, bg=c["bg"]); self.center.pack(side="left", fill="both", expand=True)

        self._build_steps_column()
        self._build_footer()       # progress + log (อยู่ล่างของ root)
        self.show_step(self.current_step)

    def _build_header(self):
        c = self.colors
        h = tk.Frame(self.root, bg=c["bg_alt"], height=70); h.pack(fill="x"); h.pack_propagate(False)
        tk.Label(h, text="PIXUP", bg=c["bg_alt"], fg=c["accent"],
                 font=("Segoe UI", 22, "bold")).pack(side="left", padx=(24, 6), pady=14)
        tk.Label(h, text=f"KH CREATION  ·  v{self.version}", bg=c["bg_alt"], fg=c["text_mute"],
                 font=("Segoe UI", 8, "bold")).pack(side="left", pady=(26, 0))

        tk.Button(h, text="⚙", command=self.open_settings, bg=c["bg_alt"], fg=c["text_dim"],
                  relief="flat", font=("Segoe UI", 18), activebackground=c["bg_alt"],
                  activeforeground=c["accent"], cursor="hand2").pack(side="right", padx=(8, 20))
        # theme selector
        self.theme_var = tk.StringVar(value=self.theme_name)
        tm = ttk.Combobox(h, textvariable=self.theme_var, values=list(theme_mod.THEMES.keys()),
                          width=10, state="readonly")
        tm.pack(side="right", padx=4, pady=20)
        tm.bind("<<ComboboxSelected>>", lambda e: self.change_theme(self.theme_var.get()))
        tk.Button(h, text="● สี", command=self.pick_accent, bg=c["bg_alt"], fg=c["accent"],
                  relief="flat", font=("Segoe UI", 11, "bold"), activebackground=c["bg_alt"],
                  cursor="hand2").pack(side="right", padx=4)

    def _build_steps_column(self):
        c = self.colors
        # workspace selector อยู่บนสุดของคอลัมน์ซ้าย
        ws = tk.Frame(self.left, bg=c["panel"]); ws.pack(fill="x", padx=14, pady=(16, 8))
        tk.Label(ws, text="WORKSPACE", bg=c["panel"], fg=c["text_mute"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.source_entry = tk.Entry(ws, textvariable=self.source_dir, font=("Consolas", 8),
                                     bg=c["input_bg"], fg=c["text"], relief="flat", insertbackground="white")
        self.source_entry.pack(fill="x", ipady=4, pady=(4, 4))
        tk.Button(ws, text="เลือกโฟลเดอร์", command=lambda: self.browse_dir(self.source_dir, False),
                  bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 8),
                  cursor="hand2").pack(fill="x")

        tk.Label(self.left, text="STEPS", bg=c["panel"], fg=c["text_mute"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=16, pady=(10, 4))
        for s in self.steps:
            row = tk.Frame(self.left, bg=c["panel"], cursor="hand2")
            row.pack(fill="x", padx=8, pady=2)
            badge = tk.Label(row, text=s["no"], width=3, bg=c["card"], fg=c["text_dim"],
                             font=("Segoe UI", 11, "bold"))
            badge.pack(side="left", padx=(4, 8), pady=6)
            txt = tk.Label(row, text=f"{s['emoji']} {s['title']}", bg=c["panel"], fg=c["text_dim"],
                           font=("Segoe UI", 9), anchor="w", justify="left")
            txt.pack(side="left", fill="x", expand=True)
            for w in (row, badge, txt):
                w.bind("<Button-1>", lambda e, sid=s["id"]: self.show_step(sid))
            self.step_widgets[s["id"]] = {"row": row, "badge": badge, "txt": txt}

    def _build_footer(self):
        c = self.colors
        wrap = tk.Frame(self.root, bg=c["bg"]); wrap.pack(side="bottom", fill="x")
        prow = tk.Frame(wrap, bg=c["bg"]); prow.pack(fill="x", padx=16, pady=(6, 2))
        self.progress = ttk.Progressbar(prow, orient="horizontal", mode="determinate",
                                        style="PixUp.Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True)
        tk.Label(prow, textvariable=self.count_var, bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold"), width=20, anchor="e").pack(side="right", padx=(8, 0))

        head = tk.Frame(wrap, bg=c["bg"]); head.pack(fill="x", padx=16)
        tk.Label(head, text="ACTIVITY LOG", bg=c["bg"], fg=c["text_mute"],
                 font=("Segoe UI", 7, "bold")).pack(side="left")
        self.log_toggle = tk.Button(head, text="▾ ซ่อน", command=self.toggle_log, bg=c["bg"],
                                    fg=c["text_dim"], relief="flat", font=("Segoe UI", 8),
                                    cursor="hand2", activebackground=c["bg"])
        self.log_toggle.pack(side="right")
        self.log_area = scrolledtext.ScrolledText(wrap, height=8, bg=c["input_bg"], fg=c["text_dim"],
                                                  font=("Consolas", 9), relief="flat", padx=12, pady=8)
        self.log_area.pack(fill="x", padx=16, pady=(4, 10))
        self.log_area.tag_config("time", foreground=c["text_mute"])
        self.log_area.tag_config("success", foreground=c["success"])
        self.log_area.tag_config("error", foreground=c["error"])
        self.log_area.tag_config("warning", foreground=c["warning"])
        self.log_area.tag_config("highlight", foreground=c["highlight"])
        self.log_area.tag_config("info", foreground=c["text"])
        self.log_area.configure(state='disabled')

    def toggle_log(self):
        if self.log_visible:
            self.log_area.pack_forget(); self.log_toggle.config(text="▸ แสดง")
        else:
            self.log_area.pack(fill="x", padx=16, pady=(4, 10)); self.log_toggle.config(text="▾ ซ่อน")
        self.log_visible = not self.log_visible

    # ===================== step navigation (กดครั้งเดียว = ทำงาน) =====================
    def show_step(self, step_id):
        self.current_step = step_id
        self._render_steps_state()
        self._render_center(step_id)
        self._render_panel(step_id)

    def _render_steps_state(self):
        c = self.colors
        for s in self.steps:
            w = self.step_widgets.get(s["id"])
            if not w:
                continue
            active = (s["id"] == self.current_step)
            done = (s["id"] in self.completed_steps)
            w["row"].config(bg=c["card_hi"] if active else c["panel"])
            w["txt"].config(bg=c["card_hi"] if active else c["panel"],
                            fg=c["text"] if active else c["text_dim"])
            if done:
                w["badge"].config(text="✓", bg=c["accent_dim"], fg=c["text"])
            else:
                w["badge"].config(text=s["no"], bg=c["accent"] if active else c["card"],
                                  fg=c["on_accent"] if active else c["text_dim"])

    def _render_center(self, step_id):
        c = self.colors
        for w in self.center.winfo_children():
            w.destroy()
        s = next(x for x in self.steps if x["id"] == step_id)
        card = tk.Frame(self.center, bg=c["card"], padx=40, pady=34,
                        highlightthickness=1, highlightbackground=c["border"])
        card.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(card, text=f"{s['emoji']}  ขั้นที่ {s['no']}", bg=c["card"], fg=c[s["color"]],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(card, text=s["title"], bg=c["card"], fg=c["text"],
                 font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(card, text=s["desc"], bg=c["card"], fg=c["text_dim"], font=("Segoe UI", 11),
                 wraplength=620, justify="left").pack(anchor="w", pady=(14, 0))

        btn = self._styled_button(card, f"{s['emoji']}  เริ่ม{s['title']}", s["action"],
                                  c[s["color"]], c["on_accent"])
        btn.pack(fill="x", pady=(28, 0), ipady=6)
        if step_id == "ai":
            self.ai_btn = btn

        tk.Label(card, textvariable=self.status_var, bg=c["card"], fg=c["accent"],
                 font=("Consolas", 11, "bold")).pack(anchor="w", pady=(14, 0))

        nav = tk.Frame(card, bg=c["card"]); nav.pack(side="bottom", fill="x", pady=(18, 0))
        ids = [x["id"] for x in self.steps]; i = ids.index(step_id)
        if i > 0:
            tk.Button(nav, text="‹ ก่อนหน้า", command=lambda: self.show_step(ids[i - 1]),
                      bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 9),
                      cursor="hand2", padx=10, pady=4).pack(side="left")
        if i < len(ids) - 1:
            tk.Button(nav, text="ถัดไป ›", command=lambda: self.show_step(ids[i + 1]),
                      bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 9),
                      cursor="hand2", padx=10, pady=4).pack(side="right")

    def _render_panel(self, step_id):
        c = self.colors
        for w in self.right.winfo_children():
            w.destroy()
        tk.Label(self.right, text="ตัวเลือก", bg=c["panel"], fg=c["text_mute"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=16, pady=(16, 6))

        def panel_card(title):
            f = tk.Frame(self.right, bg=c["card"], padx=12, pady=10,
                         highlightthickness=1, highlightbackground=c["border"])
            f.pack(fill="x", padx=12, pady=6)
            tk.Label(f, text=title, bg=c["card"], fg=c["text_dim"],
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            return f

        # ปุ่มเปิดโฟลเดอร์ที่เกี่ยวข้อง
        f = panel_card("เปิดโฟลเดอร์")
        tk.Button(f, text="📂 เปิด Workspace", command=lambda: self.open_folder(self.source_dir.get()),
                  bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(fill="x", pady=(6, 2))
        if step_id == "import":
            tk.Button(f, text="📷 เปิดโฟลเดอร์กล้อง", command=lambda: self.open_folder(self.camera_source.get()),
                      bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 9),
                      cursor="hand2").pack(fill="x", pady=2)
        if step_id in ("collect",):
            tk.Button(f, text="🗄 เปิด Photo 1", command=lambda: self.open_folder(self.photo1_dir.get()),
                      bg=c["btn_default"], fg=c["text"], relief="flat", font=("Segoe UI", 9),
                      cursor="hand2").pack(fill="x", pady=2)

        info = panel_card("คำแนะนำ")
        tips = {
            "import": "ตั้งโฟลเดอร์กล้องในหน้า ⚙ ก่อน • โหมด 'ดึงเฉพาะใหม่' จะไม่ดึงซ้ำ",
            "merge": "เลือก 2 รูปต่อโฟลเดอร์ • ลาก/ซูมในกรอบ • ส่วนเกินกรอบถูกครอป",
            "crop": "เลือกได้หลายรูป • ลากเพื่อย้าย ล้อเมาส์เพื่อซูม",
            "ai": "ควรรวม/ครอปก่อน • ล็อกอิน ChatGPT ครั้งเดียว • กดปุ่มอีกครั้งเพื่อยกเลิกระหว่างทำ",
            "rename": "รูปกรอบเขียว = ผ่าน AI แล้ว แนะนำเลือกเป็นรูปหลัก",
            "collect": "พรีวิวก่อนคัดลอก • ไม่พบหมวด=ข้าม • ติ๊กอนุญาตถ้าต้องสร้างช่วงใหม่",
            "archive": "ย้าย (ไม่ใช่คัดลอก) ทุกโฟลเดอร์เข้าคลังตามวันที่",
        }
        tk.Label(info, text=tips.get(step_id, ""), bg=c["card"], fg=c["text_dim"],
                 font=("Segoe UI", 9), wraplength=250, justify="left").pack(anchor="w", pady=(6, 0))

    def _styled_button(self, parent, text, cmd, bg, fg):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=("Segoe UI", 11, "bold"),
                      relief="flat", height=2, cursor="hand2", activebackground=self.colors["btn_hover"])
        b.bind("<Enter>", lambda e: b.config(bg=self.colors["accent_hover"] if bg == self.colors["accent"] else self.colors["btn_hover"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ===================== theme switching =====================
    def change_theme(self, name):
        self.theme_name = name
        self.colors = theme_mod.build_palette(self.theme_name, self.accent)
        self.save_settings()
        self._rebuild_ui()

    def pick_accent(self):
        rgb, hx = colorchooser.askcolor(color=self.accent, title="เลือกสี Accent")
        if hx:
            self.accent = hx
            self.colors = theme_mod.build_palette(self.theme_name, self.accent)
            self.save_settings()
            self._rebuild_ui()

    def _rebuild_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.step_widgets = {}
        self.build_ui()
        self.log("เปลี่ยนธีม/สีแล้ว", "success")

    # ===================== animation =====================
    def _animation_loop(self):
        self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
        spin = self.anim_chars[self.anim_idx]
        running_now = False
        for s in self.steps:
            w = self.step_widgets.get(s["id"])
            if not w:
                continue
            if self.is_running.get(s["id"]):
                running_now = True
                try:
                    w["badge"].config(text=spin, bg=self.colors["accent"], fg=self.colors["on_accent"])
                except tk.TclError:
                    pass
        if running_now:
            self.status_var.set(f"{spin}  กำลังทำงาน...")
        else:
            self.status_var.set("")
            self._render_steps_state()
        self.root.after(120, self._animation_loop)

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
            self.source_entry.drop_target_register(DND_FILES)
            self.source_entry.dnd_bind('<<Drop>>', self._handle_drop)
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

    # ===================== Tools (ย้ายเข้าไปในหน้า Settings แล้ว) =====================
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
        win = tk.Toplevel(self.root); win.title("ตั้งค่า / Settings")
        win.geometry("620x720"); win.configure(bg=c["bg"]); win.grab_set()
        tk.Label(win, text="⚙ SETTINGS", bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=24, pady=(20, 10))

        # ปุ่มบันทึก (อยู่ล่างสุด ไม่เลื่อนหาย)
        def save_close():
            self.save_settings(); win.destroy(); self.log("บันทึกการตั้งค่าแล้ว", "success")
        self._styled_button(win, "บันทึก & ปิด", save_close, c["accent"], c["on_accent"]).pack(
            side="bottom", fill="x", padx=24, pady=16)

        # เนื้อหาแบบเลื่อนได้ (การ์ดเยอะ)
        outer = tk.Frame(win, bg=c["bg"]); outer.pack(fill="both", expand=True, padx=24)
        canvas = tk.Canvas(outer, bg=c["bg"], highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview); sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        body = tk.Frame(canvas, bg=c["bg"]); canvas.create_window((0, 0), window=body, anchor="nw", width=560)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._path_card(body, "PHOTO 1 — MAIN DATABASE", self.photo1_dir)
        self._path_card(body, "PHOTO 2 — BACKUP DATABASE", self.photo2_dir)
        self._path_card(body, "ARCHIVE — คลังเก็บประวัติ", self.archive_dir)
        self._path_card(body, "โฟลเดอร์กล้อง (Camera Source) — สำหรับขั้นนำเข้า", self.camera_source)
        self._path_card(body, "CHROME PROFILE (ขั้นสูง · เว้นว่าง = โปรไฟล์ PixUp)", self.chrome_profile_dir)

        cg = tk.Frame(body, bg=c["card"], padx=14, pady=10, highlightthickness=1, highlightbackground=c["border"])
        cg.pack(fill="x", pady=6)
        tk.Label(cg, text="CHATGPT CUSTOM GPT URL (เว้นว่าง = chatgpt.com ปกติ)", bg=c["card"],
                 fg=c["highlight"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(cg, textvariable=self.chatgpt_url, font=("Consolas", 9), bg=c["input_bg"], fg=c["text"],
                 relief="flat", insertbackground="white").pack(fill="x", pady=(6, 0), ipady=5)

        # ===== เสียงแจ้งเตือน =====
        snd = tk.Frame(body, bg=c["card"], padx=14, pady=10, highlightthickness=1, highlightbackground=c["border"])
        snd.pack(fill="x", pady=6)
        tk.Checkbutton(snd, text="🔔 เปิดเสียงแจ้งเตือนเมื่อขั้นที่ใช้เวลานานเสร็จ (นำเข้า/AI/เก็บเข้าฐาน/คลัง)",
                       variable=self.sound_enabled, bg=c["card"], fg=c["text"], selectcolor=c["input_bg"],
                       activebackground=c["card"], font=("Segoe UI", 9), anchor="w",
                       command=self.save_settings).pack(anchor="w")

        # ===== เครื่องมือ (ย้ายมาจากเมนู Tools เดิม) =====
        tools = tk.Frame(body, bg=c["card"], padx=14, pady=10, highlightthickness=1, highlightbackground=c["border"])
        tools.pack(fill="x", pady=6)
        tk.Label(tools, text="🛠 เครื่องมือ", bg=c["card"], fg=c["text_dim"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        def tool(text, cmd):
            tk.Button(tools, text=text, command=cmd, bg=c["btn_default"], fg=c["text"], relief="flat",
                      font=("Segoe UI", 9), cursor="hand2", anchor="w").pack(fill="x", pady=3)

        tool("🗂 จัดกลุ่มตามรหัส", lambda: [win.destroy(), workflow.phase_group(self)])
        tool("🏷 จัดการหมวดหมู่สินค้า (R/N/E/UN ...)", lambda: [win.destroy(), self.open_category_manager()])
        tool("🧹 ล้างความจำการนำเข้า", self.reset_import_memory)
        tool("📜 เปิดโฟลเดอร์ Log", lambda: self.open_folder(config.CONFIG_DIR))

    def _path_card(self, parent, label, var):
        c = self.colors
        card = tk.Frame(parent, bg=c["card"], padx=14, pady=10, highlightthickness=1, highlightbackground=c["border"])
        card.pack(fill="x", pady=5)
        tk.Label(card, text=label, fg=c["text_dim"], bg=c["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg=c["card"]); row.pack(fill="x", pady=(6, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg=c["input_bg"], fg=c["text"],
                 relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=5)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, True), bg=c["btn_default"],
                  fg=c["text"], relief="flat", width=4, cursor="hand2").pack(side="right", padx=(8, 0))

    def open_category_manager(self):
        c = self.colors
        m = tk.Toplevel(self.root); m.title("Categories"); m.geometry("500x600")
        m.configure(bg=c["card"]); m.grab_set()
        tree = ttk.Treeview(m, columns=("C", "N"), show="headings", height=14)
        tree.heading("C", text="Code"); tree.heading("N", text="Name")
        tree.pack(padx=20, pady=10, fill="both", expand=True)

        def refresh():
            for i in tree.get_children():
                tree.delete(i)
            for code, name in sorted(self.type_mapping.items()):
                tree.insert("", "end", values=(code, name))
        refresh()
        ctrl = tk.Frame(m, bg=c["card"], pady=10); ctrl.pack(fill="x", padx=20)
        c_e = tk.Entry(ctrl, width=6); c_e.grid(row=0, column=0)
        n_e = tk.Entry(ctrl, width=18); n_e.grid(row=0, column=1, padx=5)

        def add():
            code, name = c_e.get().strip().upper(), n_e.get().strip()
            if code and name:
                self.type_mapping[code] = name; self.save_settings(); refresh()
                c_e.delete(0, 100); n_e.delete(0, 100)
        self._styled_button(ctrl, "ADD", add, c["accent"], c["on_accent"]).grid(row=0, column=2)

        def delete():
            sel = tree.selection()
            if sel:
                code = str(tree.item(sel[0])['values'][0])
                if messagebox.askyesno("Confirm", f"ลบ '{code}'?"):
                    self.type_mapping.pop(code, None); self.save_settings(); refresh()
        self._styled_button(m, "DELETE", delete, c["error"], "#fff").pack(fill="x", padx=20, pady=14)


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PixUpApp(root)
    root.mainloop()
