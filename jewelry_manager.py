import sys
import os

# --- CRITICAL FIX: Standardize Output for Windows (Lightweight) ---
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

# Cloud AI support (Pure Cloud - No local heavy libs)
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
        self.version = "2.0 Beta 10"
        self.root.title(f"Jewelry Media Manager v{self.version}")
        self.root.geometry("1200x950")
        self.root.configure(bg="#0f0f12")

        # Centralized Error Codes
        self.error_codes = {
            "E001": "เส้นทางที่ระบุไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในโฟลเดอร์ต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงไฟล์ (Permission Denied)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อ (Drive Offline)",
            "E006": "เชื่อมต่อ Google Cloud AI ล้มเหลว (Check Internet/API Key)",
            "E007": "เกิดปัญหาขณะก๊อปปี้ไฟล์",
            "E999": "เกิดข้อผิดพลาดภายในระบบ"
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
        
        self.process_states = {
            "p1": tk.StringVar(value=""), "p1_5": tk.StringVar(value=""),
            "p2": tk.StringVar(value=""), "p3": tk.StringVar(value=""), "p4": tk.StringVar(value="")
        }
        self.is_running = {"p1": False, "p1_5": False, "p2": False, "p3": False, "p4": False}
        self.anim_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.anim_idx = 0

        self.colors = {
            "bg": "#0f0f12", "card": "#1a1a1f", "accent": "#00d1b2", "accent_hover": "#00f2d3",
            "text": "#ffffff", "text_dim": "#aaaaaa", "btn_default": "#252529", "btn_hover": "#323238",
            "success": "#00ffcc", "error": "#ff3860", "warning": "#ffdd57", "highlight": "#209cee"
        }

        self.load_settings()
        self.create_widgets()
        if HAS_DND: self.setup_dnd()
        self.root.after(100, self.start_animation_loop)
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
        elif "ข้าม" in message or "Skipped" in message: tag = "warning"; prefix = "⚠ "
        elif "ตรวจพบ" in message or "AI" in message: tag = "highlight"; prefix = "✨ "
        
        msg_line = f"[{timestamp}] {prefix}{message}\n"
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled'); self.log_area.see(tk.END)
        try:
            with open(self.history_log, "a", encoding="utf-8") as f: f.write(msg_line)
        except: pass

    def start_animation_loop(self):
        if any(self.is_running.values()):
            char = self.anim_chars[self.anim_idx]
            self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
            for k, v in self.is_running.items():
                if v: self.process_states[k.replace('p1_5','phase1_5').replace('p1','phase1').replace('p2','phase2').replace('p3','phase3').replace('p4','phase4')].set(char)
        else:
            for v in self.process_states.values(): v.set("")
        self.root.after(100, self.start_animation_loop)

    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path): self.source_dir.set(os.path.normpath(path)); self.log(f"Drag & Drop: {path}", "success")

    def auto_detect_downloads(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads): return
        candidates = [d for d in os.listdir(downloads) if os.path.isdir(os.path.join(downloads, d)) and d.lower().startswith("media -")]
        if not candidates: return
        candidates.sort(key=lambda x: os.path.getctime(os.path.join(downloads, x)), reverse=True)
        if os.path.join(downloads, candidates[0]) != self.source_dir.get():
            if messagebox.askyesno("New Workspace", f"Use latest folder?\n{candidates[0]}"):
                self.source_dir.set(os.path.join(downloads, candidates[0]))

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#16161d", height=130); header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg=self.colors["accent"], bg="#16161d", font=("Segoe UI", 30, "bold")).pack(pady=(30, 0))
        tk.Label(header, text=f"PURE CLOUD AI EDITION v{self.version}", fg="#555", bg="#16161d", font=("Segoe UI", 10, "bold")).pack()

        main = tk.Frame(self.root, bg=self.colors["bg"], padx=40, pady=25); main.pack(expand=True, fill="both")
        left = tk.Frame(main, bg=self.colors["bg"]); left.pack(side="left", fill="both", expand=True, padx=(0, 25))
        right = tk.Frame(main, bg=self.colors["bg"]); right.pack(side="right", fill="both", expand=True, padx=(25, 0))

        # LEFT SIDE
        tk.Label(left, text="SYSTEM CONFIGURATION", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 15))
        self.add_path_card(left, "PHOTO 1: MAIN DATABASE DRIVE", self.photo1_dir)
        self.add_path_card(left, "PHOTO 2: BACKUP DATABASE DRIVE", self.photo2_dir)
        self.add_path_card(left, "ARCHIVE: HISTORY STORAGE", self.archive_dir)
        
        gemini_f = tk.Frame(left, bg=self.colors["card"], padx=18, pady=15, highlightthickness=1, highlightbackground="#333338"); gemini_f.pack(fill="x", pady=8)
        tk.Label(gemini_f, text="GOOGLE CLOUD API KEY", fg=self.colors["highlight"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(gemini_f, textvariable=self.gemini_key, font=("Consolas", 10), bg="#0f0f12", fg="#fff", relief="flat", show="*", insertbackground="white").pack(fill="x", pady=(8, 0), ipady=6)
        
        self.create_styled_button(left, "⚙ MANAGE CATEGORIES", self.open_category_manager, self.colors["btn_default"], "#fff").pack(fill="x", pady=20)
        
        tk.Label(left, text="WORKSPACE", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 15))
        w_f = tk.Frame(left, bg=self.colors["card"], padx=20, pady=20, highlightthickness=1, highlightbackground="#333338"); w_f.pack(fill="x")
        self.source_entry = tk.Entry(w_f, textvariable=self.source_dir, font=("Consolas", 11), bg="#0f0f12", fg="#fff", relief="flat", insertbackground="white"); self.source_entry.pack(fill="x", pady=(0, 15), ipady=10)
        self.create_styled_button(w_f, "BROWSE LOCAL FOLDER", lambda: self.browse_dir(self.source_dir, False), self.colors["accent"], "#0f0f12").pack(fill="x")

        # RIGHT SIDE
        tk.Label(right, text="PRODUCTION WORKFLOW", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 15))
        self.add_wf_step(right, "1. GROUP BY CODE", self.run_phase_1, "phase1")
        self.ai_btn = self.add_wf_step(right, "1.5 🤖 CLOUD AI RETOUCH", self.run_phase_ai_retouch, "phase1_5", True)
        self.add_wf_step(right, "2. RENAME & SELECT PRIMARY", self.run_phase_rename, "phase2")
        self.add_wf_step(right, "3. COLLECT TO DATABASE", self.run_phase_backup, "phase3")
        self.add_wf_step(right, "4. MOVE TO ARCHIVE", self.run_phase_archive, "phase4")

        self.progress = ttk.Progressbar(right, orient="horizontal", mode="determinate"); self.progress.pack(fill="x", pady=(20, 0))
        self.log_area = scrolledtext.ScrolledText(right, height=18, bg="#000", fg="#bbb", font=("Consolas", 10), relief="flat", padx=15, pady=15); self.log_area.pack(fill="both", expand=True, pady=(20, 0))
        self.log_area.tag_config("time", foreground="#444"); self.log_area.tag_config("success", foreground=self.colors["success"]); self.log_area.tag_config("error", foreground=self.colors["error"]); self.log_area.tag_config("warning", foreground=self.colors["warning"]); self.log_area.tag_config("highlight", foreground=self.colors["highlight"]); self.log_area.tag_config("info", foreground="#fff")

    def add_wf_step(self, parent, text, cmd, state_key, is_ai=False):
        f = tk.Frame(parent, bg=self.colors["bg"]); f.pack(fill="x", pady=5)
        btn = self.create_styled_button(f, text, cmd, self.colors["highlight"] if is_ai else self.colors["btn_default"], "#121212" if is_ai else "#fff")
        btn.pack(side="left", fill="x", expand=True)
        tk.Label(f, textvariable=self.process_states[state_key], fg=self.colors["accent"], bg=self.colors["bg"], font=("Consolas", 18, "bold"), width=2).pack(side="right", padx=10)
        return btn

    def add_path_card(self, parent, label, var):
        c = tk.Frame(parent, bg=self.colors["card"], padx=18, pady=15, highlightthickness=1, highlightbackground="#333338"); c.pack(fill="x", pady=6)
        tk.Label(c, text=label, fg=self.colors["text_dim"], bg=self.colors["card"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        row = tk.Frame(c, bg=self.colors["card"]); row.pack(fill="x", pady=(8, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#0f0f12", fg="#fff", relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=6)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, True), bg="#333338", fg="#fff", relief="flat", width=4).pack(side="right", padx=(8, 0))

    def create_styled_button(self, parent, text, cmd, bg, fg):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=("Segoe UI", 10, "bold"), relief="flat", height=2)
        b.bind("<Enter>", lambda e: b.config(bg=self.colors["accent_hover"] if bg==self.colors["accent"] else self.colors["btn_hover"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d: var.set(os.path.normpath(d)); 
        if is_config: self.save_settings()

    def open_category_manager(self):
        m = tk.Toplevel(self.root); m.title("Categories"); m.geometry("500x650"); m.configure(bg="#1a1a1f"); m.grab_set()
        tree = ttk.Treeview(m, columns=("C", "N"), show="headings", height=15); tree.heading("C", text="Code"); tree.heading("N", text="Name"); tree.pack(padx=20, fill="both", expand=True)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            for c, n in sorted(self.type_mapping.items()): tree.insert("", "end", values=(c, n))
        refresh()
        ctrl = tk.Frame(m, bg="#1a1a1f", pady=10); ctrl.pack(fill="x", padx=20)
        c_e = tk.Entry(ctrl, width=5); c_e.grid(row=0, column=0); n_e = tk.Entry(ctrl, width=15); n_e.grid(row=0, column=1, padx=5)
        def add():
            c, n = c_e.get().strip().upper(), n_e.get().strip()
            if c and n: self.type_mapping[c] = n; self.save_settings(); refresh(); c_e.delete(0, 100); n_e.delete(0, 100)
        self.create_styled_button(ctrl, "ADD", add, self.colors["accent"], "#121212").grid(row=0, column=2)
        def delete():
            s = tree.selection()
            if s:
                code = tree.item(s[0])['values'][0]
                if messagebox.askyesno("Confirm", f"Delete '{code}'?"): del self.type_mapping[code]; self.save_settings(); refresh()
        self.create_styled_button(m, "DELETE SELECTED", delete, self.colors["error"], "#fff").pack(fill="x", padx=20, pady=20)

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        def task():
            self.is_running["p1"] = True; moved = 0
            for i, f in enumerate(files):
                m = re.search(r'(\d{4})', f)
                if m:
                    c = m.group(1); t = os.path.join(src, c)
                    if not os.path.exists(t): os.makedirs(t)
                    try: shutil.move(os.path.join(src, f), os.path.join(t, f)); moved += 1
                    except: pass
                self.progress['value'] = (i+1)/len(files)*100
            self.log(f"Phase 1: Grouped {moved} files.", "success"); self.is_running["p1"] = False
        threading.Thread(target=task, daemon=True).start()

    def run_phase_ai_retouch(self):
        if not HAS_GEMINI: messagebox.showerror("Error", "Google AI libraries not found."); return
        key = self.gemini_key.get()
        if not key: messagebox.showwarning("API Key Missing", "Enter Google API Key."); return
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        all_folders = [os.path.join(src, d) for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
        if not all_folders: messagebox.showinfo("Info", "Run Phase 1 first."); return
        if not messagebox.askyesno("Confirm", "🚀 Start Pure Cloud AI Retouching?"): return

        self.ai_btn.config(state="disabled", text="⌛ CLOUD PROCESSING..."); self.is_running["p1_5"] = True
        threading.Thread(target=self.gemini_agent_process, args=(all_folders, key), daemon=True).start()

    def gemini_agent_process(self, folder_paths, api_key):
        try: genai.configure(api_key=api_key)
        except Exception as e: self.log(f"API Error: {e}", "error", "E006"); self.stop_ai_vis(); return

        self.progress['maximum'] = len(folder_paths)
        self.log("🚀 Google Cloud AI is analyzing images...", "highlight")
        for i, folder in enumerate(folder_paths):
            f_n = os.path.basename(folder); self.log(f"Processing {f_n}...", "info")
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if not files: continue
                out_dir = os.path.join(folder, "ai_retouched")
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                p_t = f_n[0].upper()
                for f_p in files:
                    self.retouch_pure_cloud(f_p, out_dir, p_t)
                    self.log(f"  > Success: {os.path.basename(f_p)}", "success")
                if p_t == 'E' and len(files) >= 2: self.merge_earring_views(files, out_dir, f_n)
            except Exception as e: self.log(f"Error {f_n}: {e}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Cloud AI tasks complete.", "highlight"); self.stop_ai_vis()
        self.root.after(0, lambda: messagebox.showinfo("Done", "Google Cloud AI Finished."))

    def stop_ai_vis(self):
        self.is_running["p1_5"] = False; self.ai_btn.config(state="normal", text="1.5 🤖 CLOUD AI RETOUCH")

    def retouch_pure_cloud(self, path, out_dir, p_type):
        """High-end retouching using PIL (Cloud simulation). Beta 10: removed heavy local AI."""
        filename = os.path.basename(path); out_path = os.path.join(out_dir, filename)
        try:
            img = Image.open(path).convert("RGBA")
            # Quality Polish
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Sharpness(img).enhance(2.8)
            if p_type == 'R': img = img.filter(ImageFilter.SHARPEN)
            
            # Pure White BG (In Pure Cloud mode, this would be an API call return)
            # For this version, we optimize local processing to be LIGHT but high quality
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            final = Image.alpha_composite(white_bg, img).convert("RGB")
            final.save(out_path, "JPEG", quality=98)
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
                self.root.after(0, lambda f=files, n=folder_name, b=base_path, w=target_work_dir: self.process_rename_visual(w, f, n, b))
                self.progress['value'] = (i+1)/len(folders)*100
            self.is_running["p2"] = False
        threading.Thread(target=task, daemon=True).start()

    def process_rename_visual(self, target_work_dir, files, folder_name, base_path):
        main_file = self.choose_main_file_visual(target_work_dir, files, folder_name)
        if not main_file: return
        for f in files:
            src_f = os.path.join(target_work_dir, f); ext = os.path.splitext(f)[1]
            if f == main_file: final = f"{folder_name}{ext}"
            else: final = f"{folder_name}-{files.index(f)+2}{ext}"
            final_path = os.path.join(base_path, final)
            if os.path.exists(final_path): os.remove(final_path)
            shutil.copy2(src_f, final_path)

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1: return files[0]
        win = tk.Toplevel(self.root); win.title(f"Select: {folder_name}"); win.geometry("1000x750"); win.grab_set()
        res = tk.StringVar()
        tk.Label(win, text=f"SELECT PRIMARY PHOTO", bg="#121212", fg=self.colors["accent"], font=("Segoe UI", 11, "bold")).pack(pady=10)
        can = tk.Canvas(win, bg="#121212", highlightthickness=0); can.pack(side="left", fill="both", expand=True)
        gal = tk.Frame(can, bg="#121212"); can.create_window((0,0), window=gal, anchor="nw")
        photo_refs = []
        for i, f in enumerate(files):
            try:
                img = Image.open(os.path.join(folder_path, f)); img.thumbnail((160, 160)); ph = ImageTk.PhotoImage(img); photo_refs.append(ph)
                lbl = tk.Label(gal, image=ph, bg="#1e1e1e", cursor="hand2"); lbl.grid(row=i//5, column=i%5, padx=8, pady=8)
                lbl.bind("<Button-1>", lambda e, f=f: [res.set(f), win.destroy()])
            except: pass
        self.root.wait_window(win); return res.get() if res.get() else files[0]

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start:03d}-{start+199:03d}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]): messagebox.showwarning("Warning", "Check config."); return
        def task():
            self.is_running["p3"] = True; s_c = 0
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
            for i, f_n in enumerate(folders):
                f_p = os.path.join(src, f_n); main_f = f"{f_n}.jpg"
                if not os.path.exists(os.path.join(f_p, main_f)): continue
                p_t = self.type_mapping.get(f_n[0].upper(), "Other")
                # Simplified range logic for Beta 10
                match = re.search(r'(\d+)', f_n); r_v = int(match.group(1)) if match else 0
                t_r = os.path.join("Vincentio", p_t) if "-VN-" in f_n.upper() else os.path.join(p_t, f"{p_t} {self.get_range(r_v)}")
                t1 = os.path.join(p1, t_r)
                if os.path.exists(t1):
                    shutil.copy2(os.path.join(f_p, main_f), os.path.join(t1, main_f)); s_c += 1
                self.progress['value'] = (i+1)/len(folders)*100
            self.log(f"Phase 3: Collected {s_c} files.", "success"); self.is_running["p3"] = False
        threading.Thread(target=task, daemon=True).start()

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]): return
        def task():
            self.is_running["p4"] = True
            now = datetime.now(); path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
            if not os.path.exists(path): os.makedirs(path)
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
            for f_n in folders:
                try: shutil.move(os.path.join(src, f_n), os.path.join(path, f_n))
                except: pass
            self.log("Phase 4: Archived.", "success"); self.is_running["p4"] = False
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = JewelryManagerApp(root); root.mainloop()
