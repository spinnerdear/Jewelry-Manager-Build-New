import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from PIL import Image, ImageTk

class JewelryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Jewelry Media Manager v1.1")
        self.root.geometry("700x550")

        # Variables for paths
        self.source_dir = tk.StringVar()
        self.photo1_dir = tk.StringVar()
        self.photo2_dir = tk.StringVar()
        self.archive_dir = tk.StringVar()

        # Item Type Mapping
        self.type_mapping = {
            'R': 'Ring',
            'E': 'Earring',
            'N': 'Necklace',
            'P': 'Pendant',
            'B': 'Bracelet',
            'S': 'Sets'
        }

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        padding = {'padx': 10, 'pady': 5}
        
        # Configuration Section
        config_label = tk.Label(main_frame, text="การตั้งค่าเส้นทางโฟลเดอร์", font=("Arial", 12, "bold"))
        config_label.pack(anchor="w", pady=(0, 10))

        # Helper to create path entries
        self.add_path_row(main_frame, "โฟลเดอร์ที่ต้องการจัดการ (Source):", self.source_dir)
        self.add_path_row(main_frame, "ไดร์ฟ Photo 1 (Main Database):", self.photo1_dir)
        self.add_path_row(main_frame, "ไดร์ฟ Photo 2 (Backup Database):", self.photo2_dir)
        self.add_path_row(main_frame, "ไดร์ฟเก็บไฟล์ถาวร (Archive):", self.archive_dir)

        # Action Buttons
        btn_frame = tk.LabelFrame(main_frame, text="ขั้นตอนการทำงาน", padx=10, pady=10)
        btn_frame.pack(fill="x", pady=20)
        
        tk.Button(btn_frame, text="1. จัดกลุ่มตามเลข 4 หลัก", 
                  command=self.run_phase_1, bg="#4CAF50", fg="white", height=2, width=25).pack(pady=5)
        
        tk.Button(btn_frame, text="2. ประมวลผลและสำรองข้อมูล", 
                  command=self.run_phase_2, bg="#2196F3", fg="white", height=2, width=25).pack(pady=5)

        # Status Bar
        self.status_var = tk.StringVar(value="พร้อมใช้งาน")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor="w")
        status_bar.pack(side="bottom", fill="x")

    def add_path_row(self, parent, label_text, var):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=label_text, width=30, anchor="w").pack(side="left")
        tk.Entry(frame, textvariable=var).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(frame, text="เลือก", command=lambda: self.browse_dir(var)).pack(side="right")

    def browse_dir(self, var):
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))

    def run_phase_1(self):
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showerror("Error", "กรุณาเลือกโฟลเดอร์ Source")
            return

        self.status_var.set("กำลังจัดกลุ่มไฟล์...")
        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        moved_count = 0
        
        for filename in files:
            match = re.search(r'(\d{4})', filename)
            if match:
                code = match.group(1)
                target_folder = os.path.join(src, code)
                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                
                shutil.move(os.path.join(src, filename), os.path.join(target_folder, filename))
                moved_count += 1

        self.status_var.set(f"จัดกลุ่มเสร็จแล้ว ย้ายไป {moved_count} ไฟล์")
        messagebox.showinfo("เสร็จสิ้น", f"จัดกลุ่มไฟล์เสร็จแล้ว!\nย้ายไป {moved_count} ไฟล์\n\nขั้นตอนต่อไป: เปลี่ยนชื่อโฟลเดอร์เป็นรหัสสินค้าจริง")

    def get_range_folder(self, code_num):
        """Calculate 200-range folder name, e.g., 8420 -> 8401-8600"""
        start = ((code_num - 1) // 200) * 200 + 1
        end = start + 199
        return f"{start}-{end}"

    def run_phase_2(self):
        src = self.source_dir.get()
        p1 = self.photo1_dir.get()
        p2 = self.photo2_dir.get()
        arc = self.archive_dir.get()

        if not all([src, p1, p2, arc]):
            messagebox.showerror("Error", "กรุณาเลือกโฟลเดอร์ให้ครบทุกช่อง")
            return

        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        
        for folder_name in folders:
            folder_path = os.path.join(src, folder_name)
            
            # Step 1: Rename Files inside folder
            self.status_var.set(f"กำลังประมวลผลโฟลเดอร์: {folder_name}")
            files = sorted([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
            
            if not files: continue

            # Logic: Find max index
            max_idx = -1
            main_file = None
            
            indexed_files = []
            for f in files:
                idx_match = re.search(r'_(\d+)\.', f)
                if idx_match:
                    idx = int(idx_match.group(1))
                    indexed_files.append((idx, f))
                    if idx > max_idx:
                        max_idx = idx
                        main_file = f
                else:
                    indexed_files.append((-1, f))

            if not main_file: # No _idx found, take the last one alphabetically or first
                main_file = files[-1]
            
            # Renaming process
            new_main_name = ""
            renamed_files = []
            
            # Sort indexed_files to handle main file first or last? 
            # Let's rename all to temporary names first to avoid collisions
            temp_names = []
            for idx, f in indexed_files:
                ext = os.path.splitext(f)[1]
                temp_name = f"temp_{f}"
                os.rename(os.path.join(folder_path, f), os.path.join(folder_path, temp_name))
                temp_names.append((idx, temp_name, ext))

            # Now rename to final names
            other_counter = 2
            final_main_path = ""
            for idx, temp_name, ext in temp_names:
                if (max_idx != -1 and idx == max_idx) or (max_idx == -1 and temp_name == f"temp_{main_file}"):
                    final_name = f"{folder_name}{ext}"
                    final_main_path = os.path.join(folder_path, final_name)
                else:
                    final_name = f"{folder_name}-{other_counter}{ext}"
                    other_counter += 1
                
                os.rename(os.path.join(folder_path, temp_name), os.path.join(folder_path, final_name))
                renamed_files.append(final_name)

            # Step 2: Handle Duplicate & Backup for the MAIN image only
            if final_main_path and final_main_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Calculate Database Path
                # Pattern: R-10591-00-S00 -> Type R, Num 10591
                type_match = re.match(r'([A-Z])', folder_name)
                num_match = re.search(r'(\d+)', folder_name)
                
                if type_match and num_match:
                    p_type = self.type_mapping.get(type_match.group(1), "Other")
                    p_num = int(num_match.group(1))
                    range_folder = self.get_range_folder(p_num)
                    
                    db_rel_path = os.path.join("jewelry", p_type, range_folder, folder_name)
                    
                    # Check in Photo 1
                    target_db_path1 = os.path.join(p1, db_rel_path)
                    target_db_path2 = os.path.join(p2, db_rel_path)
                    
                    if not os.path.exists(target_db_path1): os.makedirs(target_db_path1)
                    if not os.path.exists(target_db_path2): os.makedirs(target_db_path2)
                    
                    final_main_filename = os.path.basename(final_main_path)
                    existing_file = os.path.join(target_db_path1, final_main_filename)
                    
                    # Preview & Confirm
                    confirmed = self.show_preview_dialog(existing_file, final_main_path)
                    
                    if confirmed:
                        shutil.copy2(final_main_path, os.path.join(target_db_path1, final_main_filename))
                        shutil.copy2(final_main_path, os.path.join(target_db_path2, final_main_filename))

            # Step 3: Archive the whole folder
            now = datetime.now()
            # Path: 2026 / 05-2026 / 16-05-2026
            year_folder = now.strftime("%Y")
            month_year_folder = now.strftime("%m-%Y")
            day_month_year_folder = now.strftime("%d-%m-%Y")
            
            archive_path = os.path.join(arc, year_folder, month_year_folder, day_month_year_folder)
            if not os.path.exists(archive_path): os.makedirs(archive_path)
            
            # Move processed folder to archive
            shutil.move(folder_path, os.path.join(archive_path, folder_name))

        self.status_var.set("การประมวลผลทั้งหมดเสร็จสิ้นแล้ว")
        messagebox.showinfo("เสร็จสิ้น", "ดำเนินการเปลี่ยนชื่อ สำรองข้อมูล และเก็บไฟล์ถาวรเรียบร้อยแล้ว!")

    def show_preview_dialog(self, old_path, new_path):
        """Show a side-by-side preview window"""
        dialog = tk.Toplevel(self.root)
        dialog.title("ยืนยันการบันทึกไฟล์")
        dialog.geometry("850x500")
        dialog.grab_set() # Make it modal

        result = tk.BooleanVar(value=False)

        main_frame = tk.Frame(dialog, padx=10, pady=10)
        main_frame.pack(expand=True, fill="both")

        # Left: Old File
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", expand=True, fill="both")
        tk.Label(left_frame, text="ไฟล์เดิมในฐานข้อมูล", font=("Arial", 10, "bold")).pack()
        
        if os.path.exists(old_path):
            try:
                img_old = Image.open(old_path)
                img_old.thumbnail((400, 400))
                photo_old = ImageTk.PhotoImage(img_old)
                lbl_old = tk.Label(left_frame, image=photo_old)
                lbl_old.image = photo_old
                lbl_old.pack()
            except:
                tk.Label(left_frame, text="[ไม่สามารถแสดงรูปได้]").pack()
        else:
            tk.Label(left_frame, text="[ไม่พบไฟล์เดิม - ไฟล์ใหม่แกะกล่อง]", fg="blue").pack(pady=100)

        # Right: New File
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", expand=True, fill="both")
        tk.Label(right_frame, text="ไฟล์ใหม่ที่จะบันทึก", font=("Arial", 10, "bold")).pack()
        
        try:
            img_new = Image.open(new_path)
            img_new.thumbnail((400, 400))
            photo_new = ImageTk.PhotoImage(img_new)
            lbl_new = tk.Label(right_frame, image=photo_new)
            lbl_new.image = photo_new
            lbl_new.pack()
        except:
            tk.Label(right_frame, text="[ไม่สามารถแสดงรูปได้]").pack()

        # Buttons
        btn_frame = tk.Frame(dialog, pady=10)
        btn_frame.pack(side="bottom", fill="x")

        def on_confirm():
            result.set(True)
            dialog.destroy()

        def on_skip():
            result.set(False)
            dialog.destroy()

        tk.Button(btn_frame, text="ยืนยันการบันทึก (Confirm)", bg="#4CAF50", fg="white", width=20, command=on_confirm).pack(side="left", padx=50)
        tk.Button(btn_frame, text="ข้ามไฟล์นี้ (Skip)", bg="#f44336", fg="white", width=20, command=on_skip).pack(side="right", padx=50)

        self.root.wait_window(dialog)
        return result.get()

if __name__ == "__main__":
    root = tk.Tk()
    app = JewelryManagerApp(root)
    root.mainloop()
