import os
import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk
import difflib

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jewelry Media Manager v1.8 (Robust Edition)")
        self.root.geometry("1150x900")
        self.root.configure(bg="#121212")

        # Config file path
        self.config_dir = os.path.join(os.path.expanduser("~"), ".jewelry_manager")
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        self.config_file = os.path.join(self.config_dir, "config_v1_8.json")
        self.history_log = os.path.join(self.config_dir, "history_log.txt")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()
        self.type_mapping = {}

        self.load_settings()
        self.create_widgets()
        
        if HAS_DND:
            self.setup_dnd()
        
        # Auto-detect Downloads
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
            except: 
                self.type_mapping = default_types
        else:
            self.type_mapping = default_types

    def save_settings(self):
        data = {
            'photo1': self.photo1_dir.get(),
            'photo2': self.photo2_dir.get(),
            'archive': self.archive_dir.get(),
            'types': self.type_mapping
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def log(self, message, category="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        tag = "info"
        prefix = "• "
        if "สำเร็จ" in message or "เสร็จสิ้น" in message: tag = "success"; prefix = "✔ "
        elif "ข้าม" in message or "เตือน" in message or "ไม่พบ" in message: tag = "warning"; prefix = "⚠ "
        elif "Error" in message or "ผิดพลาด" in message: tag = "error"; prefix = "✖ "
        elif "ตรวจพบ" in message: tag = "highlight"; prefix = "✨ "
        
        msg_line = f"[{timestamp}] {prefix}{message}\n"
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)
        with open(self.history_log, "a", encoding="utf-8") as f:
            f.write(msg_line)

    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"Drag & Drop Success: {path}", "success")
        else:
            self.log("Please drag a folder, not a file.", "error")

    def auto_detect_downloads(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads): return
        candidates = [d for d in os.listdir(downloads) if os.path.isdir(os.path.join(downloads, d)) and d.lower().startswith("media -")]
        if not candidates: return
        candidates.sort(key=lambda x: os.path.getctime(os.path.join(downloads, x)), reverse=True)
        newest = os.path.join(downloads, candidates[0])
        if newest != self.source_dir.get():
            if messagebox.askyesno("พบโฟลเดอร์งานใหม่", f"ตรวจพบโฟลเดอร์งานล่าสุดใน Downloads:\n{candidates[0]}\n\nคุณต้องการใช้โฟลเดอร์นี้ใช่หรือไม่?"):
                self.source_dir.set(newest)
                self.log(f"Auto-selected newest work folder: {candidates[0]}", "highlight")

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1f1f1f", height=100)
        header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg="#00d1b2", bg="#1f1f1f", font=("Segoe UI", 26, "bold")).pack(pady=(20, 0))
        tk.Label(header, text="v1.8 - Robust Edition", fg="#555555", bg="#1f1f1f", font=("Segoe UI", 10)).pack()

        main_container = tk.Frame(self.root, bg="#121212", padx=30, pady=20)
        main_container.pack(expand=True, fill="both")

        top_bar = tk.Frame(main_container, bg="#121212")
        top_bar.pack(fill="x", pady=(0, 10))
        tk.Button(top_bar, text="⚙ MANAGE CATEGORIES", command=self.open_category_manager, bg="#333333", fg="#00d1b2", relief="flat", padx=15).pack(side="right")

        left_col = tk.Frame(main_container, bg="#121212"); left_col.pack(side="left", fill="both", expand=True, padx=(0, 15))
        right_col = tk.Frame(main_container, bg="#121212"); right_col.pack(side="right", fill="both", expand=True, padx=(15, 0))

        config_box = tk.LabelFrame(left_col, text=" 🖥️ SYSTEM PATHS ", fg="#00d1b2", bg="#121212", padx=15, pady=15, font=("Segoe UI", 10, "bold"))
        config_box.pack(fill="x", pady=(0, 20))
        self.add_path_row(config_box, "Photo 1 (Main)", self.photo1_dir, True)
        self.add_path_row(config_box, "Photo 2 (Backup)", self.photo2_dir, True)
        self.add_path_row(config_box, "Archive Drive", self.archive_dir, True)

        work_box = tk.LabelFrame(left_col, text=" 📂 CURRENT WORKSPACE ", fg="#00d1b2", bg="#121212", padx=15, pady=15, font=("Segoe UI", 10, "bold"))
        work_box.pack(fill="x")
        self.source_entry = tk.Entry(work_box, textvariable=self.source_dir, font=("Consolas", 11), bg="#1f1f1f", fg="#ffffff", relief="flat", highlightthickness=1, highlightbackground="#333333", insertbackground="white")
        self.source_entry.pack(fill="x", pady=10, ipady=8)
        tk.Button(work_box, text="BROWSE FOLDER", command=lambda: self.browse_dir(self.source_dir, False), bg="#00d1b2", fg="#121212", font=("Segoe UI", 10, "bold"), relief="flat", height=2).pack(fill="x")

        tk.Label(right_col, text="WORKFLOW STEPS", fg="#555555", bg="#121212", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 10))
        btn_style = {"font": ("Segoe UI", 11, "bold"), "relief": "flat", "height": 2, "pady": 5}
        tk.Button(right_col, text="1. GROUP BY CODE (4 DIGITS)", command=self.run_phase_1, bg="#2d2d2d", fg="white", **btn_style).pack(fill="x", pady=2)
        tk.Button(right_col, text="2. RENAME FILES", command=self.run_phase_rename, bg="#2d2d2d", fg="white", **btn_style).pack(fill="x", pady=2)
        tk.Button(right_col, text="3. COLLECT PHOTOS", command=self.run_phase_backup, bg="#00d1b2", fg="#121212", **btn_style).pack(fill="x", pady=2)
        tk.Button(right_col, text="4. MOVE TO ARCHIVE", command=self.run_phase_archive, bg="#2d2d2d", fg="white", **btn_style).pack(fill="x", pady=2)

        self.progress = ttk.Progressbar(right_col, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(20, 0))

        tk.Label(right_col, text="ACTIVITY LOG", fg="#555555", bg="#121212", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(20, 5))
        self.log_area = scrolledtext.ScrolledText(right_col, height=18, bg="#000000", fg="#dddddd", font=("Consolas", 10), relief="flat", padx=10, pady=10)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        self.log_area.tag_config("time", foreground="#444444")
        self.log_area.tag_config("success", foreground="#00ffcc")
        self.log_area.tag_config("error", foreground="#ff3860")
        self.log_area.tag_config("warning", foreground="#ffdd57")
        self.log_area.tag_config("highlight", foreground="#209cee")
        self.log_area.tag_config("info", foreground="#ffffff")

    def add_path_row(self, parent, label_text, var, is_config):
        row = tk.Frame(parent, bg="#121212")
        row.pack(fill="x", pady=5)
        tk.Label(row, text=label_text, width=15, anchor="w", bg="#121212", fg="#888888", font=("Segoe UI", 8, "bold")).pack(side="left")
        entry = tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#1f1f1f", fg="#ffffff", relief="flat", insertbackground="white")
        entry.pack(side="left", expand=True, fill="x", padx=10, ipady=4)
        tk.Button(row, text="...", command=lambda: self.browse_dir(var, is_config), bg="#333333", fg="white", relief="flat", font=("Arial", 10, "bold"), padx=10).pack(side="right")

    def browse_dir(self, var, is_config):
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))
            if is_config: self.save_settings()

    def open_category_manager(self):
        manager = tk.Toplevel(self.root); manager.title("Category Manager"); manager.geometry("500x600"); manager.configure(bg="#1f1f1f"); manager.grab_set()
        tk.Label(manager, text="MANAGE PRODUCT CATEGORIES", fg="#00d1b2", bg="#1f1f1f", font=("Segoe UI", 12, "bold")).pack(pady=20)
        list_frame = tk.Frame(manager, bg="#1f1f1f"); list_frame.pack(fill="both", expand=True, padx=20)
        tree = ttk.Treeview(list_frame, columns=("Code", "Name"), show="headings", height=15)
        tree.heading("Code", text="Code"); tree.heading("Name", text="Category Name"); tree.column("Code", width=100, anchor="center"); tree.pack(side="left", fill="both", expand=True)
        def refresh():
            for item in tree.get_children(): tree.delete(item)
            for code, name in sorted(self.type_mapping.items()): tree.insert("", "end", values=(code, name))
        refresh()
        ctrl_frame = tk.Frame(manager, bg="#1f1f1f", pady=20); ctrl_frame.pack(fill="x", padx=20)
        tk.Label(ctrl_frame, text="Code:", bg="#1f1f1f", fg="white").grid(row=0, column=0, padx=5)
        c_ent = tk.Entry(ctrl_frame, width=5); c_ent.grid(row=0, column=1, padx=5)
        tk.Label(ctrl_frame, text="Name:", bg="#1f1f1f", fg="white").grid(row=0, column=2, padx=5)
        n_ent = tk.Entry(ctrl_frame, width=20); n_ent.grid(row=0, column=3, padx=5)
        def add():
            c, n = c_ent.get().strip().upper(), n_ent.get().strip()
            if c and n: self.type_mapping[c] = n; self.save_settings(); refresh(); c_ent.delete(0, tk.END); n_ent.delete(0, tk.END)
        def delete():
            sel = tree.selection()
            if sel:
                code = tree.item(sel[0])['values'][0]
                if messagebox.askyesno("Confirm", f"Delete '{code}'?"): del self.type_mapping[code]; self.save_settings(); refresh()
        tk.Button(ctrl_frame, text="ADD / UPDATE", command=add, bg="#00d1b2", fg="#1e1e1e", relief="flat", padx=10).grid(row=0, column=4, padx=5)
        tk.Button(manager, text="DELETE SELECTED", command=delete, bg="#ff3860", fg="white", relief="flat", height=2).pack(fill="x", padx=20, pady=(0, 20))

    def find_fuzzy_folders(self, base_path, target_name):
        if not os.path.exists(base_path): return []
        existing_folders = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        return difflib.get_close_matches(target_name, existing_folders, n=3, cutoff=0.7)

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src): return
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        self.progress['maximum'] = len(files); moved = 0
        for i, f in enumerate(files):
            match = re.search(r'(\d{4})', f)
            if match:
                code = match.group(1); target = os.path.join(src, code)
                if not os.path.exists(target): os.makedirs(target)
                shutil.move(os.path.join(src, f), os.path.join(target, f)); moved += 1
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log(f"Phase 1 Complete: Grouped {moved} files.", "success")
        messagebox.showinfo("Done", "Files grouped.")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, folder_name in enumerate(folders):
            path = os.path.join(src, folder_name)
            files = sorted([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            if not files: continue
            
            # Improvement 3: UI Selection for Main File
            main_file = self.choose_main_file(path, files, folder_name)
            if not main_file: continue

            # Rename to temp
            temp_files = []
            for f in files:
                temp = f"temp_{f}"; os.rename(os.path.join(path, f), os.path.join(path, temp)); temp_files.append(temp)
            
            # Rename to final
            counter = 2
            for temp in temp_files:
                ext = os.path.splitext(temp)[1]
                if temp == f"temp_{main_file}": final = f"{folder_name}{ext}"
                else: final = f"{folder_name}-{counter}{ext}"; counter += 1
                os.rename(os.path.join(path, temp), os.path.join(path, final))
            
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Phase 2 Complete: Files renamed.", "success")

    def choose_main_file(self, folder_path, files, folder_name):
        # Auto-detect max index first
        max_idx = -1; suggested = files[-1]
        for f in files:
            m = re.search(r'_(\d+)\.', f)
            if m and int(m.group(1)) > max_idx: max_idx = int(m.group(1)); suggested = f
        
        # Simple selection dialog if more than 1 file
        if len(files) <= 1: return files[0]
        
        win = tk.Toplevel(self.root); win.title(f"Select Main File for {folder_name}"); win.geometry("600x400"); win.grab_set()
        choice = tk.StringVar(value=suggested)
        tk.Label(win, text=f"Choose primary photo for {folder_name}:", bg="#1f1f1f", fg="white", pady=10).pack()
        lb = tk.Listbox(win, font=("Consolas", 10), bg="#000000", fg="#ffffff", selectbackground="#00d1b2")
        lb.pack(expand=True, fill="both", padx=20, pady=10)
        for f in files: lb.insert(tk.END, f)
        lb.select_set(files.index(suggested))
        def ok(): choice.set(lb.get(lb.curselection())); win.destroy()
        tk.Button(win, text="CONFIRM SELECTION", command=ok, bg="#00d1b2", relief="flat", height=2).pack(fill="x", padx=20, pady=10)
        self.root.wait_window(win); return choice.get()

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
                
                # Fuzzy Match Improvement
                if not os.path.exists(t1_dir):
                    matches = self.find_fuzzy_folders(os.path.dirname(t1_dir), os.path.basename(t1_dir))
                    if matches:
                        match_win = tk.Toplevel(self.root); match_win.title("Fuzzy Match Selection"); match_win.geometry("400x300"); match_win.grab_set()
                        selected_match = tk.StringVar(value=matches[0])
                        tk.Label(match_win, text=f"Folder not found: {os.path.basename(t1_dir)}\nChoose best match:").pack(pady=10)
                        for m in matches: tk.Radiobutton(match_win, text=m, variable=selected_match, value=m).pack(anchor="w", padx=50)
                        def confirm_match(): match_win.destroy()
                        tk.Button(match_win, text="USE SELECTED", command=confirm_match).pack(pady=10)
                        self.root.wait_window(match_win)
                        t1_dir = os.path.join(os.path.dirname(t1_dir), selected_match.get())
                        t2_dir = os.path.join(p2, target_rel_dir.replace(os.path.basename(t1_dir), selected_match.get()))
                
                if not os.path.exists(t1_dir):
                    msg = f"{folder_name}: [Photo 1 Folder Missing]"; self.log(msg, "error"); errors.append(msg); skipped_count += 1; continue

                # Clean-up All Suffixes Logic
                base_code = folder_name.upper()
                alt_suffix = "-SC0" if "-S00" in base_code else "-S00" if "-SC0" in base_code else None
                alt_code = base_code.replace("-S00", "-SC0") if "-S00" in base_code else base_code.replace("-SC0", "-S00") if "-SC0" in base_code else None

                old_files_p1 = [os.path.join(t1_dir, f) for f in os.listdir(t1_dir) if os.path.splitext(f)[0].upper() in [base_code, alt_code]]
                old_files_p2 = [os.path.join(t2_dir, f) for f in os.listdir(t2_dir) if os.path.exists(t2_dir) and os.path.splitext(f)[0].upper() in [base_code, alt_code]]

                if self.show_preview(old_files_p1[0] if old_files_p1 else None, old_files_p2[0] if old_files_p2 else None, os.path.join(folder_path, main_file), target_rel_dir):
                    try:
                        for f in old_files_p1: os.remove(f)
                        shutil.copy2(os.path.join(folder_path, main_file), os.path.join(t1_dir, main_file))
                        if os.path.exists(t2_dir):
                            for f in old_files_p2: os.remove(f)
                            shutil.copy2(os.path.join(folder_path, main_file), os.path.join(t2_dir, main_file))
                        success_count += 1; self.log(f"Success: {folder_name}", "success")
                    except Exception as e:
                        self.log(f"Error {folder_name}: {str(e)}", "error"); errors.append(f"{folder_name}: {str(e)}")
                else: skipped_count += 1
            self.progress['value'] = i + 1; self.root.update_idletasks()
        
        summary = f"Results:\n- Success: {success_count}\n- Skipped/Error: {skipped_count}"
        if errors: messagebox.showwarning("Summary", summary + "\n\nErrors:\n" + "\n".join(errors))
        else: messagebox.showinfo("Summary", summary)

    def run_phase_archive(self):
        src, arc = self.source_dir.get(), self.archive_dir.get()
        if not all([src, arc]): return
        self.log("--- Starting Phase 4: Archive ---", "info")
        now = datetime.now()
        archive_path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(archive_path): os.makedirs(archive_path)
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        self.progress['maximum'] = len(folders)
        for i, folder_name in enumerate(folders):
            src_p = os.path.join(src, folder_name); dst_p = os.path.join(archive_path, folder_name)
            if os.path.exists(dst_p): dst_p = f"{dst_p}_{datetime.now().strftime('%H%M%S')}"
            try: shutil.move(src_p, dst_p); self.log(f"Archived: {folder_name}")
            except Exception as e: self.log(f"Error: {str(e)}", "error")
            self.progress['value'] = i + 1; self.root.update_idletasks()
        self.log("Archive Complete.", "success"); messagebox.showinfo("Done", "Archived.")

    def show_preview(self, p1, p2, new, dest):
        dialog = tk.Toplevel(self.root); dialog.title("Preview"); dialog.geometry("1000x700"); dialog.configure(bg="#121212"); dialog.grab_set()
        res = tk.BooleanVar(value=False)
        tk.Label(dialog, text=f"DESTINATION: {dest}", fg="#00ffcc", bg="#1e1e1e", pady=10, font=("Consolas", 10)).pack(fill="x")
        grid = tk.Frame(dialog, bg="#121212", padx=20, pady=20); grid.pack(expand=True, fill="both")
        def add_box(parent, p, title):
            box = tk.Frame(parent, bg="#121212"); box.pack(side="left", expand=True, fill="both")
            tk.Label(box, text=title, fg="#888888", bg="#121212", font=("Segoe UI", 10, "bold")).pack(pady=5)
            if p and os.path.exists(p):
                img = Image.open(p); img.thumbnail((300, 300)); ph = ImageTk.PhotoImage(img)
                l = tk.Label(box, image=ph, bg="#1e1e1e"); l.image = ph; l.pack()
                tk.Label(box, text=os.path.basename(p), fg="#444444", bg="#121212", font=("Arial", 8)).pack()
            else: tk.Label(box, text="[ NOT FOUND ]", fg="#333333", bg="#121212", font=("Segoe UI", 12, "bold")).pack(pady=120)
        add_box(grid, p1, "PHOTO 1"); add_box(grid, p2, "PHOTO 2"); add_box(grid, new, "NEW FILE")
        btn_f = tk.Frame(dialog, bg="#1e1e1e", pady=20); btn_f.pack(side="bottom", fill="x")
        tk.Button(btn_f, text="REPLACE PHOTOS", bg="#00d1b2", fg="#121212", font=("Segoe UI", 12, "bold"), width=25, height=2, command=lambda: [res.set(True), dialog.destroy()]).pack(side="left", padx=50)
        tk.Button(btn_f, text="SKIP", bg="#333333", fg="white", width=20, height=2, command=dialog.destroy).pack(side="right", padx=50)
        self.root.wait_window(dialog); return res.get()

if __name__ == "__main__":
    if HAS_DND: root = TkinterDnD.Tk()
    else: root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
