import os
import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageTk

# สำหรับ Drag and Drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jewelry Media Manager v1.4")
        self.root.geometry("1100x850")
        self.root.configure(bg="#1e1e1e") # Dark Theme

        # Config file path
        self.config_file = os.path.join(os.path.expanduser("~"), "jewelry_manager_config.json")

        # Variables
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()

        self.type_mapping = {
            'R': 'Ring',
            'N': 'Necklace',
            'E': 'Earring',
            'P': 'Pendant',
            'B': 'Bracelet',
            'S': 'Sets'
        }

        self.load_settings()
        self.create_widgets()
        
        if HAS_DND:
            self.setup_dnd()

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.photo1_dir.set(data.get('photo1', ''))
                    self.photo2_dir.set(data.get('photo2', ''))
                    self.archive_dir.set(data.get('archive', ''))
            except: pass

    def save_settings(self):
        data = {
            'photo1': self.photo1_dir.get(),
            'photo2': self.photo2_dir.get(),
            'archive': self.archive_dir.get()
        }
        with open(self.config_file, 'w') as f:
            json.dump(data, f)

    def log(self, message, category="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        
        tag = "info"
        prefix = "• "
        if "สำเร็จ" in message or "เสร็จสิ้น" in message: 
            tag = "success"
            prefix = "✔ "
        elif "ข้าม" in message or "เตือน" in message or "ไม่พบ" in message: 
            tag = "warning"
            prefix = "⚠ "
        elif "Error" in message or "ผิดพลาด" in message: 
            tag = "error"
            prefix = "✖ "
        elif "ตรวจพบ" in message: 
            tag = "highlight"
            prefix = "✨ "
        
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, f"{prefix}{message}\n", tag)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}').strip('"')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"โหลดโฟลเดอร์สำเร็จ: {path}", "success")
        else:
            self.log("กรุณาลากเฉพาะโฟลเดอร์มาวาง", "error")

    def create_widgets(self):
        # Modern UI Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        
        # Header
        header = tk.Frame(self.root, bg="#2d2d2d", height=100)
        header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg="#00d1b2", bg="#2d2d2d", 
                 font=("Segoe UI", 24, "bold")).pack(pady=(20, 5))
        tk.Label(header, text="v1.4 - Professional Edition", fg="#888888", bg="#2d2d2d", 
                 font=("Segoe UI", 10)).pack()

        main_container = tk.Frame(self.root, bg="#1e1e1e", padx=40, pady=20)
        main_container.pack(expand=True, fill="both")

        # Layout: Left (Inputs) & Right (Actions/Logs)
        left_col = tk.Frame(main_container, bg="#1e1e1e")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        # Section: Configuration
        config_box = tk.LabelFrame(left_col, text=" SYSTEM CONFIGURATION ", fg="#00d1b2", bg="#1e1e1e", padx=15, pady=15, font=("Segoe UI", 10, "bold"))
        config_box.pack(fill="x", pady=(0, 20))
        
        self.add_path_row(config_box, "PHOTO 1 (MAIN)", self.photo1_dir, True)
        self.add_path_row(config_box, "PHOTO 2 (BACKUP)", self.photo2_dir, True)
        self.add_path_row(config_box, "ARCHIVE DRIVE", self.archive_dir, True)

        # Section: Source Folder
        source_box = tk.LabelFrame(left_col, text=" WORKSPACE ", fg="#00d1b2", bg="#1e1e1e", padx=15, pady=15, font=("Segoe UI", 10, "bold"))
        source_box.pack(fill="x")
        
        tk.Label(source_box, text="DRAG & DROP FOLDER HERE", font=("Segoe UI", 9), bg="#1e1e1e", fg="#666666").pack(anchor="w", pady=(0, 5))
        src_row = tk.Frame(source_box, bg="#1e1e1e")
        src_row.pack(fill="x")
        self.source_entry = tk.Entry(src_row, textvariable=self.source_dir, font=("Consolas", 10), bg="#2d2d2d", fg="#ffffff", insertbackground="white", relief="flat", highlightthickness=1, highlightbackground="#3d3d3d")
        self.source_entry.pack(side="left", expand=True, fill="x", padx=(0, 10), ipady=8)
        
        tk.Button(src_row, text="BROWSE", command=lambda: self.browse_dir(self.source_dir, False), 
                  bg="#00d1b2", fg="#1e1e1e", font=("Segoe UI", 9, "bold"), relief="flat", padx=15).pack(side="right")

        # Right Column
        right_col = tk.Frame(main_container, bg="#1e1e1e")
        right_col.pack(side="right", fill="both", expand=True)

        # Section: Actions
        tk.Label(right_col, text="WORKFLOW STEPS", font=("Segoe UI", 10, "bold"), bg="#1e1e1e", fg="#888888").pack(anchor="w", pady=(0, 10))
        
        btn_frame = tk.Frame(right_col, bg="#1e1e1e")
        btn_frame.pack(fill="x")

        def create_btn(parent, text, cmd, color):
            btn = tk.Button(parent, text=text, command=cmd, bg=color, fg="white", 
                            font=("Segoe UI", 11, "bold"), relief="flat", height=2)
            btn.pack(fill="x", pady=5)
            return btn

        create_btn(btn_frame, "1. GROUP BY CODE (4 DIGITS)", self.run_phase_1, "#4a4a4a")
        create_btn(btn_frame, "2. RENAME FILES", self.run_phase_rename, "#4a4a4a")
        create_btn(btn_frame, "3. COLLECT PHOTOS", self.run_phase_backup, "#00d1b2")
        create_btn(btn_frame, "4. MOVE TO ARCHIVE", self.run_phase_archive, "#4a4a4a")

        # Section: Logs
        tk.Label(right_col, text="ACTIVITY LOG", font=("Segoe UI", 10, "bold"), bg="#1e1e1e", fg="#888888").pack(anchor="w", pady=(20, 5))
        self.log_area = scrolledtext.ScrolledText(right_col, height=15, bg="#000000", fg="#cccccc", font=("Consolas", 9), 
                                                 relief="flat", highlightthickness=1, highlightbackground="#3d3d3d", padx=10, pady=10)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        
        # Log Tags
        self.log_area.tag_config("time", foreground="#555555")
        self.log_area.tag_config("success", foreground="#00ffcc")
        self.log_area.tag_config("error", foreground="#ff3860")
        self.log_area.tag_config("warning", foreground="#ffdd57")
        self.log_area.tag_config("highlight", foreground="#209cee")
        self.log_area.tag_config("info", foreground="#ffffff")

    def add_path_row(self, parent, label_text, var, is_config):
        row = tk.Frame(parent, bg="#1e1e1e")
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label_text, width=15, anchor="w", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 8, "bold")).pack(side="left")
        entry = tk.Entry(row, textvariable=var, font=("Consolas", 9), bg="#2d2d2d", fg="#ffffff", relief="flat", insertbackground="white")
        entry.pack(side="left", expand=True, fill="x", padx=10, ipady=4)
        
        def on_browse():
            directory = filedialog.askdirectory()
            if directory:
                var.set(os.path.normpath(directory))
                if is_config: self.save_settings()

        tk.Button(row, text="...", command=on_browse, bg="#3d3d3d", fg="white", relief="flat", font=("Arial", 10, "bold"), padx=10).pack(side="right")

    def browse_dir(self, var, is_config):
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))
            if is_config: self.save_settings()

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "กรุณาเลือกโฟลเดอร์ Source")
            return
        self.log("Starting Grouping Phase...", "info")
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        moved = 0
        for f in files:
            match = re.search(r'(\d{4})', f)
            if match:
                code = match.group(1)
                target = os.path.join(src, code)
                if not os.path.exists(target): os.makedirs(target)
                shutil.move(os.path.join(src, f), os.path.join(target, f))
                moved += 1
        self.log(f"Grouped {moved} files into numeric folders.", "success")
        messagebox.showinfo("Done", "Phase 1 Complete. Please rename folders to product codes.")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        self.log("Starting Renaming Phase...", "info")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        for folder_name in folders:
            path = os.path.join(src, folder_name)
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            if not files: continue
            max_idx = -1
            target_main = ""
            file_data = []
            for f in files:
                idx_match = re.search(r'_(\d+)\.', f)
                idx = int(idx_match.group(1)) if idx_match else -1
                file_data.append((idx, f))
                if idx > max_idx:
                    max_idx = idx
                    target_main = f
            if not target_main: target_main = files[-1]
            temp_list = []
            for idx, f in file_data:
                ext = os.path.splitext(f)[1]
                temp = f"temp_{f}"
                os.rename(os.path.join(path, f), os.path.join(path, temp))
                temp_list.append((idx, temp, ext))
            counter = 2
            for idx, temp, ext in temp_list:
                if (max_idx != -1 and idx == max_idx) or (max_idx == -1 and temp == f"temp_{target_main}"):
                    final = f"{folder_name}{ext}"
                else:
                    final = f"{folder_name}-{counter}{ext}"
                    counter += 1
                os.rename(os.path.join(path, temp), os.path.join(path, final))
        self.log("File Renaming Complete.", "success")
        messagebox.showinfo("Done", "Phase 2 Complete.")

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start}-{start+199}"

    def run_phase_backup(self):
        src = self.source_dir.get()
        p1 = self.photo1_dir.get()
        p2 = self.photo2_dir.get()
        if not all([src, p1, p2]):
            messagebox.showerror("Error", "Setup Photo 1 and 2 paths first.")
            return

        self.log("Starting Collect Photos Phase...", "info")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        
        for folder_name in folders:
            folder_path = os.path.join(src, folder_name)
            main_file = None
            for f in os.listdir(folder_path):
                if os.path.splitext(f)[0] == folder_name:
                    main_file = f
                    break
            
            if main_file:
                type_code = folder_name[0].upper()
                p_type = self.type_mapping.get(type_code, "Other")
                
                if "-VN-" in folder_name.upper():
                    target_rel_dir = os.path.join("Vincentio", p_type)
                else:
                    num_match = re.search(r'(\d+)', folder_name)
                    if num_match:
                        num = int(num_match.group(1))
                        range_folder = self.get_range(num)
                        target_rel_dir = os.path.join(p_type, f"{p_type} {range_folder}")
                    else:
                        target_rel_dir = os.path.join(p_type, "Unknown")
                
                t1_dir = os.path.join(p1, target_rel_dir)
                t2_dir = os.path.join(p2, target_rel_dir)
                
                # ISSUE FIX: Check if folders exist. If not, don't create, warn user.
                if not os.path.exists(t1_dir):
                    self.log(f"ไม่พบโฟลเดอร์ปลายทางใน Photo 1: {target_rel_dir}", "error")
                    self.log(f"รหัส {folder_name} อาจจะผิด หรือมีการเว้นวรรคไม่ตรงกัน", "warning")
                    continue
                
                # Check for existing file (ignore extension)
                old_p1 = None
                for f in os.listdir(t1_dir):
                    if os.path.splitext(f)[0] == folder_name:
                        old_p1 = os.path.join(t1_dir, f)
                        break
                
                old_p2 = None
                if os.path.exists(t2_dir):
                    for f in os.listdir(t2_dir):
                        if os.path.splitext(f)[0] == folder_name:
                            old_p2 = os.path.join(t2_dir, f)
                            break

                src_file = os.path.join(folder_path, main_file)

                # Show Preview with BOTH old files
                if self.show_preview(old_p1, old_p2, src_file, target_rel_dir):
                    # Replace in P1
                    if old_p1: os.remove(old_p1)
                    shutil.copy2(src_file, os.path.join(t1_dir, main_file))
                    # Replace in P2
                    if os.path.exists(t2_dir):
                        if old_p2: os.remove(old_p2)
                        shutil.copy2(src_file, os.path.join(t2_dir, main_file))
                    self.log(f"Collected: {folder_name} -> {target_rel_dir}", "success")
                else:
                    self.log(f"Skipped: {folder_name}", "warning")

        self.log("Phase 3: Collect Photos Complete.", "success")

    def run_phase_archive(self):
        src = self.source_dir.get()
        arc = self.archive_dir.get()
        if not all([src, arc]): return
        self.log("Starting Archive Phase...", "info")
        now = datetime.now()
        path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(path): os.makedirs(path)
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        for f in folders:
            shutil.move(os.path.join(src, f), os.path.join(path, f))
        self.log("Archived all folders.", "success")
        messagebox.showinfo("Done", "All files moved to Archive.")

    def show_preview(self, p1_old, p2_old, new_file, dest):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"PREVIEW: {os.path.basename(new_file)}")
        dialog.geometry("1000x700")
        dialog.configure(bg="#121212")
        dialog.grab_set()
        
        res = tk.BooleanVar(value=False)
        
        # Path Header
        p_frame = tk.Frame(dialog, bg="#1e1e1e", pady=10)
        p_frame.pack(fill="x")
        tk.Label(p_frame, text=f"DESTINATION: {dest}", fg="#00ffcc", bg="#1e1e1e", font=("Consolas", 10, "bold")).pack()

        # Image Grid
        grid = tk.Frame(dialog, bg="#121212", padx=20, pady=20)
        grid.pack(expand=True, fill="both")
        
        def add_img_box(parent, path, title, color):
            box = tk.Frame(parent, bg="#121212")
            box.pack(side="left", expand=True, fill="both")
            tk.Label(box, text=title, fg=color, bg="#121212", font=("Segoe UI", 10, "bold")).pack(pady=5)
            if path and os.path.exists(path):
                try:
                    img = Image.open(path)
                    img.thumbnail((300, 300))
                    ph = ImageTk.PhotoImage(img)
                    l = tk.Label(box, image=ph, bg="#1e1e1e", bd=2, relief="flat")
                    l.image = ph; l.pack(pady=10)
                    tk.Label(box, text=os.path.basename(path), fg="#666666", bg="#121212", font=("Arial", 8)).pack()
                except: tk.Label(box, text="[CORRUPT IMAGE]", fg="red", bg="#121212").pack(pady=100)
            else:
                tk.Label(box, text="[ NOT FOUND ]", fg="#333333", bg="#121212", font=("Segoe UI", 12, "bold")).pack(pady=120)

        add_img_box(grid, p1_old, "OLD (PHOTO 1)", "#888888")
        add_img_box(grid, p2_old, "OLD (PHOTO 2)", "#888888")
        add_img_box(grid, new_file, "NEW FILE", "#00ffcc")

        # Buttons
        btn_f = tk.Frame(dialog, bg="#1e1e1e", pady=25)
        btn_f.pack(side="bottom", fill="x")
        
        def ok(): res.set(True); dialog.destroy()
        def no(): res.set(False); dialog.destroy()
        
        tk.Button(btn_f, text="REPLACE PHOTOS", bg="#00d1b2", fg="#1e1e1e", font=("Segoe UI", 12, "bold"), width=25, height=2, relief="flat", command=ok).pack(side="left", padx=50)
        tk.Button(btn_f, text="SKIP", bg="#3d3d3d", fg="white", font=("Segoe UI", 12), width=20, height=2, relief="flat", command=no).pack(side="right", padx=50)
        
        self.root.wait_window(dialog)
        return res.get()

if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
