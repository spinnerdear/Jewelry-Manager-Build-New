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
        self.root.title("Jewelry Media Manager v1.3")
        self.root.geometry("1000x800")
        self.root.configure(bg="#f8f9fa")

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
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        
        tag = "info"
        if "สำเร็จ" in message or "เสร็จสิ้น" in message: tag = "success"
        elif "ข้าม" in message or "เตือน" in message: tag = "warning"
        elif "Error" in message or "ผิดพลาด" in message: tag = "error"
        elif "ตรวจพบ" in message: tag = "highlight"
        
        self.log_area.insert(tk.END, f"{message}\n", tag)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def setup_dnd(self):
        self.source_entry.drop_target_register(DND_FILES)
        self.source_entry.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        path = event.data.strip('{}')
        if os.path.isdir(path):
            self.source_dir.set(os.path.normpath(path))
            self.log(f"โหลดโฟลเดอร์ผ่าน Drag & Drop: {path}", "success")
        else:
            self.log("กรุณาลากเฉพาะ 'โฟลเดอร์' เท่านั้น", "error")

    def create_widgets(self):
        # Header with Gradient-like blue
        header = tk.Frame(self.root, bg="#4a90e2", height=80)
        header.pack(fill="x")
        tk.Label(header, text="✨ JEWELRY MEDIA MANAGER ✨", fg="white", bg="#4a90e2", 
                 font=("Segoe UI", 20, "bold")).pack(pady=20)

        main_container = tk.Frame(self.root, bg="#f8f9fa", padx=30, pady=20)
        main_container.pack(expand=True, fill="both")

        # Section: Configuration (Card Style)
        config_card = tk.Frame(main_container, bg="white", highlightthickness=1, highlightbackground="#e1e4e8", padx=15, pady=15)
        config_card.pack(fill="x", pady=(0, 20))
        
        tk.Label(config_card, text="⚙️ การตั้งค่าระบบปลายทาง (จำค่าอัตโนมัติ)", font=("Segoe UI", 11, "bold"), bg="white", fg="#586069").pack(anchor="w", pady=(0, 10))

        self.add_path_row(config_card, "Photo 1 (Main DB):", self.photo1_dir, True)
        self.add_path_row(config_card, "Photo 2 (Backup DB):", self.photo2_dir, True)
        self.add_path_row(config_card, "Archive (คลังถาวร):", self.archive_dir, True)

        # Section: Source Folder (Card Style)
        source_card = tk.Frame(main_container, bg="white", highlightthickness=1, highlightbackground="#e1e4e8", padx=15, pady=15)
        source_card.pack(fill="x", pady=(0, 20))
        
        tk.Label(source_card, text="📂 โฟลเดอร์งานปัจจุบัน (ลากโฟลเดอร์มาวางได้ที่นี่ 👇)", font=("Segoe UI", 11, "bold"), bg="white", fg="#4a90e2").pack(anchor="w", pady=(0, 10))
        
        src_row = tk.Frame(source_card, bg="white")
        src_row.pack(fill="x")
        self.source_entry = tk.Entry(src_row, textvariable=self.source_dir, font=("Segoe UI", 10), bg="#f1f3f5", relief="flat", highlightthickness=1, highlightbackground="#dee2e6")
        self.source_entry.pack(side="left", expand=True, fill="x", padx=(0, 10), ipady=5)
        tk.Button(src_row, text="เลือกโฟลเดอร์", command=lambda: self.browse_dir(self.source_dir, False), 
                  bg="#6c757d", fg="white", relief="flat", padx=15).pack(side="right")

        # Section: Action Buttons
        btn_container = tk.Frame(main_container, bg="#f8f9fa")
        btn_container.pack(fill="x", pady=10)
        
        actions = [
            ("1. จัดกลุ่ม (4 หลัก)", "#6f42c1", self.run_phase_1),
            ("2. เปลี่ยนชื่อไฟล์", "#007bff", self.run_phase_rename),
            ("3. ตรวจสอบ & Backup", "#28a745", self.run_phase_backup),
            ("4. ย้ายเข้าคลังถาวร", "#fd7e14", self.run_phase_archive)
        ]

        for text, color, cmd in actions:
            btn = tk.Button(btn_container, text=text, bg=color, fg="white", font=("Segoe UI", 10, "bold"), 
                            relief="flat", width=22, height=2, command=cmd)
            btn.pack(side="left", padx=5, expand=True)

        # Section: Log Console
        tk.Label(main_container, text="📊 บันทึกสถานะการทำงาน", font=("Segoe UI", 10, "bold"), bg="#f8f9fa", fg="#586069").pack(anchor="w", pady=(15, 5))
        self.log_area = scrolledtext.ScrolledText(main_container, height=15, bg="#ffffff", font=("Consolas", 10), 
                                                 relief="flat", highlightthickness=1, highlightbackground="#e1e4e8")
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state='disabled')
        
        # Log Tags
        self.log_area.tag_config("time", foreground="#95a5a6")
        self.log_area.tag_config("success", foreground="#28a745", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("error", foreground="#dc3545", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("warning", foreground="#ffc107", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("highlight", foreground="#6f42c1", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("info", foreground="#343a40")

    def add_path_row(self, parent, label_text, var, is_config):
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="x", pady=4)
        tk.Label(frame, text=label_text, width=20, anchor="w", bg="white", font=("Segoe UI", 9)).pack(side="left")
        entry = tk.Entry(frame, textvariable=var, font=("Segoe UI", 9), bg="#f8f9fa", relief="flat", highlightthickness=1, highlightbackground="#dee2e6")
        entry.pack(side="left", expand=True, fill="x", padx=5, ipady=3)
        
        def on_browse():
            directory = filedialog.askdirectory()
            if directory:
                var.set(os.path.normpath(directory))
                if is_config: self.save_settings()

        tk.Button(frame, text="เลือก", command=on_browse, bg="#e9ecef", relief="flat", font=("Segoe UI", 8)).pack(side="right")

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

        self.log("--- 🚀 เริ่มเฟส 1: จัดกลุ่มตามเลข 4 หลัก ---")
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        moved = 0
        for f in files:
            match = re.search(r'(\d{4})', f)
            if match:
                code = match.group(1)
                target = os.path.join(src, code)
                if not os.path.exists(target): os.makedirs(target)
                shutil.move(os.path.join(src, f), os.path.join(target, f))
                self.log(f"ย้าย {f} -> {code}/")
                moved += 1
        
        self.log(f"เสร็จสิ้น! จัดกลุ่มไปทั้งหมด {moved} ไฟล์", "success")
        messagebox.showinfo("สำเร็จ", "จัดกลุ่มเสร็จแล้ว! กรุณาเปลี่ยนชื่อโฟลเดอร์เป็นรหัสสินค้าจริง")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        self.log("--- 📝 เริ่มเฟส 2: เปลี่ยนชื่อไฟล์ ---")
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
                    self.log(f"หลัก: {folder_name} -> {final}", "highlight")
                else:
                    final = f"{folder_name}-{counter}{ext}"
                    counter += 1
                os.rename(os.path.join(path, temp), os.path.join(path, final))
        
        self.log("เปลี่ยนชื่อไฟล์เสร็จเรียบร้อยแล้ว", "success")
        messagebox.showinfo("สำเร็จ", "เปลี่ยนชื่อไฟล์เสร็จแล้ว")

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start}-{start+199}"

    def run_phase_backup(self):
        src = self.source_dir.get()
        p1 = self.photo1_dir.get()
        p2 = self.photo2_dir.get()
        if not all([src, p1, p2]):
            messagebox.showerror("Error", "กรุณาตั้งค่า Photo 1 และ 2 ให้ครบ")
            return

        self.log("--- 🛡️ เริ่มเฟส 3: ตรวจสอบและ Backup ---")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        
        for folder_name in folders:
            folder_path = os.path.join(src, folder_name)
            main_file = None
            for f in os.listdir(folder_path):
                name_wo_ext = os.path.splitext(f)[0]
                if name_wo_ext == folder_name:
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
                
                target1 = os.path.join(p1, target_rel_dir)
                target2 = os.path.join(p2, target_rel_dir)
                
                # ค้นหาไฟล์เดิม (ไม่สนใจนามสกุล)
                existing_file_path = None
                if os.path.exists(target1):
                    for f in os.listdir(target1):
                        if os.path.splitext(f)[0] == folder_name:
                            existing_file_path = os.path.join(target1, f)
                            break
                
                src_full_path = os.path.join(folder_path, main_file)

                # แสดงพรีวิว
                if self.show_preview(existing_file_path, src_full_path, target_rel_dir):
                    if not os.path.exists(target1): os.makedirs(target1)
                    if not os.path.exists(target2): os.makedirs(target2)
                    
                    # ลบไฟล์เดิมถ้ามี (เพื่อป้องกันมีไฟล์หลายนามสกุลสำหรับรหัสเดียว)
                    if existing_file_path and os.path.exists(existing_file_path):
                        os.remove(existing_file_path)
                        # ลบใน Photo 2 ด้วย
                        p2_existing = os.path.join(target2, os.path.basename(existing_file_path))
                        if os.path.exists(p2_existing): os.remove(p2_existing)

                    shutil.copy2(src_full_path, os.path.join(target1, main_file))
                    shutil.copy2(src_full_path, os.path.join(target2, main_file))
                    self.log(f"บันทึกสำเร็จ: {folder_name} -> {target_rel_dir}", "success")
                else:
                    self.log(f"ข้ามการ Backup: {folder_name}", "warning")

        self.log("Backup ทั้งหมดเสร็จสิ้นแล้ว", "success")

    def run_phase_archive(self):
        src = self.source_dir.get()
        arc = self.archive_dir.get()
        if not all([src, arc]): return
        
        self.log("--- 📦 เริ่มเฟส 4: ย้ายเข้าคลังถาวร ---")
        now = datetime.now()
        archive_path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(archive_path): os.makedirs(archive_path)

        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        for f in folders:
            shutil.move(os.path.join(src, f), os.path.join(archive_path, f))
            self.log(f"Archive: {f} ย้ายไปที่คลังแล้ว")
        
        self.log("จัดเก็บเข้าคลังถาวรเสร็จสิ้น", "success")
        messagebox.showinfo("สำเร็จ", "งานทั้งหมดถูกย้ายเข้าคลังถาวรเรียบร้อยแล้ว")

    def show_preview(self, old_path, new_path, dest_rel):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"ตรวจสอบรหัส: {os.path.basename(new_path)}")
        dialog.geometry("1000x650")
        dialog.configure(bg="white")
        dialog.grab_set()
        
        res = tk.BooleanVar(value=False)
        
        # Info Header
        info_frame = tk.Frame(dialog, bg="#e3f2fd", pady=10)
        info_frame.pack(fill="x")
        tk.Label(info_frame, text=f"📍 ปลายทาง: {dest_rel}", font=("Segoe UI", 11, "bold"), bg="#e3f2fd", fg="#1976d2").pack()

        # Image Container
        img_container = tk.Frame(dialog, bg="white", padx=20, pady=10)
        img_container.pack(expand=True, fill="both")
        
        f_left = tk.Frame(img_container, bg="white"); f_left.pack(side="left", expand=True, fill="both")
        f_right = tk.Frame(img_container, bg="white"); f_right.pack(side="right", expand=True, fill="both")
        
        tk.Label(f_left, text="[ รูปเดิมในระบบ ]", font=("Segoe UI", 10, "bold"), bg="white", fg="#7f8c8d").pack(pady=5)
        tk.Label(f_right, text="[ รูปใหม่ที่จะแทนที่ ]", font=("Segoe UI", 10, "bold"), bg="white", fg="#2ecc71").pack(pady=5)

        def load_img(p, parent):
            if p and os.path.exists(p):
                try:
                    img = Image.open(p)
                    img.thumbnail((450, 450))
                    ph = ImageTk.PhotoImage(img)
                    l = tk.Label(parent, image=ph, bg="white"); l.image = ph; l.pack()
                    tk.Label(parent, text=f"ชื่อไฟล์: {os.path.basename(p)}", font=("Arial", 8), bg="white").pack()
                except: tk.Label(parent, text="ไม่สามารถเปิดรูปได้", bg="white").pack()
            else:
                tk.Label(parent, text="✨ ไม่พบไฟล์เดิม ✨\n(เป็นรหัสใหม่)", fg="#3498db", font=("Segoe UI", 14, "bold"), bg="white").pack(pady=180)

        load_img(old_path, f_left)
        load_img(new_path, f_right)

        # Action Buttons
        btn_f = tk.Frame(dialog, bg="#f8f9fa", pady=20)
        btn_f.pack(side="bottom", fill="x")
        
        def confirm(): res.set(True); dialog.destroy()
        def skip(): res.set(False); dialog.destroy()
        
        tk.Button(btn_f, text="✅ ยืนยันบันทึก (Confirm Replace)", bg="#28a745", fg="white", font=("Segoe UI", 12, "bold"), width=30, height=2, relief="flat", command=confirm).pack(side="left", padx=50)
        tk.Button(btn_f, text="❌ ข้ามไฟล์นี้ (Skip)", bg="#dc3545", fg="white", font=("Segoe UI", 11), width=20, height=2, relief="flat", command=skip).pack(side="right", padx=50)
        
        self.root.wait_window(dialog)
        return res.get()

if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
