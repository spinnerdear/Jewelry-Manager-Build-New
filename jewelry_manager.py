import os
import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk, ImageEnhance
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
        self.version = "2.0 Beta 6"
        self.root.title(f"Jewelry Media Manager v{self.version}")
        self.root.geometry("1200x950")
        self.root.configure(bg="#121212")

        # Centralized Error Codes
        self.error_codes = {
            "E001": "เส้นทางที่ระบุไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในโฟลเดอร์ต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงหรือแก้ไขไฟล์/โฟลเดอร์นี้ (Permission Denied)",
            "E004": "มีไฟล์ชื่อนี้อยู่แล้วในปลายทาง (File Already Exists)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อหรือออฟไลน์อยู่ (Drive Offline/Disconnected)",
            "E006": "เชื่อมต่อระบบ Cloud AI ล้มเหลว หรือ API Key ผิดพลาด",
            "E007": "เกิดปัญหาขณะก๊อปปี้ไฟล์ (Copy Operation Failed)",
            "E999": "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ (Unknown Error)"
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
        self.is_ai_running = False

        # Colors
        self.colors = {
            "bg": "#121212",
            "card": "#1e1e1e",
            "accent": "#00d1b2",
            "accent_hover": "#00f2d3",
            "text": "#ffffff",
            "text_dim": "#888888",
            "btn_default": "#333333",
            "btn_hover": "#444444",
            "success": "#00ffcc",
            "error": "#ff3860",
            "warning": "#ffdd57",
            "highlight": "#209cee"
        }

        self.load_settings()
        self.create_widgets()
        if HAS_DND: self.setup_dnd()
        self.root.after(1000, self.auto_detect_downloads)

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
        with open(self.history_log, "a", encoding="utf-8") as f: f.write(msg_line)

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
                self.source_dir.set(newest)
                self.log(f"Auto-selected: {candidates[0]}", "highlight")

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1a1a1f", height=120); header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg=self.colors["accent"], bg="#1a1a1f", font=("Segoe UI", 28, "bold")).pack(pady=(25, 0))
        tk.Label(header, text=f"CLOUD AI EDITION v{self.version}", fg=self.colors["text_dim"], bg="#1a1a1f", font=("Segoe UI", 10)).pack()

        main_container = tk.Frame(self.root, bg=self.colors["bg"], padx=40, pady=20); main_container.pack(expand=True, fill="both")
        left_side = tk.Frame(main_container, bg=self.colors["bg"]); left_side.pack(side="left", fill="both", expand=True, padx=(0, 20))
        right_side = tk.Frame(main_container, bg=self.colors["bg"]); right_side.pack(side="right", fill="both", expand=True, padx=(20, 0))

        # --- LEFT SIDE: CONFIGURATION ---
        tk.Label(left_side, text="CONFIGURATION", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        self.add_path_card(left_side, "PHOTO 1 (MAIN DATABASE)", self.photo1_dir, True)
        self.add_path_card(left_side, "PHOTO 2 (BACKUP DATABASE)", self.photo2_dir, True)
        self.add_path_card(left_side, "ARCHIVE DRIVE", self.archive_dir, True)
        
        gemini_card = tk.Frame(left_side, bg=self.colors["card"], padx=15, pady=12, highlightthickness=1, highlightbackground="#444"); gemini_card.pack(fill="x", pady=5)
        tk.Label(gemini_card, text="GEMINI API KEY (CLOUD AI)", fg=self.colors["highlight"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(gemini_card, textvariable=self.gemini_key, font=("Consolas", 9), bg="#121212", fg="#fff", relief="flat", show="*", insertbackground="white").pack(fill="x", pady=(5, 0), ipady=5)
        self.gemini_key.trace_add("write", lambda *args: self.save_settings())

        self.create_styled_button(left_side, "⚙ MANAGE CATEGORIES", self.open_category_manager, self.colors["btn_default"], self.colors["accent"]).pack(fill="x", pady=15)

        tk.Label(left_side, text="WORKSPACE", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 10))
        work_frame = tk.Frame(left_side, bg=self.colors["card"], padx=20, pady=15, highlightthickness=1, highlightbackground="#333333"); work_frame.pack(fill="x")
        self.source_entry = tk.Entry(work_frame, textvariable=self.source_dir, font=("Consolas", 11), bg="#121212", fg="#ffffff", relief="flat", highlightthickness=1, highlightbackground="#444", insertbackground="white"); self.source_entry.pack(fill="x", pady=(0, 15), ipady=8)
        self.create_styled_button(work_frame, "BROWSE FOLDER", lambda: self.browse_dir(self.source_dir, False), self.colors["accent"], "#121212").pack(fill="x")

        # --- RIGHT SIDE: STEPS & LOGS ---
        tk.Label(right_side, text="WORKFLOW PROGRESS", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 10))
        self.create_styled_button(right_side, "1. GROUP BY CODE (4 DIGITS)", self.run_phase_1, "#2d2d2d", "white").pack(fill="x", pady=4)
        
        # AI Button with Status Label
        ai_frame = tk.Frame(right_side, bg=self.colors["bg"])
        ai_frame.pack(fill="x", pady=4)
        self.ai_btn = self.create_styled_button(ai_frame, "1.5 🤖 CLOUD AI RETOUCH", self.run_phase_ai_retouch, self.colors["highlight"], "#121212")
        self.ai_btn.pack(side="left", fill="x", expand=True)
        self.ai_status_label = tk.Label(ai_frame, text="", fg=self.colors["highlight"], bg=self.colors["bg"], font=("Consolas", 14, "bold"))
        self.ai_status_label.pack(side="right", padx=10)

        self.create_styled_button(right_side, "2. RENAME FILES", self.run_phase_rename, "#2d2d2d", "white").pack(fill="x", pady=4)
        self.create_styled_button(right_side, "3. COLLECT PHOTOS", self.run_phase_backup, "#2d2d2d", "white").pack(fill="x", pady=4)
        self.create_styled_button(right_side, "4. MOVE TO ARCHIVE", self.run_phase_archive, "#2d2d2d", "white").pack(fill="x", pady=4)

        self.progress = ttk.Progressbar(right_side, orient="horizontal", mode="determinate"); self.progress.pack(fill="x", pady=(15, 0))

        self.log_area = scrolledtext.ScrolledText(right_side, height=18, bg="#000000", fg="#dddddd", font=("Consolas", 10), relief="flat", padx=15, pady=15)
        self.log_area.pack(fill="both", expand=True, pady=(20, 0))
        self.log_area.configure(state='disabled')
        self.log_area.tag_config("time", foreground="#444444")
        self.log_area.tag_config("success", foreground=self.colors["success"])
        self.log_area.tag_config("error", foreground=self.colors["error"])
        self.log_area.tag_config("warning", foreground=self.colors["warning"])
        self.log_area.tag_config("highlight", foreground=self.colors["highlight"])
        self.log_area.tag_config("info", foreground="#ffffff")

    def animate_ai_status(self):
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while self.is_ai_running:
            self.ai_status_label.config(text=chars[idx])
            idx = (idx + 1) % len(chars)
            self.root.update_idletasks()
            threading.Event().wait(0.1)
        self.ai_status_label.config(text="")

    def create_styled_button(self, parent, text, cmd, bg_color, fg_color):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg_color, fg=fg_color, font=("Segoe UI", 10, "bold"), relief="flat", height=2)
        def on_enter(e): 
            if bg_color == self.colors["accent"]: btn.config(bg=self.colors["accent_hover"])
            else: btn.config(bg=self.colors["btn_hover"])
        def on_leave(e): btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter); btn.bind("<Leave>", on_leave)
        return btn

    def add_path_card(self, parent, label, var, is_config):
        card = tk.Frame(parent, bg=self.colors["card"], padx=15, pady=12, highlightthickness=1, highlightbackground="#333333"); card.pack(fill="x", pady=5)
        tk.Label(card, text=label, fg=self.colors["text_dim"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg=self.colors["card"]); row.pack(fill="x", pady=(5, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#121212", fg="#ffffff", relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=5)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, is_config), bg="#333333", fg="white", relief="flat", width=4).pack(side="right", padx=(5, 0))

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d: var.set(os.path.normpath(d)); 
        if is_config: self.save_settings()

    def open_category_manager(self):
        manager = tk.Toplevel(self.root); manager.title("Category Manager"); manager.geometry("500x650"); manager.configure(bg="#1a1a1f"); manager.grab_set()
        tk.Label(manager, text="MANAGE CATEGORIES", fg=self.colors["accent"], bg="#1a1a1f", font=("Segoe UI", 14, "bold")).pack(pady=20)
        tree = ttk.Treeview(manager, columns=("Code", "Name"), show="headings", height=15); tree.heading("Code", text="Code"); tree.heading("Name", text="Name"); tree.pack(padx=20, fill="both", expand=True)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            for c, n in sorted(self.type_mapping.items()): tree.insert("", "end", values=(c, n))
        refresh()
        ctrl = tk.Frame(manager, bg="#1a1a1f", pady=10); ctrl.pack(fill="x", padx=20)
        c_ent = tk.Entry(ctrl, width=5); c_ent.grid(row=0, column=1, padx=5)
        n_ent = tk.Entry(ctrl, width=15); n_ent.grid(row=0, column=3, padx=5)
        def add():
            c, n = c_ent.get().strip().upper(), n_ent.get().strip()
            if c and n: self.type_mapping[c] = n; self.save_settings(); refresh(); c_ent.delete(0, tk.END); n_ent.delete(0, tk.END)
        self.create_styled_button(ctrl, "ADD", add, self.colors["accent"], "#121212").grid(row=0, column=4)
        def delete():
            s = tree.selection()
            if s:
                code = tree.item(s[0])['values'][0]
                if messagebox.askyesno("Confirm", f"Delete '{code}'?"): del self.type_mapping[code]; self.save_settings(); refresh()
        self.create_styled_button(manager, "DELETE SELECTED", delete, self.colors["error"], "white").pack(fill="x", padx=20, pady=20)

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        self.progress['maximum'] = len(files)
        moved = 0
        for i, f in enumerate(files):
            m = re.search(r'(\d{4})', f)
            if m:
                c = m.group(1); t = os.path.join(src, c)
                if not os.path.exists(t): os.makedirs(t)
                shutil.move(os.path.join(src, f), os.path.join(t, f)); moved += 1
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log(f"Phase 1 Complete: Grouped {moved} files.", "success"); messagebox.showinfo("Done", "Grouped.")

    def run_phase_ai_retouch(self):
        if not HAS_GEMINI:
            messagebox.showerror("Error", "Gemini library not found.")
            return
        key = self.gemini_key.get()
        if not key:
            messagebox.showwarning("API Key Missing", "Please enter your Gemini API Key.")
            return
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        all_folders = [os.path.join(src, d) for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
        if not all_folders:
            messagebox.showinfo("Info", "Run Phase 1 first.")
            return
        if not messagebox.askyesno("Confirm", f"Process {len(all_folders)} folders with Cloud AI Agent?"):
            return

        self.ai_btn.config(state="disabled", text="⌛ AI PROCESSING...")
        self.is_ai_running = True
        threading.Thread(target=self.animate_ai_status, daemon=True).start()
        threading.Thread(target=self.gemini_agent_process, args=(all_folders, key), daemon=True).start()

    def gemini_agent_process(self, folder_paths, api_key):
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            self.log(f"API Error: {e}", "error", "E006")
            self.stop_ai_vis(); return

        self.progress['maximum'] = len(folder_paths)
        self.log("🚀 Gemini AI Agent is now retouching...", "highlight")
        for i, folder in enumerate(folder_paths):
            folder_name = os.path.basename(folder)
            self.log(f"Processing {folder_name}...", "info")
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if not files: continue
                out_dir = os.path.join(folder, "ai_retouched")
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                p_type = folder_name[0].upper()
                for f_path in files:
                    self.retouch_single_image_advanced(f_path, out_dir, p_type)
                    self.log(f"  > Done: {os.path.basename(f_path)}", "success")
                if p_type == 'E' and len(files) >= 2:
                    self.merge_earring_views(files, out_dir, folder_name)
            except Exception as e:
                self.log(f"Error {folder_name}: {e}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Cloud Agent tasks complete.", "highlight")
        self.stop_ai_vis()
        self.root.after(0, lambda: messagebox.showinfo("Done", "AI Finished."))

    def stop_ai_vis(self):
        self.is_ai_running = False
        self.ai_btn.config(state="normal", text="1.5 🤖 CLOUD AI RETOUCH")

    def retouch_single_image_advanced(self, path, out_dir, p_type):
        import cv2
        import numpy as np
        from rembg import remove
        filename = os.path.basename(path); out_path = os.path.join(out_dir, filename)
        try:
            with open(path, 'rb') as f: input_data = f.read()
            no_bg = remove(input_data)
            nparr = np.frombuffer(no_bg, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
            if p_type == 'R':
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                img_cv = cv2.filter2D(img_cv, -1, kernel)
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGRA2RGBA))
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(white_bg, img).convert("RGB")
            img = ImageEnhance.Color(img).enhance(1.08)
            img = ImageEnhance.Brightness(img).enhance(1.02)
            img.save(out_path, "JPEG", quality=95)
        except Exception as e:
            self.log(f"Process Error {filename}: {e}", "error")

    def merge_earring_views(self, files, out_dir, folder_name):
        try:
            imgs = [Image.open(f) for f in files[:2]]
            composite = Image.new('RGB', (2400, 1200), (255, 255, 255))
            for i, im in enumerate(imgs):
                im.thumbnail((1100, 1100))
                x = 50 if i == 0 else 1250
                y = (1200 - im.height) // 2
                composite.paste(im, (x, y))
            composite.save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95)
            self.log(f"Merged view created for {folder_name}", "success")
        except Exception as e: self.log(f"Merge Error: {e}", "error")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, folder_name in enumerate(folders):
            base_path = os.path.join(src, folder_name)
            ai_path = os.path.join(base_path, "ai_retouched")
            target_work_dir = ai_path if os.path.exists(ai_path) and os.listdir(ai_path) else base_path
            files = sorted([f for f in os.listdir(target_work_dir) if os.path.isfile(os.path.join(target_work_dir, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            if not files: continue
            main_file = self.choose_main_file_visual(target_work_dir, files, folder_name)
            if not main_file: continue
            temp_files = []
            for f in files:
                src_f = os.path.join(target_work_dir, f); tmp_n = f"temp_{f}"
                shutil.copy2(src_f, os.path.join(base_path, tmp_n)); temp_files.append(tmp_n)
            counter = 2
            for temp in temp_files:
                ext = os.path.splitext(temp)[1]
                if temp == f"temp_{main_file}": final = f"{folder_name}{ext}"
                else: final = f"{folder_name}-{counter}{ext}"; counter += 1
                final_path = os.path.join(base_path, final)
                if os.path.exists(final_path): os.remove(final_path)
                os.rename(os.path.join(base_path, temp), final_path)
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Phase 2 Complete.", "success")

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1: return files[0]
        max_idx = -1; suggested = files[-1]
        for f in files:
            m = re.search(r'_(\d+)\.', f)
            if m and int(m.group(1)) > max_idx: max_idx = int(m.group(1)); suggested = f
        win = tk.Toplevel(self.root); win.title(f"Primary: {folder_name}"); win.geometry("1000x750"); win.configure(bg="#121212"); win.grab_set()
        result = tk.StringVar(value="")
        tk.Label(win, text=f"SELECT PRIMARY: {folder_name}", fg=self.colors["accent"], bg="#121212", font=("Segoe UI", 11, "bold")).pack(pady=10)
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
                f_frame = tk.Frame(gallery, bg="#1e1e1e", padx=5, pady=5, highlightthickness=1, highlightbackground="#333333")
                f_frame.grid(row=len(photo_refs)//cols, column=len(photo_refs)%cols, padx=8, pady=8)
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
        return f"{start}-{start+199}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]): messagebox.showwarning("Warning", "Config paths."); return
        def backup_task():
            self.log("--- Starting Phase 3 ---", "highlight")
            for d_n, d_p in [("PHOTO 1", p1), ("PHOTO 2", p2)]:
                dr = os.path.splitdrive(d_p)[0]
                if dr and not os.path.exists(dr):
                    self.log(f"{d_n} Offline", "error", "E005"); return
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
            self.progress['maximum'] = len(folders); s_c, sk_c, errs = 0, 0, []
            for i, f_n in enumerate(folders):
                f_p = os.path.join(src, f_n); main_f = None
                for f in os.listdir(f_p):
                    if os.path.splitext(f)[0] == f_n: main_f = f; break
                if not main_f: sk_c += 1; continue
                p_t = self.type_mapping.get(f_n[0].upper(), "Other")
                if "-VN-" in f_n.upper(): t_r = os.path.join("Vincentio", p_t)
                else:
                    m = re.search(r'(\d+)', f_n); range_s = self.get_range(int(m.group(1))) if m else "Unknown"
                    t_r = os.path.join(p_t, f"{p_t} {range_s}")
                t1, t2 = os.path.join(p1, t_r), os.path.join(p2, t_r)
                if not os.path.exists(t1):
                    par = os.path.dirname(t1)
                    if os.path.exists(par):
                        ms = difflib.get_close_matches(os.path.basename(t1), os.listdir(par), n=3, cutoff=0.6)
                        if ms:
                            sel = self.ask_folder_match_visual(f_n, t_r, par, ms)
                            if sel: t1 = os.path.join(par, sel); t2 = os.path.join(p2, t_r.replace(os.path.basename(t_r), sel))
                if not os.path.exists(t1): self.log(f"Path missing: {f_n}", "error", "E001"); sk_c += 1; continue
                try:
                    bc = f_n.upper(); ac = bc.replace("-S00", "-SC0") if "-S00" in bc else bc.replace("-SC0", "-S00") if "-SC0" in bc else None
                    o1 = [os.path.join(t1, f) for f in os.listdir(t1) if os.path.splitext(f)[0].upper() in [bc, ac]]
                    o2 = [os.path.join(t2, f) for f in os.listdir(t2) if os.path.exists(t2) and os.path.splitext(f)[0].upper() in [bc, ac]]
                    if self.show_preview(o1[0] if o1 else None, o2[0] if o2 else None, os.path.join(f_p, main_f), t1):
                        for f in o1: os.remove(f)
                        shutil.copy2(os.path.join(f_p, main_f), os.path.join(t1, main_f))
                        if os.path.exists(os.path.dirname(t2)):
                            if not os.path.exists(t2): os.makedirs(t2)
                            for f in o2: os.remove(f)
                            shutil.copy2(os.path.join(f_p, main_f), os.path.join(t2, main_f))
                        s_c += 1; self.log(f"Collected: {f_n}", "success")
                    else: sk_c += 1
                except Exception as e: self.log(f"Failed {f_n}: {e}", "error", "E007"); errs.append(e)
                self.progress['value'] = i + 1; self.root.update_idletasks()
            self.log("Phase 3 Done.", "highlight"); self.root.after(0, lambda: self.finish_phase_3(s_c, sk_c, errs))
        threading.Thread(target=backup_task, daemon=True).start()

    def ask_folder_match_visual(self, product_code, original_target, parent_path, matches):
        win = tk.Toplevel(self.root); win.title("Select Dest"); win.geometry("550x450"); win.grab_set(); res = tk.StringVar()
        tk.Label(win, text=f"DESTINATION NOT FOUND FOR: {product_code}", fg=self.colors["accent"]).pack(pady=10)
        lb = tk.Listbox(win, bg="#1e1e1e", fg="white"); lb.pack(fill="both", expand=True, padx=40)
        for m in matches: lb.insert(tk.END, m)
        def on_select():
            if lb.curselection(): res.set(matches[lb.curselection()[0]]); win.destroy()
        tk.Button(win, text="USE SELECTED", command=on_select, bg=self.colors["accent"]).pack(pady=20)
        self.root.wait_window(win); return res.get()

    def finish_phase_3(self, s, sk, e):
        messagebox.showinfo("Done", f"Success: {s}, Skipped: {sk}")

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]): return
        now = datetime.now(); path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(path): os.makedirs(path)
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, f_n in enumerate(folders):
            try: shutil.move(os.path.join(src, f_n), os.path.join(path, f_n)); self.log(f"Archived: {f_n}")
            except: pass
            self.progress['value'] = i + 1; self.root.update_idletasks()
        messagebox.showinfo("Done", "Archived.")

    def show_preview(self, p1, p2, n, d):
        dialog = tk.Toplevel(self.root); dialog.title("Preview"); dialog.geometry("1000x750"); dialog.grab_set(); res = tk.BooleanVar(value=False)
        grid = tk.Frame(dialog, bg="#121212"); grid.pack(expand=True, fill="both")
        def add_box(p, t):
            box = tk.Frame(grid, bg="#121212"); box.pack(side="left", expand=True, fill="both")
            if p and os.path.exists(p):
                img = Image.open(p); img.thumbnail((300, 300)); ph = ImageTk.PhotoImage(img)
                l = tk.Label(box, image=ph); l.image = ph; l.pack()
            else: tk.Label(box, text="[MISSING]").pack()
        add_box(p1, "P1"); add_box(p2, "P2"); add_box(n, "New")
        tk.Button(dialog, text="REPLACE", command=lambda: [res.set(True), dialog.destroy()]).pack(side="left"); tk.Button(dialog, text="SKIP", command=dialog.destroy).pack(side="right")
        self.root.wait_window(dialog); return res.get()

    def add_path_card(self, parent, label, var, is_config):
        card = tk.Frame(parent, bg=self.colors["card"], padx=15, pady=12, highlightthickness=1, highlightbackground="#333333"); card.pack(fill="x", pady=5)
        tk.Label(card, text=label, fg=self.colors["text_dim"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg=self.colors["card"]); row.pack(fill="x", pady=(5, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#121212", fg="#ffffff", relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=5)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, is_config), bg="#333333", fg="white", relief="flat", width=4).pack(side="right", padx=(5, 0))

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = JewelryManagerApp(root); root.mainloop()
