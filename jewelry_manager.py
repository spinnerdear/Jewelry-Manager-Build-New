import os
import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime
from PIL import Image, ImageTk

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jewelry Media Manager v1.2")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f2f5")

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

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

    def create_widgets(self):
        # Main Layout
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")
        tk.Label(header, text="JEWELRY MEDIA MANAGER", fg="white", bg="#2c3e50", font=("Arial", 16, "bold")).pack(pady=15)

        container = tk.Frame(self.root, bg="#f0f2f5", padx=20, pady=20)
        container.pack(expand=True, fill="both")

        # Section: Configuration (Stored)
        config_frame = tk.LabelFrame(container, text=" การตั้งค่าปลายทาง (ระบบจะจำค่าไว้) ", bg="white", padx=10, pady=10)
        config_frame.pack(fill="x", pady=(0, 20))

        self.add_path_row(config_frame, "Photo 1 (Main DB):", self.photo1_dir, True)
        self.add_path_row(config_frame, "Photo 2 (Backup DB):", self.photo2_dir, True)
        self.add_path_row(config_frame, "Archive (ถาวร):", self.archive_dir, True)

        # Section: Current Work
        work_frame = tk.LabelFrame(container, text=" โฟลเดอร์งานปัจจุบัน ", bg="white", padx=10, pady=10)
        work_frame.pack(fill="x", pady=(0, 20))
        self.add_path_row(work_frame, "Source (รูปที่โหลดมา):", self.source_dir, False)

        # Section: Actions
        action_frame = tk.Frame(container, bg="#f0f2f5")
        action_frame.pack(fill="x")

        btn_style = {"font": ("Arial", 10, "bold"), "fg": "white", "height": 2, "width": 18}
        
        tk.Button(action_frame, text="1. จัดกลุ่ม (4 หลัก)", bg="#9b59b6", command=self.run_phase_1, **btn_style).pack(side="left", padx=5)
        tk.Button(action_frame, text="2. เปลี่ยนชื่อไฟล์", bg="#3498db", command=self.run_phase_rename, **btn_style).pack(side="left", padx=5)
        tk.Button(action_frame, text="3. ตรวจสอบ & Backup", bg="#2ecc71", command=self.run_phase_backup, **btn_style).pack(side="left", padx=5)
        tk.Button(action_frame, text="4. ย้ายเข้ากรุถาวร", bg="#e67e22", command=self.run_phase_archive, **btn_style).pack(side="left", padx=5)

        # Section: Logs
        tk.Label(container, text="บันทึกการทำงาน (Log):", bg="#f0f2f5", font=("Arial", 10)).pack(anchor="w", pady=(10, 0))
        self.log_area = scrolledtext.ScrolledText(container, height=12, bg="white", font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, pady=5)

    def add_path_row(self, parent, label_text, var, is_config):
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=label_text, width=20, anchor="w", bg="white").pack(side="left")
        entry = tk.Entry(frame, textvariable=var, bg="#f8f9fa", relief="flat", highlightthickness=1, highlightbackground="#dee2e6")
        entry.pack(side="left", expand=True, fill="x", padx=5)
        
        def on_browse():
            directory = filedialog.askdirectory()
            if directory:
                var.set(os.path.normpath(directory))
                if is_config: self.save_settings()

        tk.Button(frame, text="เลือก", command=on_browse, bg="#dee2e6", relief="flat").pack(side="right")

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "กรุณาเลือกโฟลเดอร์ Source")
            return

        self.log("--- เริ่มเฟส 1: จัดกลุ่มตามเลข 4 หลัก ---")
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
        
        self.log(f"เสร็จสิ้น! ย้ายไปทั้งหมด {moved} ไฟล์")
        messagebox.showinfo("เสร็จสิ้น", "จัดกลุ่มเสร็จแล้ว กรุณาเปลี่ยนชื่อโฟลเดอร์ตัวเลขเป็นรหัสสินค้าจริง")

    def run_phase_rename(self):
        src = self.source_dir.get()
        if not src: return
        self.log("--- เริ่มเฟส 2: เปลี่ยนชื่อไฟล์ตามรหัสโฟลเดอร์ ---")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        
        for folder_name in folders:
            path = os.path.join(src, folder_name)
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            if not files: continue

            # หาไฟล์ที่มี _เลข สูงสุด
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

            # เปลี่ยนชื่อชั่วคราวเพื่อเลี่ยงชื่อซ้ำ
            temp_list = []
            for idx, f in file_data:
                ext = os.path.splitext(f)[1]
                temp = f"temp_{f}"
                os.rename(os.path.join(path, f), os.path.join(path, temp))
                temp_list.append((idx, temp, ext))

            # เปลี่ยนเป็นชื่อจริง
            counter = 2
            for idx, temp, ext in temp_list:
                if (max_idx != -1 and idx == max_idx) or (max_idx == -1 and temp == f"temp_{target_main}"):
                    final = f"{folder_name}{ext}"
                    self.log(f"ไฟล์หลัก: {folder_name}/{final}")
                else:
                    final = f"{folder_name}-{counter}{ext}"
                    counter += 1
                os.rename(os.path.join(path, temp), os.path.join(path, final))
        
        self.log("เปลี่ยนชื่อไฟล์เสร็จเรียบร้อย")
        messagebox.showinfo("เสร็จสิ้น", "เปลี่ยนชื่อไฟล์ในทุกโฟลเดอร์เสร็จแล้ว")

    def get_range(self, num):
        start = ((num - 1) // 200) * 200 + 1
        return f"{start}-{start+199}"

    def run_phase_backup(self):
        src = self.source_dir.get()
        p1 = self.photo1_dir.get()
        p2 = self.photo2_dir.get()
        if not all([src, p1, p2]):
            messagebox.showerror("Error", "กรุณาตั้งค่าพาธ Photo 1 และ 2")
            return

        self.log("--- เริ่มเฟส 3: ตรวจสอบและ Backup ---")
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        
        for folder_name in folders:
            folder_path = os.path.join(src, folder_name)
            # หาไฟล์หลัก (ชื่อตรงกับโฟลเดอร์)
            main_file = None
            for f in os.listdir(folder_path):
                name_wo_ext = os.path.splitext(f)[0]
                if name_wo_ext == folder_name:
                    main_file = f
                    break
            
            if main_file:
                # วิเคราะห์พาธฐานข้อมูล
                type_code = folder_name[0].upper()
                p_type = self.type_mapping.get(type_code, "Other")
                
                # เช็คว่าเป็นสินค้า Vincentio (VN) หรือไม่
                if "-VN-" in folder_name.upper():
                    # สำหรับ Vincentio: Vincentio/[Type]/[FileName]
                    target_rel_dir = os.path.join("Vincentio", p_type)
                    self.log(f"ตรวจพบรหัส VN: จะเก็บไว้ในโฟลเดอร์ Vincentio/{p_type} โดยตรง")
                else:
                    # สำหรับสินค้าปกติ: [Type]/[Range]/[FileName]
                    num_match = re.search(r'(\d+)', folder_name)
                    if num_match:
                        num = int(num_match.group(1))
                        range_folder = self.get_range(num)
                        target_rel_dir = os.path.join(p_type, range_folder)
                    else:
                        target_rel_dir = os.path.join(p_type, "Unknown")
                    self.log(f"สินค้าปกติ: จะเก็บไว้ในโฟลเดอร์ {p_type}/{target_rel_dir} โดยตรง")
                
                target1 = os.path.join(p1, target_rel_dir)
                target2 = os.path.join(p2, target_rel_dir)
                
                full_target_file = os.path.join(target1, main_file)
                src_file = os.path.join(folder_path, main_file)

                # พรีวิวและยืนยัน
                if self.show_preview(full_target_file, src_file):
                    if not os.path.exists(target1): os.makedirs(target1)
                    if not os.path.exists(target2): os.makedirs(target2)
                    shutil.copy2(src_file, os.path.join(target1, main_file))
                    shutil.copy2(src_file, os.path.join(target2, main_file))
                    self.log(f"Backup สำเร็จ: {main_file} -> {target_rel_dir}")
                else:
                    self.log(f"ข้ามการ Backup: {folder_name}")

        self.log("Backup เสร็จสิ้น")

    def run_phase_archive(self):
        src = self.source_dir.get()
        arc = self.archive_dir.get()
        if not all([src, arc]): return
        
        self.log("--- เริ่มเฟส 4: ย้ายเข้ากรุถาวร ---")
        now = datetime.now()
        path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        if not os.path.exists(path): os.makedirs(path)

        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        for f in folders:
            shutil.move(os.path.join(src, f), os.path.join(path, f))
            self.log(f"Archive: {f} -> {path}")
        
        self.log("ย้ายเข้ากรุถาวรเสร็จสิ้น")
        messagebox.showinfo("เสร็จสิ้น", "งานทั้งหมดถูกย้ายเข้ากรุถาวรแล้ว")

    def show_preview(self, old_path, new_path):
        dialog = tk.Toplevel(self.root)
        dialog.title("ยืนยันการบันทึก: " + os.path.basename(new_path))
        dialog.geometry("900x550")
        dialog.grab_set()
        
        res = tk.BooleanVar(value=False)
        
        # UI
        main = tk.Frame(dialog, padx=10, pady=10)
        main.pack(expand=True, fill="both")
        
        f_left = tk.Frame(main); f_left.pack(side="left", expand=True, fill="both")
        f_right = tk.Frame(main); f_right.pack(side="right", expand=True, fill="both")
        
        tk.Label(f_left, text="[ รูปเดิมในฐานข้อมูล ]", font=("Arial", 10, "bold")).pack()
        tk.Label(f_right, text="[ รูปใหม่ที่จะบันทึก ]", font=("Arial", 10, "bold")).pack()

        # Load Images
        def load_img(p, parent):
            if os.path.exists(p):
                try:
                    img = Image.open(p)
                    img.thumbnail((400, 400))
                    ph = ImageTk.PhotoImage(img)
                    l = tk.Label(parent, image=ph); l.image = ph; l.pack()
                except: tk.Label(parent, text="Error loading image").pack()
            else:
                tk.Label(parent, text="ไม่พบไฟล์เดิม (ไฟล์ใหม่)", fg="blue", font=("Arial", 12)).pack(pady=150)

        load_img(old_path, f_left)
        load_img(new_path, f_right)

        # Buttons
        b_frame = tk.Frame(dialog, pady=15)
        b_frame.pack(side="bottom")
        
        def confirm(): res.set(True); dialog.destroy()
        def skip(): res.set(False); dialog.destroy()
        
        tk.Button(b_frame, text="ยืนยันบันทึก (Confirm)", bg="#2ecc71", fg="white", width=20, command=confirm).pack(side="left", padx=10)
        tk.Button(b_frame, text="ข้าม (Skip)", bg="#e74c3c", fg="white", width=20, command=skip).pack(side="left", padx=10)
        
        self.root.wait_window(dialog)
        return res.get()

if __name__ == "__main__":
    root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
