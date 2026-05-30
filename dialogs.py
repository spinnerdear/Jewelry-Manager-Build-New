"""
PixUp - Dialogs (ไดอะล็อก/หน้าต่างย่อยทั้งหมด)
ทุกฟังก์ชันรับ (root, colors, ...) แบบ standalone ไม่พึ่ง PixUpApp
คืนผลลัพธ์เป็นค่า Python ปกติ (None = ยกเลิก)
"""
import os
import calendar as _calmod
from datetime import date as _date
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


# ----------------------------- Calendar picker (เลือกวันที่) -----------------------------
def calendar_picker(root, colors, initial=None):
    """ปฏิทินเลือกวันที่ (ทำเองด้วย Tkinter ไม่พึ่ง lib ภายนอก) คืน 'YYYY-MM-DD' หรือ None"""
    win = tk.Toplevel(root); win.title("เลือกวันที่")
    win.grab_set(); win.configure(bg=colors["bg"]); win.resizable(False, False)
    today = _date.today()
    try:
        y, m, _d = [int(x) for x in str(initial).split("-")]
        state = {"y": y, "m": m}
    except Exception:
        state = {"y": today.year, "m": today.month}
    result = {"val": None}

    header = tk.Frame(win, bg=colors["bg"]); header.pack(fill="x", padx=12, pady=(12, 4))
    title_var = tk.StringVar()
    tk.Button(header, text="‹", command=lambda: shift(-1), bg=colors["btn_default"], fg=colors["text"],
              relief="flat", font=("Segoe UI", 12, "bold"), width=3, cursor="hand2").pack(side="left")
    tk.Label(header, textvariable=title_var, bg=colors["bg"], fg=colors["accent"],
             font=("Segoe UI", 12, "bold"), width=18).pack(side="left", expand=True)
    tk.Button(header, text="›", command=lambda: shift(1), bg=colors["btn_default"], fg=colors["text"],
              relief="flat", font=("Segoe UI", 12, "bold"), width=3, cursor="hand2").pack(side="right")

    grid = tk.Frame(win, bg=colors["bg"]); grid.pack(padx=12, pady=(0, 12))

    def draw():
        for w_ in grid.winfo_children():
            w_.destroy()
        title_var.set(f"{_calmod.month_name[state['m']]} {state['y']}")
        for i, dname in enumerate(["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"]):
            tk.Label(grid, text=dname, bg=colors["bg"], fg=colors["text_mute"],
                     font=("Segoe UI", 8, "bold"), width=4).grid(row=0, column=i, pady=(0, 2))
        weeks = _calmod.Calendar(firstweekday=0).monthdayscalendar(state["y"], state["m"])
        for r, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                is_today = (state["y"] == today.year and state["m"] == today.month and day == today.day)

                def pick(dd=day):
                    result["val"] = f"{state['y']:04d}-{state['m']:02d}-{dd:02d}"
                    win.destroy()
                tk.Button(grid, text=str(day), command=pick, width=4, relief="flat", cursor="hand2",
                          bg=colors["accent"] if is_today else colors["card"],
                          fg=colors["on_accent"] if is_today else colors["text"],
                          font=("Segoe UI", 9, "bold" if is_today else "normal"),
                          activebackground=colors["accent_hover"]).grid(row=r, column=col, padx=1, pady=1)

    def shift(delta):
        m = state["m"] + delta; y = state["y"]
        while m < 1:
            m += 12; y -= 1
        while m > 12:
            m -= 12; y += 1
        state["m"] = m; state["y"] = y; draw()

    draw()
    root.wait_window(win)
    return result["val"]


def _is_image(f):
    return f.lower().endswith(IMAGE_EXTENSIONS)


# ----------------------------- Image selector (เลือกรูปจากหลายโฟลเดอร์) -----------------------------
def image_selector(root, colors, folder_paths, max_per_folder, title, subtitle=""):
    """ติ๊กเลือกรูปต่อโฟลเดอร์ คืน {folder_path: [files]} หรือ None ถ้ายกเลิก"""
    win = tk.Toplevel(root); win.title(title); win.geometry("1120x860")
    win.grab_set(); win.configure(bg=colors["bg"])

    head = tk.Frame(win, bg=colors["bg"]); head.pack(fill="x", padx=20, pady=(16, 2))
    tk.Label(head, text=title, bg=colors["bg"], fg=colors["accent"],
             font=("Segoe UI", 14, "bold")).pack(anchor="w")
    if subtitle:
        tk.Label(head, text=subtitle, bg=colors["bg"], fg=colors["text_dim"],
                 font=("Segoe UI", 9)).pack(anchor="w")

    sel = {}
    photo_refs = {}
    count_var = tk.StringVar(value="เลือกแล้ว 0 รูป")

    def update_count():
        count_var.set(f"เลือกแล้ว {sum(len(v) for v in sel.values())} รูป")

    btns = tk.Frame(win, bg=colors["bg_alt"]); btns.pack(fill="x", side="bottom")
    btns_in = tk.Frame(btns, bg=colors["bg_alt"]); btns_in.pack(fill="x", padx=20, pady=14)
    tk.Label(btns_in, textvariable=count_var, bg=colors["bg_alt"], fg=colors["text"],
             font=("Segoe UI", 10, "bold")).pack(side="left")
    confirmed = {"ok": False}

    def on_ok():
        final = {k: v for k, v in sel.items() if v}
        if not final:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกอย่างน้อย 1 รูป", parent=win)
            return
        confirmed["ok"] = True
        sel.clear(); sel.update(final)
        win.destroy()

    tk.Button(btns_in, text="ยืนยัน ✓", command=on_ok, bg=colors["accent"], fg=colors["on_accent"],
              font=("Segoe UI", 11, "bold"), padx=28, pady=8, relief="flat", cursor="hand2").pack(side="right")
    tk.Button(btns_in, text="ยกเลิก", command=win.destroy, bg=colors["btn_default"],
              fg=colors["text"], relief="flat", font=("Segoe UI", 10, "bold"), padx=20, pady=8,
              cursor="hand2").pack(side="right", padx=(0, 10))

    container = tk.Frame(win, bg=colors["bg"]); container.pack(fill="both", expand=True, padx=20, pady=10)
    canvas = tk.Canvas(container, bg=colors["bg"], highlightthickness=0); canvas.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview); scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)
    scroll_f = tk.Frame(canvas, bg=colors["bg"]); canvas.create_window((0, 0), window=scroll_f, anchor="nw")
    scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    for f_path in folder_paths:
        f_name = os.path.basename(f_path)
        row = tk.Frame(scroll_f, bg=colors["card"], pady=10, padx=10,
                       highlightthickness=1, highlightbackground=colors["border"])
        row.pack(fill="x", pady=5)
        tk.Label(row, text=f_name, bg=colors["card"], fg=colors["text_dim"],
                 font=("Consolas", 10, "bold"), width=14, anchor="w").pack(side="left", padx=8)
        img_container = tk.Frame(row, bg=colors["card"]); img_container.pack(side="left", fill="x", expand=True)
        try:
            files = sorted([f for f in os.listdir(f_path) if _is_image(f)])
        except Exception:
            files = []
        sel[f_path] = []
        if not files:
            tk.Label(img_container, text="(ไม่มีรูปในโฟลเดอร์นี้)", bg=colors["card"],
                     fg=colors["text_mute"], font=("Segoe UI", 9)).pack(side="left", padx=8)
        for f in files:
            try:
                full_p = os.path.join(f_path, f)
                img = Image.open(full_p); img.thumbnail((110, 110)); ph = ImageTk.PhotoImage(img)
                photo_refs[full_p] = ph
                cell = tk.Frame(img_container, bg=colors["card"]); cell.pack(side="left", padx=4)
                lbl = tk.Label(cell, image=ph, bg=colors["card"], cursor="hand2",
                               highlightthickness=3, highlightbackground=colors["card"])
                lbl.pack()
                cap = tk.Label(cell, text=f, bg=colors["card"], fg=colors["text_mute"],
                               font=("Consolas", 7), wraplength=110)
                cap.pack()

                def toggle(f_p=f_path, fn=f, b=lbl):
                    if fn in sel[f_p]:
                        sel[f_p].remove(fn)
                        b.config(relief="flat", highlightbackground=colors["card"])
                    else:
                        if max_per_folder is not None and len(sel[f_p]) >= max_per_folder:
                            messagebox.showwarning("จำกัด", f"เลือกได้สูงสุด {max_per_folder} รูป/โฟลเดอร์", parent=win)
                            return
                        sel[f_p].append(fn)
                        b.config(relief="solid", highlightbackground=colors["accent"])
                    update_count()
                lbl.bind("<Button-1>", lambda e, f_p=f_path, fn=f, b=lbl: toggle(f_p, fn, b))
            except Exception:
                pass

    root.wait_window(win)
    try:
        canvas.unbind_all("<MouseWheel>")
    except Exception:
        pass
    return dict(sel) if confirmed["ok"] else None


# ----------------------------- Primary chooser (เลือกรูปหลัก) -----------------------------
def primary_chooser(root, colors, folder_path, files, folder_name, log=None):
    """เลือกรูปหลัก 1 รูป (ไฮไลต์ _AI). คืนชื่อไฟล์"""
    if len(files) <= 1:
        return files[0]

    def is_ai(f):
        return os.path.splitext(f)[0].lower().endswith("_ai")
    files = sorted(files, key=lambda f: (not is_ai(f), f.lower()))

    win = tk.Toplevel(root); win.title(f"เลือกรูปหลัก: {folder_name}")
    win.geometry("1040x780"); win.grab_set(); win.configure(bg=colors["bg"])
    res = tk.StringVar()
    tk.Label(win, text=f"เลือกรูปหลัก (PRIMARY) — โฟลเดอร์ {folder_name}", bg=colors["bg"],
             fg=colors["accent"], font=("Segoe UI", 12, "bold")).pack(pady=(10, 0))
    tk.Label(win, text="รูปกรอบเขียว = ผ่าน AI แล้ว (แนะนำให้เลือกเป็นรูปหลัก)",
             bg=colors["bg"], fg=colors["text_dim"], font=("Segoe UI", 9)).pack(pady=(0, 8))
    can = tk.Canvas(win, bg=colors["bg"], highlightthickness=0)
    can.pack(side="left", fill="both", expand=True, padx=10)
    sb = ttk.Scrollbar(win, orient="vertical", command=can.yview); sb.pack(side="right", fill="y")
    can.configure(yscrollcommand=sb.set)
    gal = tk.Frame(can, bg=colors["bg"]); can.create_window((0, 0), window=gal, anchor="nw")
    gal.bind("<Configure>", lambda e: can.configure(scrollregion=can.bbox("all")))
    photo_refs = []
    for i, f in enumerate(files):
        try:
            img = Image.open(os.path.join(folder_path, f)); img.thumbnail((160, 160))
            ph = ImageTk.PhotoImage(img); photo_refs.append(ph)
            ai = is_ai(f)
            border = colors["accent"] if ai else colors["border"]
            cell = tk.Frame(gal, bg=colors["card"], padx=6, pady=6,
                            highlightthickness=2 if ai else 1, highlightbackground=border, highlightcolor=border)
            cell.grid(row=i // 5, column=i % 5, padx=8, pady=8)
            if ai:
                tk.Label(cell, text="✨ AI", bg=colors["accent"], fg=colors["on_accent"],
                         font=("Segoe UI", 8, "bold")).pack(anchor="w")
            lbl = tk.Label(cell, image=ph, bg=colors["card"], cursor="hand2"); lbl.pack()
            name = tk.Label(cell, text=f, bg=colors["card"],
                            fg=colors["accent"] if ai else colors["text_dim"],
                            font=("Consolas", 8, "bold" if ai else "normal"), wraplength=160, cursor="hand2")
            name.pack(pady=(4, 0))
            for wdg in (lbl, name):
                wdg.bind("<Button-1>", lambda e, f=f: [res.set(f), win.destroy()])
        except Exception as e:
            if log:
                log(f"ข้ามตัวอย่าง {f}: {e}", "warning")
    root.wait_window(win)
    return res.get() if res.get() else files[0]


# ----------------------------- Merge editor (รวมรูปต่างหู 2 กรอบ) -----------------------------
def merge_editor(root, colors, ai_paths, out_dir, folder_name, current, total, done_event):
    win = tk.Toplevel(root); win.title(f"MERGE: {folder_name} ({current}/{total})")
    win.geometry("860x880"); win.grab_set(); win.configure(bg=colors["bg"])
    COMP, PV = 2000, 640

    try:
        base_imgs = [Image.open(p).convert("RGBA") for p in ai_paths]
    except Exception as e:
        messagebox.showerror("Error", f"เปิดรูปไม่ได้: {e}", parent=win)
        win.destroy(); done_event.set(); return

    frames = [(0, 0, COMP // 2, COMP), (COMP // 2, 0, COMP // 2, COMP)]
    state = [{"scale": 1.0, "ox": COMP // 4, "oy": COMP // 2},
             {"scale": 1.0, "ox": COMP // 4, "oy": COMP // 2}]
    active = {"i": 0}
    zoom_vars = [tk.DoubleVar(value=1.0), tk.DoubleVar(value=1.0)]

    tk.Label(win, text=f"รวมรูปต่างหู — {folder_name}  ({current}/{total})", bg=colors["bg"],
             fg=colors["accent"], font=("Segoe UI", 13, "bold")).pack(pady=(12, 0))
    tk.Label(win, text="ลากรูปในกรอบเพื่อย้าย · แถบ ZOOM ของแต่ละฝั่งเพื่อย่อ/ขยาย (ส่วนเกินกรอบถูกครอป)",
             bg=colors["bg"], fg=colors["text_dim"], font=("Segoe UI", 9)).pack(pady=(0, 6))

    bar = tk.Frame(win, bg=colors["bg_alt"]); bar.pack(side="bottom", fill="x")
    barin = tk.Frame(bar, bg=colors["bg_alt"]); barin.pack(fill="x", padx=20, pady=12)
    ctrl = tk.Frame(win, bg=colors["bg"]); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 8))

    canvas = tk.Canvas(win, width=PV, height=PV, bg="white", highlightthickness=1,
                       highlightbackground=colors["border"], cursor="fleur")
    canvas.pack(pady=8)

    def clamp(i):
        fw, fh = frames[i][2], frames[i][3]
        state[i]["ox"] = min(max(state[i]["ox"], 0), fw)
        state[i]["oy"] = min(max(state[i]["oy"], 0), fh)

    def build(size):
        s = size / COMP
        comp = Image.new('RGB', (size, size), (255, 255, 255))
        for i, im in enumerate(base_imgs):
            fx, fy, fw, fh = frames[i]
            tw, th = max(1, int(fw * s)), max(1, int(fh * s))
            tile = Image.new('RGB', (tw, th), (255, 255, 255))
            boxw = max(1, int(fw * state[i]["scale"] * s))
            boxh = max(1, int(fh * state[i]["scale"] * s))
            t = im.copy(); t.thumbnail((boxw, boxh), Image.Resampling.LANCZOS)
            ox = int(state[i]["ox"] * s - t.width / 2)
            oy = int(state[i]["oy"] * s - t.height / 2)
            tile.paste(t, (ox, oy), t)
            comp.paste(tile, (int(fx * s), int(fy * s)))
        return comp

    def refresh():
        clamp(0); clamp(1)
        canvas.delete("all")
        comp = build(COMP).resize((PV, PV), Image.Resampling.BILINEAR)
        ph = ImageTk.PhotoImage(comp); canvas.image = ph
        canvas.create_image(0, 0, image=ph, anchor="nw")
        for i in range(2):
            fx, fy, fw, fh = frames[i]
            s = PV / COMP
            color = colors["accent"] if i == active["i"] else colors["text_mute"]
            canvas.create_rectangle(fx * s + 1, fy * s + 1, (fx + fw) * s - 1, (fy + fh) * s - 1,
                                    outline=color, width=2)
        canvas.create_line(PV / 2, 0, PV / 2, PV, fill=colors["highlight"], width=1, dash=(6, 4))

    drag = {"x": 0, "y": 0}

    def on_press(e):
        active["i"] = 0 if e.x < PV / 2 else 1
        drag["x"], drag["y"] = e.x, e.y
        refresh()

    def on_drag(e):
        f = COMP / PV
        state[active["i"]]["ox"] += (e.x - drag["x"]) * f
        state[active["i"]]["oy"] += (e.y - drag["y"]) * f
        drag["x"], drag["y"] = e.x, e.y
        refresh()

    def on_wheel(e):
        i = 0 if e.x < PV / 2 else 1
        active["i"] = i
        d = 1.1 if e.delta > 0 else 0.9
        state[i]["scale"] = max(0.2, min(4.0, state[i]["scale"] * d))
        zoom_vars[i].set(round(state[i]["scale"], 2))
        refresh()

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<MouseWheel>", on_wheel)

    def apply_zoom(i):
        state[i]["scale"] = max(0.2, min(4.0, zoom_vars[i].get()))
        active["i"] = i
        refresh()

    zl = tk.Frame(ctrl, bg=colors["bg"]); zl.pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Label(zl, text="ZOOM ซ้าย", bg=colors["bg"], fg=colors["text"], font=("Segoe UI", 8)).pack(anchor="w")
    tk.Scale(zl, from_=0.2, to=4.0, resolution=0.05, variable=zoom_vars[0], orient="horizontal",
             bg=colors["bg"], fg=colors["text"], highlightthickness=0, troughcolor=colors["card"],
             command=lambda e: apply_zoom(0)).pack(fill="x")
    zr = tk.Frame(ctrl, bg=colors["bg"]); zr.pack(side="left", fill="x", expand=True, padx=(8, 8))
    tk.Label(zr, text="ZOOM ขวา", bg=colors["bg"], fg=colors["text"], font=("Segoe UI", 8)).pack(anchor="w")
    tk.Scale(zr, from_=0.2, to=4.0, resolution=0.05, variable=zoom_vars[1], orient="horizontal",
             bg=colors["bg"], fg=colors["text"], highlightthickness=0, troughcolor=colors["card"],
             command=lambda e: apply_zoom(1)).pack(fill="x")

    def swap():
        base_imgs[0], base_imgs[1] = base_imgs[1], base_imgs[0]
        state[0], state[1] = state[1], state[0]
        zoom_vars[0].set(round(state[0]["scale"], 2)); zoom_vars[1].set(round(state[1]["scale"], 2))
        refresh()
    tk.Button(ctrl, text="⇄ สลับ", command=swap, bg=colors["btn_default"], fg=colors["text"],
              relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(0, 6))

    def reset():
        for i in range(2):
            state[i] = {"scale": 1.0, "ox": COMP // 4, "oy": COMP // 2}
            zoom_vars[i].set(1.0)
        refresh()
    tk.Button(ctrl, text="รีเซ็ต", command=reset, bg=colors["btn_default"], fg=colors["text"],
              relief="flat", cursor="hand2", padx=10).pack(side="left")

    def save_and_next():
        build(COMP).save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95, optimize=True)
        win.destroy(); done_event.set()
    tk.Button(barin, text="บันทึก & ถัดไป →", command=save_and_next, bg=colors["success"], fg="#08130d",
              font=("Segoe UI", 12, "bold"), padx=24, pady=8, relief="flat", cursor="hand2").pack(side="right")
    tk.Button(barin, text="ข้าม", command=lambda: [win.destroy(), done_event.set()],
              bg=colors["btn_default"], fg=colors["text"], relief="flat",
              font=("Segoe UI", 10, "bold"), padx=18, pady=8, cursor="hand2").pack(side="right", padx=(0, 10))

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), done_event.set()])
    refresh()


# ----------------------------- Crop editor (ครอบตัด cover) -----------------------------
def crop_editor(root, colors, img_path, out_dir, filename, current, total, done_event):
    win = tk.Toplevel(root); win.title(f"CROP: {filename} ({current}/{total})")
    win.geometry("860x880"); win.grab_set(); win.configure(bg=colors["bg"])
    COMP, PV = 2000, 640

    try:
        base = Image.open(img_path).convert("RGBA")
    except Exception as e:
        messagebox.showerror("Error", f"เปิดรูปไม่ได้: {e}", parent=win)
        win.destroy(); done_event.set(); return

    st = {"scale": 1.0, "cx": COMP / 2, "cy": COMP / 2}
    scale_var = tk.DoubleVar(value=1.0)
    bw, bh = base.size

    tk.Label(win, text=f"ครอบตัด & จัดตำแหน่ง — {filename}  ({current}/{total})", bg=colors["bg"],
             fg=colors["accent"], font=("Segoe UI", 13, "bold")).pack(pady=(12, 0))
    tk.Label(win, text="ลากเพื่อย้ายรูป · ล้อเมาส์หรือแถบเลื่อนเพื่อซูมเข้า/ออก",
             bg=colors["bg"], fg=colors["text_dim"], font=("Segoe UI", 9)).pack(pady=(0, 6))

    bar = tk.Frame(win, bg=colors["bg_alt"]); bar.pack(side="bottom", fill="x")
    barin = tk.Frame(bar, bg=colors["bg_alt"]); barin.pack(fill="x", padx=20, pady=12)
    ctrl = tk.Frame(win, bg=colors["bg"]); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 6))

    canvas = tk.Canvas(win, width=PV, height=PV, bg="white", highlightthickness=1,
                       highlightbackground=colors["border"], cursor="fleur")
    canvas.pack(pady=8)

    def build(size):
        s = size / COMP
        comp = Image.new('RGB', (size, size), (255, 255, 255))
        target = max(10.0, COMP * st["scale"] * s)
        r = target / min(bw, bh)
        nw, nh = max(1, int(bw * r)), max(1, int(bh * r))
        t = base.resize((nw, nh), Image.Resampling.LANCZOS)
        x = int(st["cx"] * s - nw / 2)
        y = int(st["cy"] * s - nh / 2)
        comp.paste(t, (x, y), t)
        return comp

    def refresh():
        canvas.delete("all")
        comp = build(COMP).resize((PV, PV), Image.Resampling.BILINEAR)
        ph = ImageTk.PhotoImage(comp); canvas.image = ph
        canvas.create_image(0, 0, image=ph, anchor="nw")

    drag = {"x": 0, "y": 0}

    def on_press(e):
        drag["x"], drag["y"] = e.x, e.y

    def on_drag(e):
        f = COMP / PV
        st["cx"] += (e.x - drag["x"]) * f
        st["cy"] += (e.y - drag["y"]) * f
        drag["x"], drag["y"] = e.x, e.y
        refresh()

    def apply_scale(v):
        st["scale"] = max(0.1, min(3.0, v))
        refresh()

    def on_wheel(e):
        d = 1.1 if e.delta > 0 else 0.9
        apply_scale(st["scale"] * d)
        scale_var.set(round(st["scale"], 2))

    canvas.bind("<Button-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<MouseWheel>", on_wheel)

    tk.Label(ctrl, text="ZOOM", bg=colors["bg"], fg=colors["text"], width=6, anchor="w").pack(side="left")
    tk.Scale(ctrl, from_=0.1, to=3.0, resolution=0.05, variable=scale_var, orient="horizontal",
             bg=colors["bg"], fg=colors["text"], highlightthickness=0, troughcolor=colors["card"],
             command=lambda e: apply_scale(scale_var.get())).pack(side="left", fill="x", expand=True)

    def reset():
        st["scale"] = 1.0; st["cx"] = COMP / 2; st["cy"] = COMP / 2
        scale_var.set(1.0); refresh()
    tk.Button(ctrl, text="รีเซ็ต", command=reset, bg=colors["btn_default"], fg=colors["text"],
              relief="flat", cursor="hand2", padx=10).pack(side="left", padx=(10, 0))

    def save_and_next():
        build(COMP).save(img_path, "JPEG", quality=95, optimize=True)
        win.destroy(); done_event.set()
    tk.Button(barin, text="บันทึก & ถัดไป →", command=save_and_next, bg=colors["success"], fg="#08130d",
              font=("Segoe UI", 12, "bold"), padx=24, pady=8, relief="flat", cursor="hand2").pack(side="right")
    tk.Button(barin, text="ข้าม", command=lambda: [win.destroy(), done_event.set()],
              bg=colors["btn_default"], fg=colors["text"], relief="flat",
              font=("Segoe UI", 10, "bold"), padx=18, pady=8, cursor="hand2").pack(side="right", padx=(0, 10))

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), done_event.set()])
    refresh()


# ----------------------------- Collect preview (ขั้นเก็บเข้าฐานข้อมูล — ทีละสินค้า) -----------------------------
def collect_preview(root, colors, plan):
    """พรีวิวทีละสินค้า: รูปต้นทาง + รูปปลายทางเดิม P1/P2 + เลือกแทน/ไม่แทน/ข้าม
    คืน {'allow_new': bool, 'decisions': {folder: 'replace'|'skip_dup'|'skip'}} หรือ None"""
    win = tk.Toplevel(root); win.title("ตรวจสอบก่อนเก็บเข้าฐานข้อมูล")
    win.geometry("920x780"); win.grab_set(); win.configure(bg=colors["bg"])
    status_label = {"exists": ("✓ มีหมวดอยู่แล้ว", colors["success"]),
                    "nearest": ("≈ ช่วงใกล้เคียง", colors["highlight"]),
                    "new": ("+ สร้างช่วงใหม่", colors["warning"]),
                    "no_category": ("✖ ไม่พบหมวด (จะข้าม)", colors["error"])}
    n = len(plan)
    idx = {"i": 0}
    allow_new = tk.BooleanVar(value=False)
    decisions = {item["folder"]: tk.StringVar(value="replace") for item in plan}
    confirmed = {"ok": False}
    win._refs = []

    tk.Label(win, text="ตรวจสอบรูปหลัก & ปลายทางก่อนคัดลอก (ทีละสินค้า)", bg=colors["bg"],
             fg=colors["accent"], font=("Segoe UI", 14, "bold")).pack(pady=(14, 2))
    counter_var = tk.StringVar()
    tk.Label(win, textvariable=counter_var, bg=colors["bg"], fg=colors["text_dim"],
             font=("Segoe UI", 10, "bold")).pack(pady=(0, 6))

    # แถบล่าง (อยู่ล่างสุดเสมอ)
    bar = tk.Frame(win, bg=colors["bg_alt"]); bar.pack(side="bottom", fill="x")
    barin = tk.Frame(bar, bg=colors["bg_alt"]); barin.pack(fill="x", padx=20, pady=12)
    tk.Checkbutton(barin, text="อนุญาตให้สร้างโฟลเดอร์ช่วงใหม่ (+)", variable=allow_new,
                   bg=colors["bg_alt"], fg=colors["text"], selectcolor=colors["card"],
                   activebackground=colors["bg_alt"], font=("Segoe UI", 9)).pack(side="left")

    def ok():
        confirmed["ok"] = True; win.destroy()
    tk.Button(barin, text="ยืนยันคัดลอกทั้งหมด →", command=ok, bg=colors["accent"], fg=colors["on_accent"],
              font=("Segoe UI", 11, "bold"), padx=24, pady=8, relief="flat", cursor="hand2").pack(side="right")
    tk.Button(barin, text="ยกเลิก", command=win.destroy, bg=colors["btn_default"],
              fg=colors["text"], relief="flat", font=("Segoe UI", 10, "bold"), padx=18, pady=8,
              cursor="hand2").pack(side="right", padx=(0, 10))

    detail = tk.Frame(win, bg=colors["bg"]); detail.pack(fill="both", expand=True, padx=16, pady=8)

    def _thumb(path, size=(190, 190)):
        try:
            img = Image.open(path); img.thumbnail(size); ph = ImageTk.PhotoImage(img)
            win._refs.append(ph); return ph
        except Exception:
            return None

    def _col(parent, title, img_path, status_txt=None, status_color=None, rel=None):
        f = tk.Frame(parent, bg=colors["card"], padx=12, pady=12, width=250,
                     highlightthickness=1, highlightbackground=colors["border"])
        f.pack_propagate(False)
        tk.Label(f, text=title, bg=colors["card"], fg=colors["text_dim"],
                 font=("Segoe UI", 9, "bold")).pack()
        ph = _thumb(img_path) if img_path else None
        if ph:
            tk.Label(f, image=ph, bg=colors["card"]).pack(pady=8)
        else:
            tk.Label(f, text="— ยังไม่มีรูปปลายทาง —\n(จะสร้างใหม่)", bg=colors["card"],
                     fg=colors["text_mute"], font=("Segoe UI", 9), height=9).pack(pady=8)
        if status_txt:
            tk.Label(f, text=status_txt, bg=colors["card"], fg=status_color,
                     font=("Segoe UI", 9, "bold")).pack()
        if rel:
            tk.Label(f, text=rel, bg=colors["card"], fg=colors["text_dim"],
                     font=("Consolas", 8), wraplength=220).pack()
        return f

    def render():
        for w_ in detail.winfo_children():
            w_.destroy()
        win._refs.clear()
        item = plan[idx["i"]]
        counter_var.set(f"สินค้า {idx['i'] + 1} / {n}   ·   {item['file']}")

        cols = tk.Frame(detail, bg=colors["bg"]); cols.pack()
        _col(cols, "📷 รูปต้นทาง (จะคัดลอก)", item["fpath"]).grid(row=0, column=0, padx=8)
        for c_i, key, lbl in ((1, "p1", "🗄 ปลายทาง P1 (ของเดิม)"), (2, "p2", "🗄 ปลายทาง P2 (ของเดิม)")):
            _t, rel, status = item[key]
            txt, color = status_label.get(status, (status, colors["text_dim"]))
            _col(cols, lbl, item[f"{key}_existing"], txt, color, rel).grid(row=0, column=c_i, padx=8)

        act = tk.Frame(detail, bg=colors["bg"]); act.pack(pady=(14, 0), anchor="w", padx=8)
        tk.Label(act, text="ทำอย่างไรกับสินค้านี้:", bg=colors["bg"], fg=colors["text"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        var = decisions[item["folder"]]
        for val, label in (("replace", "✓ แทนที่ — คัดลอกทับของเดิม (ถ้ามี)"),
                           ("skip_dup", "↷ ไม่แทนของเดิม — ข้ามเฉพาะปลายทางที่มีไฟล์ซ้ำ แต่ยังสร้างที่ยังไม่มี"),
                           ("skip", "✖ ข้ามสินค้านี้ — ไม่คัดลอกเลย")):
            tk.Radiobutton(act, text=label, variable=var, value=val, bg=colors["bg"], fg=colors["text"],
                           selectcolor=colors["input_bg"], activebackground=colors["bg"],
                           font=("Segoe UI", 9), anchor="w").pack(anchor="w")

        nav = tk.Frame(detail, bg=colors["bg"]); nav.pack(fill="x", pady=(16, 0))
        if idx["i"] > 0:
            tk.Button(nav, text="‹ ก่อนหน้า", command=lambda: go(-1), bg=colors["btn_default"],
                      fg=colors["text"], relief="flat", font=("Segoe UI", 10, "bold"),
                      padx=16, pady=6, cursor="hand2").pack(side="left")
        if idx["i"] < n - 1:
            tk.Button(nav, text="ถัดไป ›", command=lambda: go(1), bg=colors["btn_default"],
                      fg=colors["text"], relief="flat", font=("Segoe UI", 10, "bold"),
                      padx=16, pady=6, cursor="hand2").pack(side="right")

    def go(d):
        idx["i"] = max(0, min(n - 1, idx["i"] + d)); render()

    render()
    root.wait_window(win)
    return ({"allow_new": allow_new.get(),
             "decisions": {k: v.get() for k, v in decisions.items()}}
            if confirmed["ok"] else None)


# ----------------------------- Import options (โหมดนำเข้า) -----------------------------
def import_options(root, colors):
    """เลือกโหมดนำเข้า คืน dict {mode, date_from, date_to, codes} หรือ None"""
    win = tk.Toplevel(root); win.title("ตัวเลือกการนำเข้า")
    win.geometry("520x520"); win.grab_set(); win.configure(bg=colors["bg"])
    tk.Label(win, text="📥 ตัวเลือกการนำเข้ารูป", bg=colors["bg"], fg=colors["accent"],
             font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=24, pady=(20, 4))

    mode = tk.StringVar(value="new")
    opts = [
        ("new", "ดึงเฉพาะรูปใหม่ (จำที่เคยดึงแล้ว)", "แนะนำ — ดึงเฉพาะไฟล์ที่ยังไม่เคยนำเข้า"),
        ("all", "ดึงทั้งหมด (ไม่สนความจำ)", "ดึงทุกไฟล์ในโฟลเดอร์กล้อง รวมที่เคยดึงแล้ว"),
        ("date", "ดึงตามช่วงวันที่", "เฉพาะไฟล์ที่แก้ไขในช่วงวันที่ที่ระบุ"),
        ("codes", "ดึงเฉพาะรหัสที่ระบุ", "พิมพ์รหัส 4 หลัก คั่นด้วยจุลภาค (ดึงซ้ำได้)"),
    ]
    body = tk.Frame(win, bg=colors["bg"]); body.pack(fill="x", padx=24, pady=6)
    for val, title, desc in opts:
        cell = tk.Frame(body, bg=colors["card"], padx=12, pady=8,
                        highlightthickness=1, highlightbackground=colors["border"])
        cell.pack(fill="x", pady=4)
        tk.Radiobutton(cell, text=title, variable=mode, value=val, bg=colors["card"], fg=colors["text"],
                       selectcolor=colors["input_bg"], activebackground=colors["card"],
                       font=("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w", fill="x")
        tk.Label(cell, text=desc, bg=colors["card"], fg=colors["text_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=24)

    extra = tk.Frame(win, bg=colors["bg"]); extra.pack(fill="x", padx=24, pady=(4, 0))
    tk.Label(extra, text="ช่วงวันที่ (กดปุ่ม 📅 เลือกจากปฏิทิน หรือพิมพ์ YYYY-MM-DD):", bg=colors["bg"],
             fg=colors["text_dim"], font=("Segoe UI", 8)).pack(anchor="w")
    drow = tk.Frame(extra, bg=colors["bg"]); drow.pack(fill="x")
    date_from = tk.StringVar(); date_to = tk.StringVar()

    def add_date_field(var):
        e = tk.Entry(drow, textvariable=var, width=12, bg=colors["input_bg"], fg=colors["text"],
                     relief="flat", insertbackground="white")
        e.pack(side="left", ipady=4)

        def pick():
            v = calendar_picker(win, colors, var.get().strip() or None)
            if v:
                var.set(v)
        tk.Button(drow, text="📅", command=pick, bg=colors["btn_default"], fg=colors["text"],
                  relief="flat", cursor="hand2", width=3).pack(side="left", padx=(2, 0))

    add_date_field(date_from)
    tk.Label(drow, text="  ถึง  ", bg=colors["bg"], fg=colors["text_dim"]).pack(side="left")
    add_date_field(date_to)
    tk.Label(extra, text="รหัสที่ต้องการ (เช่น 1212,0789 · 1000 1001 · 1000-1005 · ปนกันได้):", bg=colors["bg"],
             fg=colors["text_dim"], font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
    codes = tk.StringVar()
    tk.Entry(extra, textvariable=codes, bg=colors["input_bg"], fg=colors["text"],
             relief="flat", insertbackground="white").pack(fill="x", ipady=4)

    result = {}

    def ok():
        result.update({"mode": mode.get(), "date_from": date_from.get().strip(),
                       "date_to": date_to.get().strip(), "codes": codes.get().strip()})
        win.destroy()
    bar = tk.Frame(win, bg=colors["bg"]); bar.pack(fill="x", side="bottom", padx=24, pady=16)
    tk.Button(bar, text="เริ่มนำเข้า →", command=ok, bg=colors["accent"], fg=colors["on_accent"],
              font=("Segoe UI", 11, "bold"), pady=8, relief="flat", cursor="hand2").pack(side="right")
    tk.Button(bar, text="ยกเลิก", command=win.destroy, bg=colors["btn_default"], fg=colors["text"],
              relief="flat", font=("Segoe UI", 10, "bold"), padx=18, pady=8,
              cursor="hand2").pack(side="right", padx=(0, 10))

    root.wait_window(win)
    return result if result else None
