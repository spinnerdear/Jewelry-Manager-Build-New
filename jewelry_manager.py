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

# AI and Image Processing support
try:
    from rembg import remove
    import cv2
    import numpy as np
    HAS_AI_LIBS = True
except ImportError:
    HAS_AI_LIBS = False

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.version = "2.0 Beta 1"
        self.root.title(f"Jewelry Media Manager v{self.version}")
        self.root.geometry("1200x950")
        self.root.configure(bg="#121212")

        # Config file path
        self.config_dir = os.path.join(os.path.expanduser("~"), ".jewelry_manager")
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "config_v1_9.json")
        self.history_log = os.path.join(self.config_dir, "history_log.txt")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()
        self.type_mapping = {}

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
        
        if HAS_DND:
            self.setup_dnd()
        
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
                    self.type_mapping = data.get('types', default_types)
            except: self.type_mapping = default_types
        else: self.type_mapping = default_types

    def save_settings(self):
        data = {'photo1': self.photo1_dir.get(), 'photo2': self.photo2_dir.get(), 'archive': self.archive_dir.get(), 'types': self.type_mapping}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def log(self, message, category="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        tag = "info"; prefix = "• "
        if "สำเร็จ" in message or "Success" in message: tag = "success"; prefix = "✔ "
        elif "ข้าม" in message or "Skipped" in message or "ไม่พบ" in message: tag = "warning"; prefix = "⚠ "
        elif "Error" in message or "ผิดพลาด" in message: tag = "error"; prefix = "✖ "
        elif "ตรวจพบ" in message or "Highlight" in message: tag = "highlight"; prefix = "✨ "
        
        msg_line = f"[{timestamp}] {prefix}{message}\n"
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)
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
        # Header
        header = tk.Frame(self.root, bg="#1a1a1f", height=120)
        header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg=self.colors["accent"], bg="#1a1a1f", font=("Segoe UI", 28, "bold")).pack(pady=(25, 0))
        tk.Label(header, text=f"PROFESSIONAL VERSION {self.version}", fg=self.colors["text_dim"], bg="#1a1a1f", font=("Segoe UI", 10)).pack()

        main_container = tk.Frame(self.root, bg=self.colors["bg"], padx=40, pady=30)
        main_container.pack(expand=True, fill="both")

        # Sidebar & Content Split
        left_side = tk.Frame(main_container, bg=self.colors["bg"])
        left_side.pack(side="left", fill="both", expand=True, padx=(0, 20))
        right_side = tk.Frame(main_container, bg=self.colors["bg"])
        right_side.pack(side="right", fill="both", expand=True, padx=(20, 0))

        # --- LEFT SIDE: CONFIGURATION ---
        tk.Label(left_side, text="CONFIGURATION", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Path Cards
        self.add_path_card(left_side, "PHOTO 1 (MAIN DATABASE)", self.photo1_dir, True)
        self.add_path_card(left_side, "PHOTO 2 (BACKUP DATABASE)", self.photo2_dir, True)
        self.add_path_card(left_side, "ARCHIVE DRIVE", self.archive_dir, True)
        
        # Categories Button
        cat_btn = self.create_styled_button(left_side, "⚙ MANAGE CATEGORIES", self.open_category_manager, self.colors["btn_default"], self.colors["accent"])
        cat_btn.pack(fill="x", pady=20)

        # Workspace Card
        tk.Label(left_side, text="WORKSPACE", fg=self.colors["accent"], bg=self.colors["bg"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 15))
        work_frame = tk.Frame(left_side, bg=self.colors["card"], padx=20, pady=20, highlightthickness=1, highlightbackground="#333333")
        work_frame.pack(fill="x")
        self.source_entry = tk.Entry(work_frame, textvariable=self.source_dir, font=("Consolas", 11), bg="#121212", fg="#ffffff", relief="flat", highlightthickness=1, highlightbackground="#444444", insertbackground="white")
        self.source_entry.pack(fill="x", pady=(0, 15), ipady=10)
        self.create_styled_button(work_frame, "BROWSE FOLDER", lambda: self.browse_dir(self.source_dir, False), self.colors["accent"], "#121212").pack(fill="x")

        # --- RIGHT SIDE: STEPS & LOGS ---
        tk.Label(right_side, text="WORKFLOW PROGRESS", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.create_styled_button(right_side, "1. GROUP BY CODE (4 DIGITS)", self.run_phase_1, "#2d2d2d", "white").pack(fill="x", pady=4)
        
        # New AI Retouch Button
        self.ai_btn = self.create_styled_button(right_side, "1.5 🤖 AI RETOUCH IMAGES", self.run_phase_ai_retouch, self.colors["highlight"], "#121212")
        self.ai_btn.pack(fill="x", pady=4)

        self.create_styled_button(right_side, "2. RENAME FILES", self.run_phase_rename, "#2d2d2d", "white").pack(fill="x", pady=4)
        self.create_styled_button(right_side, "3. COLLECT PHOTOS", self.run_phase_backup, "#2d2d2d", "white").pack(fill="x", pady=4)
        self.create_styled_button(right_side, "4. MOVE TO ARCHIVE", self.run_phase_archive, "#2d2d2d", "white").pack(fill="x", pady=4)

        self.progress = ttk.Progressbar(right_side, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(20, 0))

        tk.Label(right_side, text="ACTIVITY LOG", fg=self.colors["text_dim"], bg=self.colors["bg"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(25, 5))
        self.log_area = scrolledtext.ScrolledText(right_side, height=20, bg="#000000", fg="#dddddd", font=("Consolas", 10), relief="flat", padx=15, pady=15)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        self.log_area.tag_config("time", foreground="#444444")
        self.log_area.tag_config("success", foreground=self.colors["success"])
        self.log_area.tag_config("error", foreground=self.colors["error"])
        self.log_area.tag_config("warning", foreground=self.colors["warning"])
        self.log_area.tag_config("highlight", foreground=self.colors["highlight"])
        self.log_area.tag_config("info", foreground="#ffffff")

    def create_styled_button(self, parent, text, cmd, bg_color, fg_color):
        btn = tk.Button(parent, text=text, command=cmd, bg=bg_color, fg=fg_color, font=("Segoe UI", 10, "bold"), relief="flat", height=2)
        def on_enter(e): 
            if bg_color == self.colors["accent"]: btn.config(bg=self.colors["accent_hover"])
            else: btn.config(bg=self.colors["btn_hover"])
        def on_leave(e): btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def add_path_card(self, parent, label, var, is_config):
        card = tk.Frame(parent, bg=self.colors["card"], padx=15, pady=12, highlightthickness=1, highlightbackground="#333333")
        card.pack(fill="x", pady=5)
        tk.Label(card, text=label, fg=self.colors["text_dim"], bg=self.colors["card"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card, bg=self.colors["card"])
        row.pack(fill="x", pady=(5, 0))
        tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#121212", fg="#ffffff", relief="flat", insertbackground="white").pack(side="left", expand=True, fill="x", ipady=5)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, is_config), bg="#333333", fg="white", relief="flat", width=4).pack(side="right", padx=(5, 0))

    def browse_dir(self, var, is_config):
        d = filedialog.askdirectory()
        if d:
            var.set(os.path.normpath(d))
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
        tk.Label(ctrl, text="CODE:", bg="#1a1a1f", fg="white").grid(row=0, column=0); c_ent = tk.Entry(ctrl, width=5); c_ent.grid(row=0, column=1, padx=5)
        tk.Label(ctrl, text="NAME:", bg="#1a1a1f", fg="white").grid(row=0, column=2); n_ent = tk.Entry(ctrl, width=15); n_ent.grid(row=0, column=3, padx=5)
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
        if not HAS_AI_LIBS:
            messagebox.showerror("Error", "AI Libraries not found.\nPlease install: pip install rembg opencv-python numpy pillow onnxruntime")
            return
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        
        all_images = []
        for root, dirs, files in os.walk(src):
            if "ai_retouched" in root: continue
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg')): all_images.append(os.path.join(root, f))
        
        if not all_images: messagebox.showinfo("Info", "No images to retouch."); return
        if not messagebox.askyesno("Confirm", f"Process {len(all_images)} images with AI?\nThis may take some time."): return

        self.ai_btn.config(state="disabled")
        threading.Thread(target=self.ai_retouch_process, args=(all_images,), daemon=True).start()

    def ai_retouch_process(self, image_paths):
        self.progress['maximum'] = len(image_paths)
        success_count = 0
        self.log("🚀 Starting AI Retouching...", "highlight")
        
        for i, path in enumerate(image_paths):
            try:
                folder = os.path.dirname(path); filename = os.path.basename(path)
                out_dir = os.path.join(folder, "ai_retouched")
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                out_path = os.path.join(out_dir, filename)

                # 1. Background Removal
                self.log(f"Processing: {filename}...", "info")
                with open(path, 'rb') as f: input_data = f.read()
                output_data = remove(input_data)
                
                # 2. Enhancement
                img = Image.open(io.BytesIO(output_data)).convert("RGBA")
                white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(white_bg, img).convert("RGB")

                # Sharpness & Contrast (Turbo Enhancement)
                img = ImageEnhance.Sharpness(img).enhance(2.5) 
                img = ImageEnhance.Contrast(img).enhance(1.3)
                
                # Shank Reconstruction (Simulated via localized sharpening)
                # In Beta 1, we boost overall clarity; specialized Inpainting will come in Beta 2
                
                img.save(out_path, "JPEG", quality=95)
                success_count += 1; self.log(f"Success: {filename}", "success")
            except Exception as e: self.log(f"Error {filename}: {e}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()

        self.log(f"AI Complete: {success_count} images processed.", "highlight")
        self.ai_btn.config(state="normal")
        self.root.after(0, lambda: messagebox.showinfo("Done", f"AI Retouching Finished!\nProcessed {success_count} images."))

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, folder_name in enumerate(folders):
            path = os.path.join(src, folder_name)
            files = sorted([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            if not files: continue
            
            # --- IMPROVEMENT: VISUAL PHOTO SELECTION ---
            main_file = self.choose_main_file_visual(path, files, folder_name)
            if not main_file: continue

            temp_files = []
            for f in files:
                temp = f"temp_{f}"; os.rename(os.path.join(path, f), os.path.join(path, temp)); temp_files.append(temp)
            
            counter = 2
            for temp in temp_files:
                ext = os.path.splitext(temp)[1]
                if temp == f"temp_{main_file}": final = f"{folder_name}{ext}"
                else: final = f"{folder_name}-{counter}{ext}"; counter += 1
                os.rename(os.path.join(path, temp), os.path.join(path, final))
            
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Phase 2 Complete: Files renamed.", "success")

    def choose_main_file_visual(self, folder_path, files, folder_name):
        if len(files) <= 1: return files[0]
        
        # Suggestion Logic
        max_idx = -1; suggested = files[-1]
        for f in files:
            m = re.search(r'_(\d+)\.', f)
            if m and int(m.group(1)) > max_idx: max_idx = int(m.group(1)); suggested = f
        
        # Visual Gallery Dialog
        win = tk.Toplevel(self.root); win.title(f"Select Primary Photo: {folder_name}"); win.geometry("900x700"); win.configure(bg="#121212"); win.grab_set()
        result = tk.StringVar(value="")

        tk.Label(win, text=f"SELECT PRIMARY PHOTO FOR: {folder_name}", fg=self.colors["accent"], bg="#121212", font=("Segoe UI", 12, "bold")).pack(pady=20)
        
        scroll_frame = tk.Frame(win, bg="#121212")
        scroll_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_frame, bg="#121212", highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview); scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        gallery = tk.Frame(canvas, bg="#121212")
        canvas.create_window((0, 0), window=gallery, anchor="nw")
        
        def on_click(f): result.set(f); win.destroy()

        cols = 3; r, c = 0, 0
        photo_refs = [] # To prevent GC
        
        for f in files:
            try:
                img = Image.open(os.path.join(folder_path, f)); img.thumbnail((250, 250))
                ph = ImageTk.PhotoImage(img)
                photo_refs.append(ph)
                
                f_frame = tk.Frame(gallery, bg="#1e1e1e", padx=10, pady=10, highlightthickness=2, highlightbackground="#333333")
                f_frame.grid(row=r, column=c, padx=15, pady=15)
                
                lbl = tk.Label(f_frame, image=ph, bg="#1e1e1e", cursor="hand2")
                lbl.pack()
                lbl.bind("<Button-1>", lambda e, f=f: on_click(f))
                
                name_lbl = tk.Label(f_frame, text=f, fg="white", bg="#1e1e1e", font=("Arial", 8), width=25)
                name_lbl.pack(pady=(5, 0))
                
                if f == suggested:
                    f_frame.config(highlightbackground=self.colors["accent"])
                    tk.Label(f_frame, text="SUGGESTED", fg=self.colors["accent"], bg="#1e1e1e", font=("Arial", 7, "bold")).pack()

                # Hover Effects for gallery frames
                def on_gal_enter(e, fr=f_frame): fr.config(highlightbackground="#555555")
                def on_gal_leave(e, fr=f_frame, is_sug=(f==suggested)): 
                    fr.config(highlightbackground=self.colors["accent"] if is_sug else "#333333")
                f_frame.bind("<Enter>", on_gal_enter); f_frame.bind("<Leave>", on_gal_leave)
                lbl.bind("<Enter>", on_gal_enter); lbl.bind("<Leave>", on_gal_leave)

                c += 1
                if c >= cols: c = 0; r += 1
            except: pass

        gallery.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        self.root.wait_window(win)
        return result.get() if result.get() else suggested

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start}-{start+199}"

    def run_phase_backup(self):
        src, p1, p2 = self.source_dir.get(), self.photo1_dir.get(), self.photo2_dir.get()
        if not all([src, p1, p2]): return
        self.log("--- Starting Phase 3: Collect Photos ---", "info")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders); errors = []; success_count = 0; skipped_count = 0
        
        for i, folder_name in enumerate(folders):
            folder_path = os.path.join(src, folder_name)
            main_file = None
            for f in os.listdir(folder_path):
                if os.path.splitext(f)[0] == folder_name: main_file = f; break
            
            if main_file:
                p_type = self.type_mapping.get(folder_name[0].upper(), "Other")
                if "-VN-" in folder_name.upper(): target_rel_dir = os.path.join("Vincentio", p_type)
                else:
                    num_match = re.search(r'(\d+)', folder_name)
                    range_str = self.get_range(int(num_match.group(1))) if num_match else "Unknown"
                    target_rel_dir = os.path.join(p_type, f"{p_type} {range_str}")
                
                t1_dir = os.path.join(p1, target_rel_dir); t2_dir = os.path.join(p2, target_rel_dir)
                
                if not os.path.exists(t1_dir):
                    matches = difflib.get_close_matches(os.path.basename(t1_dir), os.listdir(os.path.dirname(t1_dir)) if os.path.exists(os.path.dirname(t1_dir)) else [], n=3, cutoff=0.7)
                    if matches:
                        match_win = tk.Toplevel(self.root); match_win.title("Match Selection"); match_win.geometry("400x300"); match_win.grab_set()
                        sel = tk.StringVar(value=matches[0])
                        tk.Label(match_win, text=f"Folder not found. Choose best match:").pack(pady=10)
                        for m in matches: tk.Radiobutton(match_win, text=m, variable=sel, value=m).pack(anchor="w", padx=50)
                        tk.Button(match_win, text="USE SELECTED", command=match_win.destroy).pack(pady=10); self.root.wait_window(match_win)
                        t1_dir = os.path.join(os.path.dirname(t1_dir), sel.get())
                        t2_dir = os.path.join(p2, target_rel_dir.replace(os.path.basename(t1_dir), sel.get()))

                if not os.path.exists(t1_dir):
                    msg = f"{folder_name}: [Photo 1 Missing]"; self.log(msg, "error"); errors.append(msg); skipped_count += 1; continue

                base_code = folder_name.upper()
                alt_code = base_code.replace("-S00", "-SC0") if "-S00" in base_code else base_code.replace("-SC0", "-S00") if "-SC0" in base_code else None
                old_p1_files = [os.path.join(t1_dir, f) for f in os.listdir(t1_dir) if os.path.splitext(f)[0].upper() in [base_code, alt_code]]
                old_p2_files = [os.path.join(t2_dir, f) for f in os.listdir(t2_dir) if os.path.exists(t2_dir) and os.path.splitext(f)[0].upper() in [base_code, alt_code]]

                if self.show_preview(old_p1_files[0] if old_p1_files else None, old_p2_files[0] if old_p2_files else None, os.path.join(folder_path, main_file), target_rel_dir):
                    try:
                        for f in old_p1_files: os.remove(f)
                        shutil.copy2(os.path.join(folder_path, main_file), os.path.join(t1_dir, main_file))
                        if os.path.exists(t2_dir):
                            for f in old_p2_files: os.remove(f)
                            shutil.copy2(os.path.join(folder_path, main_file), os.path.join(t2_dir, main_file))
                        success_count += 1; self.log(f"Success: {folder_name}", "success")
                    except Exception as e: self.log(f"Error {folder_name}: {e}", "error"); errors.append(f"{folder_name}: {e}")
                else: skipped_count += 1
            self.progress['value'] = i + 1; self.root.update_idletasks()
        
        summary = f"Done!\n- Success: {success_count}\n- Skipped: {skipped_count}"
        messagebox.showwarning("Summary", summary + "\n\nErrors:\n" + "\n".join(errors)) if errors else messagebox.showinfo("Summary", summary)

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]): return
        now = datetime.now(); path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(path): os.makedirs(path)
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, f_name in enumerate(folders):
            src_p = os.path.join(src, f_name); dst_p = os.path.join(path, f_name)
            if os.path.exists(dst_p): dst_p = f"{dst_p}_{datetime.now().strftime('%H%M%S')}"
            try: shutil.move(src_p, dst_p); self.log(f"Archived: {f_name}")
            except Exception as e: self.log(f"Error: {e}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()
        messagebox.showinfo("Done", "Archived.")

    def show_preview(self, p1, p2, new, dest):
        dialog = tk.Toplevel(self.root); dialog.title("Preview Comparison"); dialog.geometry("1000x750"); dialog.configure(bg="#121212"); dialog.grab_set()
        res = tk.BooleanVar(value=False)
        tk.Label(dialog, text=f"DESTINATION: {dest}", fg=self.colors["accent"], bg="#1e1e1e", pady=12, font=("Consolas", 10, "bold")).pack(fill="x")
        grid = tk.Frame(dialog, bg="#121212", padx=20, pady=20); grid.pack(expand=True, fill="both")
        def add_box(parent, p, title):
            box = tk.Frame(parent, bg="#121212"); box.pack(side="left", expand=True, fill="both")
            tk.Label(box, text=title, fg=self.colors["text_dim"], bg="#121212", font=("Segoe UI", 10, "bold")).pack(pady=5)
            if p and os.path.exists(p):
                img = Image.open(p); img.thumbnail((300, 300)); ph = ImageTk.PhotoImage(img)
                l = tk.Label(box, image=ph, bg="#1e1e1e", highlightthickness=1, highlightbackground="#333333"); l.image = ph; l.pack()
                tk.Label(box, text=os.path.basename(p), fg="#555555", bg="#121212", font=("Arial", 8)).pack(pady=5)
            else: tk.Label(box, text="[ NOT FOUND ]", fg="#333333", bg="#121212", font=("Segoe UI", 12, "bold")).pack(pady=130)
        add_box(grid, p1, "PHOTO 1 (CURRENT)"); add_box(grid, p2, "PHOTO 2 (CURRENT)"); add_box(grid, new, "NEW PHOTO")
        btn_f = tk.Frame(dialog, bg="#1e1e1e", pady=30); btn_f.pack(side="bottom", fill="x")
        self.create_styled_button(btn_f, "REPLACE PHOTOS", lambda: [res.set(True), dialog.destroy()], self.colors["accent"], "#121212").pack(side="left", padx=100, expand=True, fill="x")
        self.create_styled_button(btn_f, "SKIP ITEM", dialog.destroy, "#333333", "white").pack(side="right", padx=100, expand=True, fill="x")
        self.root.wait_window(dialog); return res.get()

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
