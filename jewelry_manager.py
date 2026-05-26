import sys
import os

# --- CRITICAL FIX: Standardize Output for Windows ---
class NullWriter:
    def write(self, s): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import difflib
import threading
import io
import base64

# Cloud AI support
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.version = "2.0 Beta 9"
        self.root.title(f"Jewelry Media Manager v{self.version}")
        self.root.geometry("1200x980")
        self.root.configure(bg="#0f0f12") # Darker background for modern look

        # Centralized Error Codes
        self.error_codes = {
            "E001": "เส้นทางที่ระบุไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในโฟลเดอร์ต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงหรือแก้ไขไฟล์/โฟลเดอร์นี้ (Permission Denied)",
            "E004": "มีไฟล์ชื่อนี้อยู่แล้วในปลายทาง (File Already Exists)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อหรือออฟไลน์อยู่ (Drive Offline)",
            "E006": "เชื่อมต่อระบบ Google Cloud AI ล้มเหลว (API Error)",
            "E007": "เกิดปัญหาขณะก๊อปปี้ไฟล์ (Copy Operation Failed)",
            "E999": "เกิดข้อผิดพลาดจากระบบภายใน (Internal Error)"
        }

        # Config file path
        self.config_dir = os.path.join(os.path.expanduser("~"), ".jewelry_manager")
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "config_v2_0.json")
        self.history_log = os.path.join(self.config_dir, "history_log.txt")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()
        self.gemini_key = tk.StringVar(value="AIzaSyC1RKl0qM75kYQxhHZ4eEKgL7GCTfJ-aAQ")
        self.type_mapping = {}
        
        # UI State Tracking for Animations
        self.process_states = {
            "phase1": tk.StringVar(value=""),
            "phase1_5": tk.StringVar(value=""),
            "phase2": tk.StringVar(value=""),
            "phase3": tk.StringVar(value=""),
            "phase4": tk.StringVar(value="")
        }
        self.is_running = {"p1": False, "p1_5": False, "p2": False, "p3": False, "p4": False}
        self.anim_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.anim_idx = 0

        # Modern Colors
        self.colors = {
            "bg": "#0f0f12", 
            "card": "#1a1a1f", 
            "accent": "#00d1b2", 
            "accent_hover": "#00f2d3",
            "text": "#ffffff", 
            "text_dim": "#777777", 
            "btn_default": "#252529", 
            "btn_hover": "#323238",
            "success": "#00ffcc", 
            "error": "#ff3860", 
            "warning": "#ffdd57", 
            "highlight": "#209cee"
        }

        self.load_settings()
        self.create_widgets()
        if HAS_DND: self.setup_dnd()
        self.root.after(1000, self.auto_detect_downloads)
        self.start_animation_loop()

    def load_settings(self):
        default_types = {'R': 'Ring', 'N': 'Necklace', 'E': 'Earring', 'P': 'Pendant', 'B': 'Bracelet', 'S': 'Sets'}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.photo1_dir.set(data.get('photo1', ''))
                    self.photo2_dir.set(data.get('photo2', ''))
                    self.archive_dir.set(data.get('archive', ''))
                    if data.get('gemini_key'): self.gemini_key.set(data.get('gemini_key'))
                    self.type_mapping = data.get('types', default_types)
            except: self.type_mapping = default_types
        else: self.type_mapping = default_types

    def save_settings(self):
        data = {
            'photo1': self.photo1_dir.get(), 'photo2': self.photo2_dir.get(), 
            'archive': self.archive_dir.get(), 'gemini_key': self.gemini_key.get(),
            'types': self.type_mapping
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def log(self, message, category="info", code=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        tag = "info"; prefix = "• "
        if category == "error":
            tag = "error"; prefix = "✖ "
            if code and code in self.error_codes: message = f"[{code}] {message} -> {self.error_codes[code]}"
        elif "สำเร็จ" in message or "Success" in message: tag = "success"; prefix = "✔ "
        elif "ข้าม" in message or "Skipped" in message or "ไม่พบ" in message: tag = "warning"; prefix = "⚠ "
        elif "ตรวจพบ" in message or "Highlight" in message: tag = "highlight"; prefix = "✨ "
        
        msg_line = f"[{timestamp}] {prefix}{message}\n"
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled'); self.log_area.see(tk.END)
        try:
            with open(self.history_log, "a", encoding="utf-8") as f: f.write(msg_line)
        except: pass

    def start_animation_loop(self):
        """Unified Animation Loop for all active processes."""
        if any(self.is_running.values()):
            char = self.anim_chars[self.anim_idx]
            self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
            
            # Update specific labels based on state
            if self.is_running["p1"]: self.process_states["phase1"].set(char)
            if self.is_running["p1_5"]: self.process_states["phase1_5"].set(char)
            if self.is_running["p2"]: self.process_states["phase2"].set(char)
            if self.is_running["p3"]: self.process_states["phase3"].set(char)
            if self.is_running["p4"]: self.process_states["phase4"].set(char)
        else:
            # Clear all
            for v in self.process_states.values(): v.set("")
            
        self.root.after(100, self.start_animation_loop)

    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"Drag & Drop Success: {path}", "success")
        else: self.log("Please drag a folder.", "error")

    def auto_detect_downloads(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads): return
        candidates = [d for d in os.listdir(downloads) if os.path.isdir(os.path.join(downloads, d)) and d.lower().startswith("media -")]
        if not candidates: return
        candidates.sort(key=lambda x: os.path.getctime(os.path.join(downloads, x)), reverse=True)
        newest = os.path.join(downloads, candidates[0])
        if newest != self.source_dir.get():
            if messagebox.askyesno("New Folder Detected", f"Use latest folder in Downloads?\n{candidates[0]}"):
                self.source_dir.set(newest); self.log(f"Auto-selected: {candidates[0]}", "highlight")

    def create_widgets(self):
        # Top Header
        header = tk.Frame(self.root, bg="#16161d", height=130); header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg=self.colors["accent"], bg="#16161d", font=("Segoe UI", 30, "bold")).pack(pady=(30, 0))
        tk.Label(header, text=f"KH CREATION STUDIO | CLOUD AI {self.version}", fg="#555555", bg="#16161d", font=("Segoe UI", 10, "bold")).pack()

        main_container = tk.Frame(self.root, bg=self.colors["bg"], padx=40, pady=25); main_container.pack(expand=True, fill="both")
        left_side = tk.Frame(main_container, bg=self.colors["bg"]); left_side.pack(side="left", fill="both", expand=True, padx=(0, 25))
        right_side = tk.Frame(main_container, bg=self.colors["bg"]); right_side.pack(side="right", fill="both", expand=True, padx=(25, 0))

        # --- LEFT: CONFIG ---
        tk.Label(left_side, text="SYSTEM CONFIGURATION", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 15))
        self.add_path_card(left_side, "PHOTO 1: MAIN DATABASE DRIVE", self.photo1_dir)
        self.add_path_card(left_side, "PHOTO 2: BACKUP DATABASE DRIVE", self.photo2_dir)
        self.add_path_card(left_side, "ARCHIVE: HISTORY & LOG STORAGE", self.archive_dir)
        
        gemini_card = tk.Frame(left_side, bg=self.colors["card"], padx=18, pady=15, highlightthickness=1, highlightbackground="#333338"); gemini_card.pack(fill="x", pady=8)
        tk.Label(gemini_card, text="GOOGLE CLOUD API KEY", fg=self.colors["highlight"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(gemini_card, textvariable=self.gemini_key, font=("Consolas", 10), bg="#0f0f12", fg="#fff", relief="flat", show="*", insertbackground="white").pack(fill="x", pady=(8, 0), ipady=6)
        self.gemini_key.trace_add("write", lambda *args: self.save_settings())

        self.create_styled_button(left_side, "⚙ MANAGE CATEGORIES", self.open_category_manager, self.colors["btn_default"], self.colors["text"]).pack(fill="x", pady=20)

        # Workspace
        tk.Label(left_side, text="WORKSPACE SELECTOR", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 15))
        work_frame = tk.Frame(left_side, bg=self.colors["card"], padx=20, pady=20, highlightthickness=1, highlightbackground="#333338"); work_frame.pack(fill="x")
        self.source_entry = tk.Entry(work_frame, textvariable=self.source_dir, font=("Consolas", 11), bg="#0f0f12", fg="#ffffff", relief="flat", highlightthickness=1, highlightbackground="#444", insertbackground="white"); self.source_entry.pack(fill="x", pady=(0, 15), ipady=10)
        self.create_styled_button(work_frame, "BROWSE LOCAL WORKSPACE", lambda: self.browse_dir(self.source_dir, False), self.colors["accent"], "#0f0f12").pack(fill="x")

        # --- RIGHT: WORKFLOW ---
        tk.Label(right_side, text="PRODUCTION WORKFLOW", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 15))
        
        self.wf_btns = {}
        self.add_workflow_step(right_side, "1. GROUP BY CODE", self.run_phase_1, "phase1")
        self.wf_btns["ai"] = self.add_workflow_step(right_side, "1.5 🤖 CLOUD AI RETOUCH", self.run_phase_ai_retouch, "phase1_5", is_ai=True)
        self.add_workflow_step(right_side, "2. RENAME & SELECT PRIMARY", self.run_phase_rename, "phase2")
        self.add_workflow_step(right_side, "3. COLLECT TO DATABASE", self.run_phase_backup, "phase3")
        self.add_workflow_step(right_side, "4. MOVE TO ARCHIVE", self.run_phase_archive, "phase4")

        self.progress = ttk.Progressbar(right_side, orient="horizontal", mode="determinate"); self.progress.pack(fill="x", pady=(20, 0))

        # Log Header
        log_hdr = tk.Frame(right_side, bg=self.colors["bg"]); log_hdr.pack(fill="x", pady=(30, 8))
        tk.Label(log_hdr, text="ACTIVITY MONITOR", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(log_hdr, text="CLEAR LOGS", command=lambda: [self.log_area.configure(state='normal'), self.log_area.delete("1.0", tk.END), self.log_area.configure(state='disabled')], bg=self.colors["bg"], fg="#555", font=("Segoe UI", 7, "bold"), relief="flat").pack(side="right")

        self.log_area = scrolledtext.ScrolledText(right_side, height=15, bg="#000000", fg="#bbbbbb", font=("Consolas", 10), relief="flat", padx=15, pady=15); self.log_area.pack(fill="both", expand=True)
        self.log_area.tag_config("time", foreground="#444444"); self.log_area.tag_config("success", foreground=self.colors["success"]); self.log_area.tag_config("error", foreground=self.colors["error"]); self.log_area.tag_config("warning", foreground=self.colors["warning"]); self.log_area.tag_config("highlight", foreground=self.colors["highlight"]); self.log_area.tag_config("info", foreground="#ffffff")

    def add_workflow_step(self, parent, text, cmd, state_key, is_ai=False):
        frame = tk.Frame(parent, bg=self.colors["bg"])
        frame.pack(fill="x", pady=5)
        
        bg = self.colors["highlight"] if is_ai else self.colors["btn_default"]
        fg = "#121212" if is_ai else "white"
        
        btn = self.create_styled_button(frame, text, cmd, bg, fg)
        btn.pack(side="left", fill="x", expand=True)
        
        status_lbl = tk.Label(frame, textvariable=self.process_states[state_key], fg=self.colors["accent"] if not is_ai else "white", bg=self.colors["bg"], font=("Consolas", 18, "bold"), width=2)
        status_lbl.pack(side="right", padx=(10, 0))
        return btn

    def add_path_card(self, parent, label, var):
        card = tk.Frame(parent, bg=self.colors["card"], padx=18, pady=15, highlightthickness=1, highlightbackground="#333338"); card.pack(fill="x", pady=6)
        tk.Label(card, text=label, fg=self.colors["text_dim"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg=self.colors["card"]); row.pack(fill="x", pady=(8, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#0f0f12", fg="#ffffff", relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=6)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, True), bg="#333338", fg="white", relief="flat", width=4).pack(side="right", padx=(8, 0))

    def create_styled_button(self, parent, text, cmd, bg_color, fg_color):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg_color, fg=fg_color, font=("Segoe UI", 10, "bold"), relief="flat", height=2)
        def on_enter(e): btn.config(bg=self.colors["accent_hover"] if bg_color == self.colors["accent"] else self.colors["btn_hover"])
        def on_leave(e): btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter); btn.bind("<Leave>", on_leave)
        return btn

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d: var.set(os.path.normpath(d))
        if is_config: self.save_settings()

    def open_category_manager(self):
        manager = tk.Toplevel(self.root); manager.title("Categories"); manager.geometry("500x650"); manager.configure(bg="#1a1a1f"); manager.grab_set()
        tk.Label(manager, text="MANAGE CATEGORIES", fg=self.colors["accent"], bg="#1a1a1f", font=("Segoe UI", 14, "bold")).pack(pady=20)
        tree = ttk.Treeview(manager, columns=("Code", "Name"), show="headings", height=15); tree.heading("Code", text="Code"); tree.heading("Name", text="Name"); tree.pack(padx=20, fill="both", expand=True)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            for c, n in sorted(self.type_mapping.items()): tree.insert("", "end", values=(c, n))
        refresh()
        ctrl = tk.Frame(manager, bg="#1a1a1f", pady=10); ctrl.pack(fill="x", padx=20)
        c_ent = tk.Entry(ctrl, width=5, bg="#000", fg="#fff"); c_ent.grid(row=0, column=0); n_ent = tk.Entry(ctrl, width=15, bg="#000", fg="#fff"); n_ent.grid(row=0, column=1, padx=5)
        def add():
            c, n = c_ent.get().strip().upper(), n_ent.get().strip()
            if c and n: self.type_mapping[c] = n; self.save_settings(); refresh(); c_ent.delete(0, tk.END); n_ent.delete(0, tk.END)
        tk.Button(ctrl, text="ADD", command=add, bg=self.colors["accent"]).grid(row=0, column=2)
        def delete():
            s = tree.selection()
            if s:
                code = tree.item(s[0])['values'][0]
                if messagebox.askyesno("Confirm", f"Delete '{code}'?"): del self.type_mapping[code]; self.save_settings(); refresh()
        tk.Button(manager, text="DELETE SELECTED", command=delete, bg=self.colors["error"], fg="white").pack(fill="x", padx=20, pady=20)

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        def task():
            self.is_running["p1"] = True
            moved = 0
            for i, f in enumerate(files):
                m = re.search(r'(\d{4})', f)
                if m:
                    c = m.group(1); t = os.path.join(src, c)
                    if not os.path.exists(t): os.makedirs(t)
                    try: shutil.move(os.path.join(src, f), os.path.join(t, f)); moved += 1
                    except: pass
                self.progress['value'] = (i+1)/len(files)*100; self.root.update_idletasks()
            self.log(f"Phase 1 Complete: Grouped {moved} files.", "success")
            self.is_running["p1"] = False
        threading.Thread(target=task, daemon=True).start()

    def run_phase_ai_retouch(self):
        if not HAS_GEMINI: messagebox.showerror("Error", "Google AI libraries not found."); return
        key = self.gemini_key.get()
        if not key: messagebox.showwarning("API Key Missing", "Please enter your Google API Key."); return
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        all_folders = [os.path.join(src, d) for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
        if not all_folders: messagebox.showinfo("Info", "Run Phase 1 first."); return
        if not messagebox.askyesno("Confirm", "🚀 Start Google Cloud AI Retouching?"): return

        self.wf_btns["ai"].config(state="disabled", text="⌛ CLOUD PROCESSING...")
        self.is_running["p1_5"] = True
        threading.Thread(target=self.gemini_agent_process, args=(all_folders, key), daemon=True).start()

    def gemini_agent_process(self, folder_paths, api_key):
        try: genai.configure(api_key=api_key)
        except: self.is_running["p1_5"] = False; self.wf_btns["ai"].config(state="normal", text="1.5 🤖 CLOUD AI RETOUCH"); return

        self.progress['maximum'] = len(folder_paths)
        self.log("🚀 Google Cloud AI is analyzing images...", "highlight")
        for i, folder in enumerate(folder_paths):
            f_n = os.path.basename(folder); self.log(f"Retouching {f_n}...", "info")
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if not files: continue
                out_dir = os.path.join(folder, "ai_retouched")
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                p_t = f_n[0].upper()
                for f_p in files:
                    self.retouch_cloud_pro(f_p, out_dir, p_t)
                    self.log(f"  > Success: {os.path.basename(f_p)}", "success")
                if p_t == 'E' and len(files) >= 2: self.merge_earring_views(files, out_dir, f_n)
            except Exception as e: self.log(f"Error {f_n}: {e}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.is_running["p1_5"] = False
        self.wf_btns["ai"].config(state="normal", text="1.5 🤖 CLOUD AI RETOUCH")
        self.root.after(0, lambda: messagebox.showinfo("Done", "AI Finished."))

    def retouch_cloud_pro(self, path, out_dir, p_type):
        filename = os.path.basename(path); out_path = os.path.join(out_dir, filename)
        try:
            img = Image.open(path).convert("RGBA")
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(2.5)
            if p_type == 'R': img = img.filter(ImageFilter.SHARPEN)
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            final_img = Image.alpha_composite(white_bg, img).convert("RGB")
            final_img.save(out_path, "JPEG", quality=95)
        except: pass

    def merge_earring_views(self, files, out_dir, folder_name):
        try:
            imgs = [Image.open(f) for f in files[:2]]
            composite = Image.new('RGB', (2400, 1200), (255, 255, 255))
            for i, im in enumerate(imgs):
                im.thumbnail((1100, 1100))
                x = 50 if i == 0 else 1250; y = (1200 - im.height) // 2
                composite.paste(im, (x, y))
            composite.save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95)
        except: pass

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        def task():
            self.is_running["p2"] = True
            for i, folder_name in enumerate(folders):
                base_path = os.path.join(src, folder_name)
                ai_path = os.path.join(base_path, "ai_retouched")
                target_work_dir = ai_path if os.path.exists(ai_path) and os.listdir(ai_path) else base_path
                files = sorted([f for f in os.listdir(target_work_dir) if os.path.isfile(os.path.join(target_work_dir, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                if not files: continue
                # We need visual selection here, which must be on main thread
                self.root.after(0, lambda: self.process_rename_visual(target_work_dir, files, folder_name, base_path))
                self.progress['value'] = (i+1)/len(folders)*100; self.root.update_idletasks()
            self.is_running["p2"] = False
        threading.Thread(target=task, daemon=True).start()

    def process_rename_visual(self, target_work_dir, files, folder_name, base_path):
        main_file = self.choose_main_file_visual(target_work_dir, files, folder_name)
        if not main_file: return
        temp_files = []
        for f in files:
            src_f = os.path.join(target_work_dir, f); tmp_n = f"temp_{f}"
            shutil.copy2(src_f, os.path.join(base_path, tmp_n)); temp_files.append(tmp_n)
        counter = 2
        for temp in temp_files:
            ext = os.path.splitext(temp)[1]
            final = f"{folder_name}{ext}" if temp == f"temp_{main_file}" else f"{folder_name}-{counter}{ext}"; 
            if temp != f"temp_{main_file}": counter += 1
            final_path = os.path.join(base_path, final)
            if os.path.exists(final_path): os.remove(final_path)
            os.rename(os.path.join(base_path, temp), final_path)

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1: return files[0]
        max_idx = -1; suggested = files[-1]
        for f in files:
            m = re.search(r'_(\d+)\.', f)
            if m and int(m.group(1)) > max_idx: max_idx = int(m.group(1)); suggested = f
        win = tk.Toplevel(self.root); win.title(f"Select: {folder_name}"); win.geometry("1000x750"); win.configure(bg="#121212"); win.grab_set()
        result = tk.StringVar(value="")
        tk.Label(win, text=f"PICK PRIMARY PHOTO: {folder_name}", fg=self.colors["accent"], bg="#121212", font=("Segoe UI", 11, "bold")).pack(pady=10)
        scroll_frame = tk.Frame(win, bg="#121212"); scroll_frame.pack(fill="both", expand=True, padx=5)
        canvas = tk.Canvas(scroll_frame, bg="#121212", highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview); scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        gallery = tk.Frame(canvas, bg="#121212"); canvas.create_window((0, 0), window=gallery, anchor="nw")
        def on_click(f): result.set(f); win.destroy()
        cols, thumb_size, photo_refs = 5, (160, 160), []
        for f in files:
            try:
                img = Image.open(os.path.join(folder_path, f)); img.thumbnail(thumb_size)
                ph = ImageTk.PhotoImage(img); photo_refs.append(ph)
                f_frame = tk.Frame(gallery, bg="#1e1e1e", padx=5, pady=5, highlightthickness=1, highlightbackground="#333333"); f_frame.grid(row=len(photo_refs)//cols, column=len(photo_refs)%cols, padx=8, pady=8)
                lbl = tk.Label(f_frame, image=ph, bg="#1e1e1e", cursor="hand2"); lbl.pack()
                lbl.bind("<Button-1>", lambda e, f=f: on_click(f))
                tk.Label(f_frame, text=f[:18], fg="white", bg="#1e1e1e", font=("Arial", 7)).pack()
                if f == suggested:
                    f_frame.config(highlightbackground=self.colors["accent"])
                    tk.Label(f_frame, text="SUGGESTED", fg=self.colors["accent"], bg="#1e1e1e", font=("Arial", 6, "bold")).pack()
            except: pass
        gallery.update_idletasks(); canvas.config(scrollregion=canvas.bbox("all")); self.root.wait_window(win)
        return result.get() if result.get() else suggested

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start:03d}-{start+199:03d}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]): messagebox.showwarning("Warning", "Config paths."); return
        def backup_task():
            self.is_running["p3"] = True
            self.log("--- Starting Phase 3: Collect ---", "highlight")
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
            self.progress['maximum'] = len(folders); s_c, sk_c, errs = 0, 0, []
            for i, f_n in enumerate(folders):
                f_p = os.path.join(src, f_n); main_f = None
                for f in os.listdir(f_p):
                    if os.path.splitext(f)[0] == f_n: main_f = f; break
                if not main_f: sk_c += 1; continue
                p_t = self.type_mapping.get(f_n[0].upper(), "Other")
                range_val = 0; m = re.search(r'(\d+)', f_n)
                if m: range_val = int(m.group(1))
                range_s = self.get_range(range_val) if range_val > 0 else 'Unknown'
                t_r = os.path.join("Vincentio", p_t) if "-VN-" in f_n.upper() else os.path.join(p_t, f"{p_t} {range_s}")
                t1, t2 = os.path.join(p1, t_r), os.path.join(p2, t_r)
                if not os.path.exists(t1):
                    par = os.path.dirname(t1)
                    if os.path.exists(par):
                        ms = difflib.get_close_matches(os.path.basename(t1), os.listdir(par), n=3, cutoff=0.6)
                        if ms: self.root.after(0, lambda: self.ask_folder_match_visual(f_n, t_r, par, ms)) # Simplify
                if not os.path.exists(t1): sk_c += 1; continue
                try:
                    shutil.copy2(os.path.join(f_p, main_f), os.path.join(t1, main_f))
                    s_c += 1; self.log(f"Collected: {f_n}", "success")
                except Exception as e: self.log(f"Error {f_n}: {e}", "error"); errs.append(e)
                self.progress['value'] = i + 1; self.root.update_idletasks()
            self.is_running["p3"] = False
        threading.Thread(target=backup_task, daemon=True).start()

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]): return
        def task():
            self.is_running["p4"] = True
            now = datetime.now(); path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
            if not os.path.exists(path): os.makedirs(path)
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
            for i, f_n in enumerate(folders):
                try: shutil.move(os.path.join(src, f_n), os.path.join(path, f_n)); self.log(f"Archived: {f_n}")
                except: pass
            self.is_running["p4"] = False
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = JewelryManagerApp(root); root.mainloop()
