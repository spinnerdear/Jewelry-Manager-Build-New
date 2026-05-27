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
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk, ImageEnhance, ImageOps
import threading
import time

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')

try:
    from google import genai as google_genai
    HAS_GEMINI_IMAGE = True
except ImportError:
    HAS_GEMINI_IMAGE = False

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class PixUpApp:
    def __init__(self, root):
        self.root = root
        self.version = "2.1 Beta 4"
        self.root.title(f"PixUp v{self.version}")

        self.root.geometry("1200x950")
        self.root.configure(bg="#0f0f12")

        # Memory for AI tasks and Earring status
        self.ai_tasks = {} # folder_path: {"files": [f1, f2], "is_earring": True/False}

        # Centralized Error Codes
        self.error_codes = {
            "E001": "เส้นทางที่ระบุไม่ถูกต้องหรือหาไม่พบ (Path Not Found)",
            "E002": "ไม่พบไฟล์รูปภาพในโฟลเดอร์ต้นทาง (File Not Found)",
            "E003": "ไม่มีสิทธิ์เข้าถึงไฟล์ (Permission Denied)",
            "E005": "ไดรฟ์ปลายทางไม่ได้เชื่อมต่อ (Drive Offline)",
            "E006": "เชื่อมต่อระบบ Cloud AI ล้มเหลว (Check Internet/API Key)",
            "E007": "เกิดปัญหาขณะก๊อปปี้ไฟล์",
            "E999": "เกิดข้อผิดพลาดภายในระบบ"
        }

        # Config file path
        self.config_dir = os.path.join(os.path.expanduser("~"), ".pixup")
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "config_v2_1.json")
        self.history_log = os.path.join(self.config_dir, "history_log.txt")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()
        self.gemini_key = tk.StringVar(value=os.environ.get("GOOGLE_API_KEY", ""))
        self.type_mapping = {}

        # QC FIX: Standards mapping keys for animations
        self.process_states = {
            "phase1": tk.StringVar(value=""),
            "phase1_5": tk.StringVar(value=""),
            "phase1_6": tk.StringVar(value=""),
            "phase1_7": tk.StringVar(value=""),
            "phase2": tk.StringVar(value=""),
            "phase3": tk.StringVar(value=""),
            "phase4": tk.StringVar(value="")
        }
        self.is_running = {"phase1": False, "phase1_5": False, "phase1_6": False, "phase1_7": False, "phase2": False, "phase3": False, "phase4": False}
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
            except Exception as e:
                self.type_mapping = default_types
                print(f"Failed to load settings: {e}")
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

    def set_ai_button(self, state, text):
        self.root.after(0, lambda: self.ai_btn.config(state=state, text=text))

    def is_image_file(self, filename):
        return filename.lower().endswith(IMAGE_EXTENSIONS)

    def start_animation_loop(self):
        if any(self.is_running.values()):
            char = self.anim_chars[self.anim_idx]
            self.anim_idx = (self.anim_idx + 1) % len(self.anim_chars)
            for k, v in self.is_running.items():
                if v: 
                    self.process_states[k].set(char)
                    # If any of the AI sub-phases are running, update the combined state
                    if k in ["phase1_5", "phase1_6", "phase1_7"]:
                        self.ai_combined_state.set(char)
        else:
            for v in self.process_states.values(): v.set("")
            self.ai_combined_state.set("")
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
        tk.Label(header, text="PIXUP", fg=self.colors["accent"], bg="#16161d", font=("Segoe UI", 30, "bold")).pack(pady=(30, 0))
        tk.Label(header, text=f"KH CREATION STUDIO | CLOUD AI {self.version}", fg="#555", bg="#16161d", font=("Segoe UI", 10, "bold")).pack()

        main = tk.Frame(self.root, bg=self.colors["bg"], padx=40, pady=25); main.pack(expand=True, fill="both")
        left = tk.Frame(main, bg=self.colors["bg"]); left.pack(side="left", fill="both", expand=True, padx=(0, 25))
        right = tk.Frame(main, bg=self.colors["bg"]); right.pack(side="right", fill="both", expand=True, padx=(25, 0))

        # --- LEFT: CONFIG ---
        tk.Label(left, text="SYSTEM CONFIGURATION", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 15))
        self.add_path_card(left, "PHOTO 1: MAIN DATABASE DRIVE", self.photo1_dir)
        self.add_path_card(left, "PHOTO 2: BACKUP DATABASE DRIVE", self.photo2_dir)
        self.add_path_card(left, "ARCHIVE: HISTORY STORAGE", self.archive_dir)
        
        gemini_f = tk.Frame(left, bg=self.colors["card"], padx=18, pady=15, highlightthickness=1, highlightbackground="#333338"); gemini_f.pack(fill="x", pady=8)
        tk.Label(gemini_f, text="GOOGLE CLOUD API KEY", fg=self.colors["highlight"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Entry(gemini_f, textvariable=self.gemini_key, font=("Consolas", 10), bg="#0f0f12", fg="#fff", relief="flat", show="*", insertbackground="white").pack(fill="x", pady=(8, 0), ipady=6)
        
        self.create_styled_button(left, "⚙ MANAGE CATEGORIES", self.open_category_manager, self.colors["btn_default"], "#fff").pack(fill="x", pady=20)
        
        tk.Label(left, text="WORKSPACE SELECTOR", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 15))
        w_f = tk.Frame(left, bg=self.colors["card"], padx=20, pady=20, highlightthickness=1, highlightbackground="#333338"); w_f.pack(fill="x")
        self.source_entry = tk.Entry(w_f, textvariable=self.source_dir, font=("Consolas", 11), bg="#0f0f12", fg="#fff", relief="flat", highlightthickness=1, highlightbackground="#444", insertbackground="white"); self.source_entry.pack(fill="x", pady=(0, 15), ipady=10)
        self.create_styled_button(w_f, "BROWSE LOCAL FOLDER", lambda: self.browse_dir(self.source_dir, False), self.colors["accent"], "#0f0f12").pack(fill="x")

        # --- RIGHT: WORKFLOW ---
        tk.Label(right, text="PRODUCTION WORKFLOW", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 15))
        self.add_wf_step(right, "1. GROUP BY CODE", self.run_phase_1, "phase1")
        
        # Combined AI Row (1.5, 1.6, 1.7)
        ai_f = tk.Frame(right, bg=self.colors["bg"]); ai_f.pack(fill="x", pady=5)
        ai_btns_container = tk.Frame(ai_f, bg=self.colors["bg"]); ai_btns_container.pack(side="left", fill="x", expand=True)
        
        self.ai_btn = self.create_styled_button(ai_btns_container, "1.5 🤖 AI", self.run_phase_ai_retouch, self.colors["highlight"], "#121212")
        self.ai_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.merge_btn = self.create_styled_button(ai_btns_container, "1.6 🔗 MERGE", self.run_phase_interactive_merge, "#a362ff", "#fff")
        self.merge_btn.pack(side="left", fill="x", expand=True, padx=2)
        self.crop_btn = self.create_styled_button(ai_btns_container, "1.7 ✂️ CROP", self.run_phase_interactive_crop, "#ff9f43", "#000")
        self.crop_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))
        
        # Shared progress label for AI tools to align with other rows
        self.ai_combined_state = tk.StringVar(value="")
        tk.Label(ai_f, textvariable=self.ai_combined_state, fg=self.colors["accent"], bg=self.colors["bg"], font=("Consolas", 18, "bold"), width=2).pack(side="right", padx=10)

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

        # QC SAFE ACCESS: Check if state_key exists in process_states
        state_var = self.process_states.get(state_key)
        if state_var:
            tk.Label(f, textvariable=state_var, fg=self.colors["accent"], bg=self.colors["bg"], font=("Consolas", 18, "bold"), width=2).pack(side="right", padx=10)
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
        if d: var.set(os.path.normpath(d))
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
        self.create_styled_button(m, "DELETE", delete, self.colors["error"], "#fff").pack(fill="x", padx=20, pady=20)

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"])
            return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        if not files:
            messagebox.showinfo("Info", self.error_codes["E002"])
            return
        def task():
            self.set_running("phase1", True); moved = 0
            for i, f in enumerate(files):
                m = re.search(r'(\d{4})', f)
                if m:
                    c = m.group(1); t = os.path.join(src, c)
                    if not os.path.exists(t): os.makedirs(t)
                    try:
                        shutil.move(os.path.join(src, f), os.path.join(t, f)); moved += 1
                    except Exception as e:
                        self.log_threadsafe(f"Move failed for {f}: {e}", "error", "E007")
                self.set_progress_threadsafe((i+1)/len(files)*100)
            self.log_threadsafe(f"Phase 1: Grouped {moved} files.", "success"); self.set_running("phase1", False)
        threading.Thread(target=task, daemon=True).start()

    def run_phase_ai_retouch(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"])
            return
        
        self.log("Phase 1.5: Scanning folders for AI Retouch...", "info")
        folders = sorted([os.path.join(src, d) for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"])
        if not folders: 
            self.log("Phase 1.5: No folders found. Please run Phase 1 first.", "warning")
            messagebox.showinfo("Info", "Run Phase 1 first.")
            return

        # Step 1: Visual Selection
        self.log("Phase 1.5: Opening Visual Selector...", "info")
        self.ai_tasks = self.open_visual_ai_selector(folders)
        if not self.ai_tasks: 
            self.log("Phase 1.5: Selection cancelled by user.", "warning")
            return 

        # Step 2: Processing
        key = self.gemini_key.get().strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
        if not key: 
            self.log("Phase 1.5: API Key is missing.", "error")
            messagebox.showwarning("API Key Missing", "Enter Google API Key.")
            return
        
        self.log(f"Phase 1.5: Starting Cloud AI for {len(self.ai_tasks)} items...", "highlight")
        self.set_ai_button("disabled", "⌛ PROCESSING...")
        self.set_running("phase1_5", True)
        threading.Thread(target=self.gemini_agent_process, args=(key,), daemon=True).start()

    def open_visual_ai_selector(self, folder_paths):
        win = tk.Toplevel(self.root); win.title("AI PHOTO SELECTOR"); win.geometry("1100x850"); win.grab_set()
        win.configure(bg="#0f0f12")
        
        tk.Label(win, text="SELECT PHOTOS FOR AI RETOUCH (MAX 2 PER FOLDER)", bg="#0f0f12", fg=self.colors["accent"], font=("Segoe UI", 12, "bold")).pack(pady=15)
        
        container = tk.Frame(win, bg="#0f0f12"); container.pack(fill="both", expand=True, padx=20)
        canvas = tk.Canvas(container, bg="#0f0f12", highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview); scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scroll_f = tk.Frame(canvas, bg="#0f0f12"); canvas.create_window((0,0), window=scroll_f, anchor="nw")
        scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        tasks = {} # folder_path: [selected_files]
        photo_refs = {} # To keep references to PhotoImage objects

        for f_path in folder_paths:
            f_name = os.path.basename(f_path)
            row = tk.Frame(scroll_f, bg="#1a1a1f", pady=10, padx=10, highlightthickness=1, highlightbackground="#333"); row.pack(fill="x", pady=5)
            tk.Label(row, text=f_name, bg="#1a1a1f", fg="#aaa", font=("Consolas", 10, "bold"), width=15, anchor="w").pack(side="left", padx=10)
            
            img_container = tk.Frame(row, bg="#1a1a1f"); img_container.pack(side="left", fill="x", expand=True)
            
            files = sorted([f for f in os.listdir(f_path) if self.is_image_file(f)])
            tasks[f_path] = []
            
            for f in files:
                try:
                    full_p = os.path.join(f_path, f)
                    img = Image.open(full_p); img.thumbnail((120, 120)); ph = ImageTk.PhotoImage(img)
                    photo_refs[full_p] = ph
                    
                    btn = tk.Label(img_container, image=ph, bg="#1a1a1f", borderwidth=2, relief="flat", cursor="hand2")
                    btn.pack(side="left", padx=4)
                    
                    def toggle(f_p=f_path, fn=f, b=btn):
                        if fn in tasks[f_p]:
                            tasks[f_p].remove(fn)
                            b.config(relief="flat", bg="#1a1a1f", highlightthickness=0)
                        else:
                            if len(tasks[f_p]) < 2:
                                tasks[f_p].append(fn)
                                b.config(relief="solid", bg=self.colors["accent"], highlightthickness=2, highlightbackground=self.colors["accent"])
                            else:
                                messagebox.showwarning("Limit", "Max 2 photos per folder.")
                    
                    btn.bind("<Button-1>", lambda e, f_p=f_path, fn=f, b=btn: toggle(f_p, fn, b))
                except: pass

        confirmed = tk.BooleanVar(value=False)
        def on_ok():
            # Filter out empty tasks
            final_tasks = {k: {"files": v, "is_earring": len(v)==2} for k, v in tasks.items() if v}
            if not final_tasks:
                messagebox.showwarning("Warning", "Please select at least one photo.")
                return
            tasks.clear(); tasks.update(final_tasks)
            confirmed.set(True); win.destroy()

        tk.Button(win, text="CONFIRM & START AI RETOUCH", command=on_ok, bg=self.colors["accent"], fg="#000", font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x", side="bottom", padx=20, pady=20)
        
        self.root.wait_window(win)
        return tasks if confirmed.get() else None

    def gemini_agent_process(self, api_key):
        # Calculate total files across all selected tasks
        total_files = sum(len(info["files"]) for info in self.ai_tasks.values())
        processed_files = 0
        
        self.set_progress_threadsafe(0, total_files)
        self.log_threadsafe(f"AI is performing image retouching on {total_files} files...", "highlight")
        
        for folder_path, info in self.ai_tasks.items():
            f_n = os.path.basename(folder_path)
            try:
                for f_p in info["files"]:
                    # NEW: Throttling to stay within 15 RPM (approx 4s between requests)
                    if processed_files > 0:
                        self.log_threadsafe(f"    • Waiting 3.5s to avoid Rate Limit...", "info")
                        time.sleep(3.5)

                    processed_files += 1
                    file_path = os.path.join(folder_path, f_p)
                    self.log_threadsafe(f"[{processed_files}/{total_files}] Processing: {f_p} in {f_n}...", "info")
                    
                    success, err_msg, is_critical = self.retouch_with_gemini_image(file_path, folder_path, "X", api_key)
                    
                    if success:
                        self.log_threadsafe(f"  > Gemini Image Retouched: {f_p}", "success")
                    else:
                        self.log_threadsafe(f"  > AI Failed for {f_p}: {err_msg}", "error")
                        if is_critical:
                            self.log_threadsafe("Critical AI error occurred. Stopping process.", "error")
                            self.root.after(0, lambda m=err_msg: messagebox.showerror("AI Critical Error", f"กระบวนการหยุดทำงานเนื่องจากข้อผิดพลาดร้ายแรง:\n\n{m}"))
                            self.stop_ai_vis(); return
                    
                    self.set_progress_threadsafe(processed_files)
            except Exception as e: 
                self.log_threadsafe(f"Error in folder {f_n}: {e}", "error")
            
        self.log_threadsafe("Advanced AI Retouching complete.", "highlight"); self.stop_ai_vis()
        self.root.after(0, lambda: messagebox.showinfo("Done", "AI Advanced Retouching Finished. Go to Step 1.6 to Merge Earrings or 1.7 to Crop."))

    def run_phase_interactive_merge(self):
        self.log("Phase 1.6: Filtering earring folders for merge...", "info")
        earring_folders = [k for k, v in self.ai_tasks.items() if v.get("is_earring", False)]
        if not earring_folders:
            self.log("Phase 1.6: No earring tasks found. (Select 2 photos in Phase 1.5 first)", "warning")
            messagebox.showinfo("Info", "No earring tasks found. Ensure you selected 2 photos in Phase 1.5.")
            return

        def task():
            self.log(f"Phase 1.6: Starting Interactive Merge for {len(earring_folders)} folders...", "highlight")
            self.set_running("phase1_6", True)
            for i, f_path in enumerate(earring_folders):
                f_n = os.path.basename(f_path)
                selected_files = self.ai_tasks[f_path]["files"]
                # AI files are named name_AI.ext
                ai_files = []
                for f in selected_files:
                    name_p, ext = os.path.splitext(f)
                    ai_p = os.path.join(f_path, f"{name_p}_AI{ext}")
                    if os.path.exists(ai_p): ai_files.append(ai_p)
                
                if len(ai_files) < 2:
                    self.log_threadsafe(f"Skipping {f_n}: AI files not found.", "warning")
                    continue
                
                self.log_threadsafe(f"Merging Earring: {f_n} ({i+1}/{len(earring_folders)})", "info")
                self.root.after(0, lambda p=ai_files, d=f_path, n=f_n, idx=i+1, total=len(earring_folders): 
                               self.open_interactive_merge_ui(p, d, n, idx, total))
                # We need to wait for the UI to close before next folder
                # This is tricky in a thread, we'll use a threading event
                self.merge_done_event = threading.Event()
                self.merge_done_event.wait()
            
            self.set_running("phase1_6", False)
            self.log_threadsafe("Earring Merge Process Finished.", "success")
        
        threading.Thread(target=task, daemon=True).start()

    def open_interactive_merge_ui(self, ai_paths, out_dir, folder_name, current, total):
        win = tk.Toplevel(self.root); win.title(f"MERGE EARRING: {folder_name} ({current}/{total})"); win.geometry("1100x850"); win.grab_set()
        win.configure(bg="#0f0f12")

        # Workspace Data
        img_paths = list(ai_paths)
        scales = [tk.DoubleVar(value=1.0), tk.DoubleVar(value=1.0)]
        
        # UI Layout
        tk.Label(win, text=f"EARING MERGE TOOL - {folder_name}", bg="#0f0f12", fg=self.colors["accent"], font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        canvas = tk.Canvas(win, width=800, height=800, bg="white", highlightthickness=1, highlightbackground="#444")
        canvas.pack(pady=10)
        
        ctrl = tk.Frame(win, bg="#0f0f12"); ctrl.pack(fill="x", padx=20)
        
        def refresh_canvas():
            canvas.delete("all")
            try:
                # Create 2000x2000 composite in memory
                comp = Image.new('RGB', (2000, 2000), (255, 255, 255))
                for i, p in enumerate(img_paths):
                    im = Image.open(p).convert("RGBA")
                    # Calculate size
                    base_size = 900
                    new_w = int(base_size * scales[i].get())
                    im.thumbnail((new_w, new_w), Image.Resampling.LANCZOS)
                    
                    x = 50 + (1000 if i == 1 else 0) + (900 - im.width) // 2
                    y = (2000 - im.height) // 2
                    comp.paste(im, (x, y), im)
                
                # Show preview
                preview = comp.copy()
                preview.thumbnail((800, 800))
                ph = ImageTk.PhotoImage(preview)
                canvas.image = ph # Keep ref
                canvas.create_image(0, 0, image=ph, anchor="nw")
                return comp
            except Exception as e: print(f"Refresh Error: {e}")

        # Controls
        s_f = tk.Frame(ctrl, bg="#0f0f12"); s_f.pack(side="left", padx=20)
        tk.Label(s_f, text="LEFT SCALE", bg="#0f0f12", fg="#fff", font=("Segoe UI", 8)).pack()
        tk.Scale(s_f, from_=0.5, to=1.5, resolution=0.05, variable=scales[0], orient="horizontal", bg="#0f0f12", fg="#fff", highlightthickness=0, command=lambda e: refresh_canvas()).pack()
        
        s_f2 = tk.Frame(ctrl, bg="#0f0f12"); s_f2.pack(side="left", padx=20)
        tk.Label(s_f2, text="RIGHT SCALE", bg="#0f0f12", fg="#fff", font=("Segoe UI", 8)).pack()
        tk.Scale(s_f2, from_=0.5, to=1.5, resolution=0.05, variable=scales[1], orient="horizontal", bg="#0f0f12", fg="#fff", highlightthickness=0, command=lambda e: refresh_canvas()).pack()

        def swap():
            img_paths[0], img_paths[1] = img_paths[1], img_paths[0]
            scales[0].set(scales[1].get()) # Optional: swap scales too? User might prefer it.
            refresh_canvas()

        tk.Button(ctrl, text="⇄ SWAP", command=swap, bg="#333", fg="#fff", width=10).pack(side="left", padx=10)
        
        def save_and_next():
            final = refresh_canvas()
            final.save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95, optimize=True)
            win.destroy()
            self.merge_done_event.set()

        tk.Button(win, text="SAVE & NEXT →", command=save_and_next, bg=self.colors["success"], fg="#000", font=("Segoe UI", 12, "bold"), pady=10).pack(fill="x", padx=100, pady=20)
        
        win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), self.merge_done_event.set()])
        refresh_canvas()

    def run_phase_interactive_crop(self):
        self.log("Phase 1.7: Filtering AI-retouched files for cropping...", "info")
        # Identify non-earring files that have been AI retouched
        crop_tasks = []
        for folder_path, info in self.ai_tasks.items():
            if not info.get("is_earring", False):
                for f in info["files"]:
                    name_p, ext = os.path.splitext(f)
                    ai_p = os.path.join(folder_path, f"{name_p}_AI{ext}")
                    if os.path.exists(ai_p):
                        crop_tasks.append((ai_p, folder_path, f"{name_p}_AI{ext}"))
        
        if not crop_tasks:
            self.log("Phase 1.7: No AI-retouched photos found for cropping.", "warning")
            messagebox.showinfo("Info", "No AI-retouched photos found for cropping (excluding earrings).")
            return

        def task():
            self.log(f"Phase 1.7: Starting Interactive Crop for {len(crop_tasks)} files...", "highlight")
            self.set_running("phase1_7", True)
            for i, (ai_path, out_dir, filename) in enumerate(crop_tasks):
                self.log_threadsafe(f"Cropping: {filename} ({i+1}/{len(crop_tasks)})", "info")
                self.root.after(0, lambda p=ai_path, d=out_dir, n=filename, idx=i+1, total=len(crop_tasks): 
                               self.open_interactive_crop_ui(p, d, n, idx, total))
                self.crop_done_event = threading.Event()
                self.crop_done_event.wait()
            
            self.set_running("phase1_7", False)
            self.log_threadsafe("Image Cropping Process Finished.", "success")
        
        threading.Thread(target=task, daemon=True).start()

    def open_interactive_crop_ui(self, img_path, out_dir, filename, current, total):
        win = tk.Toplevel(self.root); win.title(f"CROP IMAGE: {filename} ({current}/{total})"); win.geometry("1100x900"); win.grab_set()
        win.configure(bg="#0f0f12")

        # Workspace Data
        scale = tk.DoubleVar(value=1.0)
        off_x = tk.IntVar(value=0)
        off_y = tk.IntVar(value=0)
        
        tk.Label(win, text=f"IMAGE CROP & POSITION - {filename}", bg="#0f0f12", fg=self.colors["accent"], font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        canvas = tk.Canvas(win, width=800, height=800, bg="white", highlightthickness=1, highlightbackground="#444")
        canvas.pack(pady=10)
        
        ctrl = tk.Frame(win, bg="#0f0f12"); ctrl.pack(fill="x", padx=40)
        
        def refresh_canvas():
            canvas.delete("all")
            try:
                # Create 2000x2000 composite
                comp = Image.new('RGB', (2000, 2000), (255, 255, 255))
                im = Image.open(img_path).convert("RGBA")
                
                # Calculate size based on scale
                base_size = 1800
                new_w = int(base_size * scale.get())
                im.thumbnail((new_w, new_w), Image.Resampling.LANCZOS)
                
                # Calculate center position + offsets
                x = (2000 - im.width) // 2 + off_x.get()
                y = (2000 - im.height) // 2 + off_y.get()
                
                comp.paste(im, (x, y), im)
                
                # Show preview
                preview = comp.copy()
                preview.thumbnail((800, 800))
                ph = ImageTk.PhotoImage(preview)
                canvas.image = ph
                canvas.create_image(0, 0, image=ph, anchor="nw")
                return comp
            except Exception as e: print(f"Refresh Error: {e}")

        # Controls Row 1: Scale
        row1 = tk.Frame(ctrl, bg="#0f0f12"); row1.pack(fill="x", pady=5)
        tk.Label(row1, text="ZOOM (SCALE)", bg="#0f0f12", fg="#fff", width=15).pack(side="left")
        tk.Scale(row1, from_=0.1, to=3.0, resolution=0.05, variable=scale, orient="horizontal", bg="#0f0f12", fg="#fff", highlightthickness=0, command=lambda e: refresh_canvas()).pack(side="left", fill="x", expand=True)

        # Controls Row 2: X Offset
        row2 = tk.Frame(ctrl, bg="#0f0f12"); row2.pack(fill="x", pady=5)
        tk.Label(row2, text="MOVE X (LEFT/RIGHT)", bg="#0f0f12", fg="#fff", width=15).pack(side="left")
        tk.Scale(row2, from_=-1000, to=1000, variable=off_x, orient="horizontal", bg="#0f0f12", fg="#fff", highlightthickness=0, command=lambda e: refresh_canvas()).pack(side="left", fill="x", expand=True)

        # Controls Row 3: Y Offset
        row3 = tk.Frame(ctrl, bg="#0f0f12"); row3.pack(fill="x", pady=5)
        tk.Label(row3, text="MOVE Y (UP/DOWN)", bg="#0f0f12", fg="#fff", width=15).pack(side="left")
        tk.Scale(row3, from_=-1000, to=1000, variable=off_y, orient="horizontal", bg="#0f0f12", fg="#fff", highlightthickness=0, command=lambda e: refresh_canvas()).pack(side="left", fill="x", expand=True)

        def save_and_next():
            final = refresh_canvas()
            # Overwrite the AI file or save as cropped? Let's overwrite as it's the "final" version for this stage
            final.save(img_path, "JPEG", quality=95, optimize=True)
            win.destroy()
            self.crop_done_event.set()

        tk.Button(win, text="SAVE & NEXT →", command=save_and_next, bg=self.colors["success"], fg="#000", font=("Segoe UI", 12, "bold"), pady=10).pack(fill="x", padx=100, pady=20)
        
        win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), self.crop_done_event.set()])
        refresh_canvas()

    def retouch_with_gemini_image(self, path, out_dir, p_type, api_key):
        if not HAS_GEMINI_IMAGE:
            return False, "Google GenAI library missing", True

        filename = os.path.basename(path)
        name_p, ext = os.path.splitext(filename)
        out_path = os.path.join(out_dir, f"{name_p}_AI{ext}")
        
        max_retries = 4
        retry_delay = 4 # Initial delay in seconds

        for attempt in range(max_retries + 1):
            try:
                self.log_threadsafe(f"    • Connecting to Google Cloud AI (Attempt {attempt+1}/{max_retries+1})...", "info")
                client = google_genai.Client(api_key=api_key)
                
                # NEW: Image Optimization - Smaller resolution and convert to RGB
                self.log_threadsafe(f"    • Optimizing & Uploading image...", "info")
                img = Image.open(path).convert("RGB")
                # Optimization: Target 1200px (still high quality but saves 40% tokens vs 1600px)
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

                prompt = (
                    "Edit this jewelry product photo into a premium e-commerce studio image. "
                    "Keep the exact same jewelry design, stone count, gemstone color, metal color, proportions, and viewing angle. "
                    "Do not invent, remove, or reshape stones, prongs, engraving, shank, hooks, or any jewelry details. "
                    "Cleanly remove the background and replace it with pure white (#ffffff). "
                    "Brighten the jewelry naturally, preserve highlights, recover shadow detail, and avoid making the metal or stones darker. "
                    "Remove dust, fingerprints, gray cast, yellow cast, and small photography artifacts. "
                    "For rings, keep the shank crisp but anatomically faithful to the source. "
                    "For earrings, remove hanging fixtures only if they are not part of the product. "
                    "Return one final retouched product image only."
                )

                self.version = "2.1 Beta 9"

                self.log_threadsafe(f"    • AI is processing (gemini-2.5-flash with code execution)...", "highlight")
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, img],
                    config={
                        "tools": [{"code_execution": {}}],
                        "system_instruction": "You are a professional jewelry retoucher. "
                        "You will be provided with an image. "
                        "Your task is to retouch the jewelry, remove the background (replace with pure white #ffffff), "
                        "brighten the metal/stones, and return the final image result in the response. "
                    }
                )



                # DEBUG: Print full response to log area
                self.log_threadsafe(f"    DEBUG: API Response -> {response}", "info")

                self.log_threadsafe(f"    • Receiving and saving image...", "info")

                for part in response.parts:
                    if getattr(part, "inline_data", None) is not None:
                        edited = part.as_image()
                        # Optimization: Save with 85 quality to save disk and keep high fidelity
                        edited.save(out_path, "JPEG", quality=85, optimize=True)
                        return True, "", False

                return False, "Gemini returned no image data", False

            except Exception as e:
                err_str = str(e)
                is_critical = False
                friendly_err = err_str

                # NEW: Exponential Backoff for Rate Limits (429)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if attempt < max_retries:
                        self.log_threadsafe(f"    ⚠ Rate Limit hit. Retrying in {retry_delay}s...", "warning")
                        time.sleep(retry_delay)
                        retry_delay *= 2 # Exponential increase
                        continue
                    else:
                        friendly_err = "โควต้าการใช้งานเต็มแล้ว (Quota Exceeded). ลองใหม่อีกครั้งพรุ่งนี้หรือเปลี่ยน API Key"
                        is_critical = True
                elif "401" in err_str or "API_KEY_INVALID" in err_str:
                    friendly_err = "API Key ไม่ถูกต้อง (Invalid API Key). กรุณาตรวจสอบ Key ของคุณ"
                    is_critical = True
                elif "400" in err_str:
                    friendly_err = "คำขอไม่ถูกต้อง (Bad Request). อาจเกิดจากขนาดไฟล์หรือรูปแบบรูปภาพที่ไม่รองรับ"
                elif "500" in err_str or "503" in err_str:
                    friendly_err = "เซิร์ฟเวอร์ Google มีปัญหา (Server Error). กรุณาลองใหม่ภายหลัง"
                elif "DNS" in err_str or "connection" in err_str.lower():
                    friendly_err = "ปัญหาการเชื่อมต่ออินเทอร์เน็ต (Network Error). กรุณาตรวจสอบเน็ตของคุณ"
                    is_critical = True

                return False, friendly_err, is_critical

    def stop_ai_vis(self):
        self.set_running("phase1_5", False); self.set_ai_button("normal", "1.5 🤖 AI")

    def merge_earring_views(self, files, out_dir, folder_name):
        try:
            imgs = [Image.open(f) for f in files[:2]]
            composite = Image.new('RGB', (2400, 1200), (255, 255, 255))
            for i, im in enumerate(imgs):
                im.thumbnail((1100, 1100))
                x = 100 if i == 0 else 1300; y = (1200 - im.height) // 2
                composite.paste(im, (x, y))
            composite.save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=90, optimize=True)
        except Exception as e:
            self.log_threadsafe(f"Earring montage failed for {folder_name}: {e}", "error", "E999")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"])
            return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d != "ai_retouched"]
        if not folders:
            messagebox.showinfo("Info", "No folders found. Run Phase 1 first.")
            return
        def task():
            self.set_running("phase2", True)
            for i, folder_name in enumerate(folders):
                base_path = os.path.join(src, folder_name)
                files = sorted([f for f in os.listdir(base_path) if self.is_image_file(f)])
                if files: self.root.after(0, lambda f=files, n=folder_name, b=base_path: self.process_rename_visual(b, f, n, b))
                self.set_progress_threadsafe((i+1)/len(folders)*100)
            self.set_running("phase2", False)
        threading.Thread(target=task, daemon=True).start()

    def process_rename_visual(self, work_dir, files, folder_name, base_path):
        main_file = self.choose_main_file_visual(work_dir, files, folder_name)
        if not main_file: return
        temp_dir = os.path.join(base_path, "_rename_temp")
        if os.path.exists(temp_dir):
            self.log(f"Rename temp folder already exists for {folder_name}; skipped to avoid overwriting recovery files.", "error", "E007")
            return
        try:
            os.makedirs(temp_dir)
            planned_names = {}
            counter = 2
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                final = f"{folder_name}{ext}" if f == main_file else f"{folder_name}-{counter}{ext}"
                if f != main_file: counter += 1
                planned_names[f] = final

            for f in files:
                shutil.move(os.path.join(base_path, f), os.path.join(temp_dir, f))

            for original, final in planned_names.items():
                final_path = os.path.join(base_path, final)
                if os.path.exists(final_path):
                    os.replace(final_path, os.path.join(temp_dir, f"existing_{final}"))
                shutil.copy2(os.path.join(temp_dir, original), final_path)

            shutil.rmtree(temp_dir)
            self.log(f"Renamed: {folder_name}", "success")
        except Exception as e:
            self.log(f"Rename failed for {folder_name}: {e}. Recovery files remain in _rename_temp.", "error", "E007")

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1: return files[0]
        win = tk.Toplevel(self.root); win.title(f"Select: {folder_name}"); win.geometry("1000x750"); win.grab_set(); res = tk.StringVar()
        tk.Label(win, text=f"PICK PRIMARY PHOTO", bg="#121212", fg=self.colors["accent"], font=("Segoe UI", 11, "bold")).pack(pady=10)
        can = tk.Canvas(win, bg="#121212", highlightthickness=0); can.pack(side="left", fill="both", expand=True)
        gal = tk.Frame(can, bg="#121212"); can.create_window((0,0), window=gal, anchor="nw")
        photo_refs = []
        for i, f in enumerate(files):
            try:
                img = Image.open(os.path.join(folder_path, f)); img.thumbnail((160, 160)); ph = ImageTk.PhotoImage(img); photo_refs.append(ph)
                lbl = tk.Label(gal, image=ph, bg="#1e1e1e", cursor="hand2"); lbl.grid(row=i//5, column=i%5, padx=8, pady=8)
                lbl.bind("<Button-1>", lambda e, f=f: [res.set(f), win.destroy()])
            except Exception as e:
                self.log(f"Preview skipped for {f}: {e}", "warning")
        self.root.wait_window(win); return res.get() if res.get() else files[0]

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start:03d}-{start+199:03d}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]): messagebox.showwarning("Warning", "Check config."); return
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
                if not files_to_copy: continue
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
                self.set_progress_threadsafe((i+1)/len(folders)*100)
            self.log_threadsafe(f"Phase 3: Collected {s_c} files.", "success"); self.set_running("phase3", False)
        threading.Thread(target=task, daemon=True).start()

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]) or not os.path.exists(src):
            messagebox.showerror("Error", self.error_codes["E001"])
            return
        def task():
            self.set_running("phase4", True)
            now = datetime.now(); path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
            os.makedirs(path, exist_ok=True)
            folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
            for f_n in folders:
                try:
                    shutil.move(os.path.join(src, f_n), os.path.join(path, f_n))
                except Exception as e:
                    self.log_threadsafe(f"Archive failed for {f_n}: {e}", "error", "E007")
            self.log_threadsafe("Phase 4: Archived.", "success"); self.set_running("phase4", False)
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = PixUpApp(root); root.mainloop()
