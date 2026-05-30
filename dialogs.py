"""
PixUp - Dialogs (ไดอะล็อก/หน้าต่างย่อยทั้งหมด) — CustomTkinter
ทุกฟังก์ชันรับ (root, colors, ...) แบบ standalone ไม่พึ่ง PixUpApp
คืนผลลัพธ์เป็นค่า Python ปกติ (None = ยกเลิก)
หมายเหตุ: หน้ารวมรูป/ครอป ยังใช้ tk.Canvas (ตรรกะวาด/ลาก/ซูมเดิม) แค่เปลี่ยนปุ่ม/แถบเป็น ctk
"""
import os
import calendar as _calmod
from datetime import date as _date
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
FONT = "Segoe UI"


def _is_image(f):
    return f.lower().endswith(IMAGE_EXTENSIONS)


def _toplevel(root, colors, title, geometry=None):
    win = ctk.CTkToplevel(root); win.title(title)
    if geometry:
        win.geometry(geometry)
    win.configure(fg_color=colors["bg"])
    win.after(120, win.grab_set)
    return win


def _ctk_img(pil, size):
    return ctk.CTkImage(light_image=pil, dark_image=pil, size=(int(size[0]), int(size[1])))


def _btn(parent, text, cmd, colors, kind="default", **kw):
    c = colors
    if kind == "accent":
        fg, hover, tcol = c["accent"], c["accent_hover"], c["on_accent"]
    elif kind == "success":
        fg, hover, tcol = c["success"], c["success"], "#08130d"
    elif kind == "danger":
        fg, hover, tcol = c["error"], c["error"], "#ffffff"
    else:
        fg, hover, tcol = c["btn_default"], c["btn_hover"], c["text"]
    return ctk.CTkButton(parent, text=text, command=cmd, fg_color=fg, hover_color=hover,
                         text_color=tcol, corner_radius=8, **kw)


# ----------------------------- Calendar picker -----------------------------
def calendar_picker(root, colors, initial=None):
    """ปฏิทินเลือกวันที่ คืน 'YYYY-MM-DD' หรือ None"""
    win = _toplevel(root, colors, "เลือกวันที่")
    win.resizable(False, False)
    today = _date.today()
    try:
        y, m, _d = [int(x) for x in str(initial).split("-")]
        state = {"y": y, "m": m}
    except Exception:
        state = {"y": today.year, "m": today.month}
    result = {"val": None}

    header = ctk.CTkFrame(win, fg_color="transparent"); header.pack(fill="x", padx=14, pady=(14, 4))
    title_var = tk.StringVar()
    _btn(header, "‹", lambda: shift(-1), colors, width=36, height=32, font=(FONT, 14, "bold")).pack(side="left")
    ctk.CTkLabel(header, textvariable=title_var, text_color=colors["accent"],
                 font=(FONT, 13, "bold"), width=180).pack(side="left", expand=True)
    _btn(header, "›", lambda: shift(1), colors, width=36, height=32, font=(FONT, 14, "bold")).pack(side="right")

    grid = ctk.CTkFrame(win, fg_color="transparent"); grid.pack(padx=14, pady=(0, 14))

    def draw():
        for w_ in grid.winfo_children():
            w_.destroy()
        title_var.set(f"{_calmod.month_name[state['m']]} {state['y']}")
        for i, dname in enumerate(["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"]):
            ctk.CTkLabel(grid, text=dname, text_color=colors["text_mute"],
                         font=(FONT, 11, "bold"), width=40).grid(row=0, column=i, pady=(0, 2))
        weeks = _calmod.Calendar(firstweekday=0).monthdayscalendar(state["y"], state["m"])
        for r, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                is_today = (state["y"] == today.year and state["m"] == today.month and day == today.day)

                def pick(dd=day):
                    result["val"] = f"{state['y']:04d}-{state['m']:02d}-{dd:02d}"
                    win.destroy()
                ctk.CTkButton(grid, text=str(day), command=pick, width=40, height=34, corner_radius=8,
                              fg_color=colors["accent"] if is_today else colors["card"],
                              hover_color=colors["accent_hover"],
                              text_color=colors["on_accent"] if is_today else colors["text"],
                              font=(FONT, 12)).grid(row=r, column=col, padx=2, pady=2)

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


# ----------------------------- Image selector -----------------------------
def image_selector(root, colors, folder_paths, max_per_folder, title, subtitle=""):
    """ติ๊กเลือกรูปต่อโฟลเดอร์ คืน {folder_path: [files]} หรือ None ถ้ายกเลิก"""
    win = _toplevel(root, colors, title, "1120x860")

    head = ctk.CTkFrame(win, fg_color="transparent"); head.pack(fill="x", padx=20, pady=(16, 2))
    ctk.CTkLabel(head, text=title, text_color=colors["accent"], font=(FONT, 16, "bold")).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(head, text=subtitle, text_color=colors["text_dim"], font=(FONT, 11)).pack(anchor="w")

    sel = {}
    refs = []
    count_var = tk.StringVar(value="เลือกแล้ว 0 รูป")

    def update_count():
        count_var.set(f"เลือกแล้ว {sum(len(v) for v in sel.values())} รูป")

    bar = ctk.CTkFrame(win, fg_color=colors["bg_alt"], corner_radius=0); bar.pack(fill="x", side="bottom")
    barin = ctk.CTkFrame(bar, fg_color="transparent"); barin.pack(fill="x", padx=20, pady=14)
    ctk.CTkLabel(barin, textvariable=count_var, text_color=colors["text"], font=(FONT, 12, "bold")).pack(side="left")
    confirmed = {"ok": False}

    def on_ok():
        final = {k: v for k, v in sel.items() if v}
        if not final:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกอย่างน้อย 1 รูป", parent=win)
            return
        confirmed["ok"] = True
        sel.clear(); sel.update(final)
        win.destroy()

    _btn(barin, "Confirm ✓", on_ok, colors, kind="accent", height=38, width=130,
         font=(FONT, 13, "bold")).pack(side="right")
    _btn(barin, "Cancel", win.destroy, colors, height=38, width=100,
         font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))

    scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=16, pady=10)

    for f_path in folder_paths:
        f_name = os.path.basename(f_path)
        row = ctk.CTkFrame(scroll, fg_color=colors["card"], corner_radius=10)
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=f_name, text_color=colors["text_dim"], font=("Consolas", 12, "bold"),
                     width=120, anchor="w").pack(side="left", padx=12, pady=10)
        img_container = ctk.CTkFrame(row, fg_color="transparent"); img_container.pack(side="left", fill="x", expand=True)
        try:
            files = sorted([f for f in os.listdir(f_path) if _is_image(f)])
        except Exception:
            files = []
        sel[f_path] = []
        if not files:
            ctk.CTkLabel(img_container, text="(ไม่มีรูปในโฟลเดอร์นี้)", text_color=colors["text_mute"],
                         font=(FONT, 11)).pack(side="left", padx=8)
        for f in files:
            try:
                full_p = os.path.join(f_path, f)
                img = Image.open(full_p); img.thumbnail((104, 104))
                cell = ctk.CTkFrame(img_container, fg_color=colors["card"], corner_radius=8,
                                    border_width=2, border_color=colors["card"])
                cell.pack(side="left", padx=4, pady=4)
                cimg = _ctk_img(img, img.size); refs.append(cimg)
                lbl = ctk.CTkLabel(cell, image=cimg, text="", cursor="hand2")
                lbl.pack(padx=3, pady=(3, 0))
                ctk.CTkLabel(cell, text=f, text_color=colors["text_mute"],
                             font=("Consolas", 9), wraplength=104).pack(padx=3, pady=(0, 3))

                def toggle(f_p=f_path, fn=f, frame=cell):
                    if fn in sel[f_p]:
                        sel[f_p].remove(fn)
                        frame.configure(border_color=colors["card"])
                    else:
                        if max_per_folder is not None and len(sel[f_p]) >= max_per_folder:
                            messagebox.showwarning("จำกัด", f"เลือกได้สูงสุด {max_per_folder} รูป/โฟลเดอร์", parent=win)
                            return
                        sel[f_p].append(fn)
                        frame.configure(border_color=colors["accent"])
                    update_count()
                lbl.bind("<Button-1>", lambda e, fn=f, fp=f_path, fr=cell: toggle(fp, fn, fr))
            except Exception:
                pass

    win._refs = refs
    root.wait_window(win)
    return dict(sel) if confirmed["ok"] else None


# ----------------------------- Primary chooser -----------------------------
def primary_chooser(root, colors, folder_path, files, folder_name, log=None):
    """เลือกรูปหลัก 1 รูป (ไฮไลต์ _AI). คืนชื่อไฟล์"""
    if len(files) <= 1:
        return files[0]

    def is_ai(f):
        return os.path.splitext(f)[0].lower().endswith("_ai")
    files = sorted(files, key=lambda f: (not is_ai(f), f.lower()))

    win = _toplevel(root, colors, f"เลือกรูปหลัก: {folder_name}", "1040x800")
    res = tk.StringVar()
    ctk.CTkLabel(win, text=f"เลือกรูปหลัก (PRIMARY) — โฟลเดอร์ {folder_name}", text_color=colors["accent"],
                 font=(FONT, 14, "bold")).pack(pady=(12, 0))
    ctk.CTkLabel(win, text="รูปกรอบเทอร์คอยซ์ = ผ่าน AI แล้ว (แนะนำให้เลือกเป็นรูปหลัก)",
                 text_color=colors["text_dim"], font=(FONT, 11)).pack(pady=(0, 8))
    gal = ctk.CTkScrollableFrame(win, fg_color="transparent")
    gal.pack(fill="both", expand=True, padx=12, pady=8)
    refs = []
    for i, f in enumerate(files):
        try:
            img = Image.open(os.path.join(folder_path, f)); img.thumbnail((158, 158))
            ai = is_ai(f)
            border = colors["accent"] if ai else colors["border"]
            cell = ctk.CTkFrame(gal, fg_color=colors["card"], corner_radius=10,
                                border_width=2 if ai else 1, border_color=border)
            cell.grid(row=i // 5, column=i % 5, padx=8, pady=8)
            if ai:
                ctk.CTkLabel(cell, text="✨ AI", fg_color=colors["accent"], text_color=colors["on_accent"],
                             font=(FONT, 10, "bold"), corner_radius=5).pack(anchor="w", padx=6, pady=(6, 0))
            cimg = _ctk_img(img, img.size); refs.append(cimg)
            lbl = ctk.CTkLabel(cell, image=cimg, text="", cursor="hand2"); lbl.pack(padx=6, pady=6)
            name = ctk.CTkLabel(cell, text=f, text_color=colors["accent"] if ai else colors["text_dim"],
                                font=("Consolas", 10, "bold" if ai else "normal"), wraplength=158, cursor="hand2")
            name.pack(padx=6, pady=(0, 6))
            for wdg in (lbl, name):
                wdg.bind("<Button-1>", lambda e, f=f: [res.set(f), win.destroy()])
        except Exception as e:
            if log:
                log(f"ข้ามตัวอย่าง {f}: {e}", "warning")
    win._refs = refs
    root.wait_window(win)
    return res.get() if res.get() else files[0]


# ----------------------------- Merge editor (คง tk.Canvas) -----------------------------
def merge_editor(root, colors, ai_paths, out_dir, folder_name, current, total, done_event):
    win = _toplevel(root, colors, f"MERGE: {folder_name} ({current}/{total})", "860x900")
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

    ctk.CTkLabel(win, text=f"รวมรูปต่างหู — {folder_name}  ({current}/{total})", text_color=colors["accent"],
                 font=(FONT, 14, "bold")).pack(pady=(12, 0))
    ctk.CTkLabel(win, text="ลากรูปในกรอบเพื่อย้าย · แถบ ZOOM แต่ละฝั่งเพื่อย่อ/ขยาย (ส่วนเกินกรอบถูกครอป)",
                 text_color=colors["text_dim"], font=(FONT, 11)).pack(pady=(0, 6))

    bar = ctk.CTkFrame(win, fg_color=colors["bg_alt"], corner_radius=0); bar.pack(side="bottom", fill="x")
    barin = ctk.CTkFrame(bar, fg_color="transparent"); barin.pack(fill="x", padx=20, pady=12)
    ctrl = ctk.CTkFrame(win, fg_color="transparent"); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 8))

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

    zl = ctk.CTkFrame(ctrl, fg_color="transparent"); zl.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ctk.CTkLabel(zl, text="ZOOM ซ้าย", text_color=colors["text"], font=(FONT, 11)).pack(anchor="w")
    ctk.CTkSlider(zl, from_=0.2, to=4.0, variable=zoom_vars[0], command=lambda v: apply_zoom(0),
                  progress_color=colors["accent"], button_color=colors["accent"]).pack(fill="x")
    zr = ctk.CTkFrame(ctrl, fg_color="transparent"); zr.pack(side="left", fill="x", expand=True, padx=(8, 8))
    ctk.CTkLabel(zr, text="ZOOM ขวา", text_color=colors["text"], font=(FONT, 11)).pack(anchor="w")
    ctk.CTkSlider(zr, from_=0.2, to=4.0, variable=zoom_vars[1], command=lambda v: apply_zoom(1),
                  progress_color=colors["accent"], button_color=colors["accent"]).pack(fill="x")

    def swap():
        base_imgs[0], base_imgs[1] = base_imgs[1], base_imgs[0]
        state[0], state[1] = state[1], state[0]
        zoom_vars[0].set(round(state[0]["scale"], 2)); zoom_vars[1].set(round(state[1]["scale"], 2))
        refresh()
    _btn(ctrl, "⇄ Swap", swap, colors, width=80, height=30).pack(side="left", padx=(0, 6))

    def reset():
        for i in range(2):
            state[i] = {"scale": 1.0, "ox": COMP // 4, "oy": COMP // 2}
            zoom_vars[i].set(1.0)
        refresh()
    _btn(ctrl, "Reset", reset, colors, width=80, height=30).pack(side="left")

    def save_and_next():
        build(COMP).save(os.path.join(out_dir, f"{folder_name}-merged.jpg"), "JPEG", quality=95, optimize=True)
        win.destroy(); done_event.set()
    _btn(barin, "Save & Next →", save_and_next, colors, kind="success", height=40,
         font=(FONT, 13, "bold")).pack(side="right")
    _btn(barin, "Skip", lambda: [win.destroy(), done_event.set()], colors, height=40,
         width=90, font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), done_event.set()])
    refresh()


# ----------------------------- Crop editor (คง tk.Canvas) -----------------------------
def crop_editor(root, colors, img_path, out_dir, filename, current, total, done_event):
    win = _toplevel(root, colors, f"CROP: {filename} ({current}/{total})", "860x900")
    COMP, PV = 2000, 640

    try:
        base = Image.open(img_path).convert("RGBA")
    except Exception as e:
        messagebox.showerror("Error", f"เปิดรูปไม่ได้: {e}", parent=win)
        win.destroy(); done_event.set(); return

    st = {"scale": 1.0, "cx": COMP / 2, "cy": COMP / 2}
    scale_var = tk.DoubleVar(value=1.0)
    bw, bh = base.size

    ctk.CTkLabel(win, text=f"ครอบตัด & จัดตำแหน่ง — {filename}  ({current}/{total})", text_color=colors["accent"],
                 font=(FONT, 14, "bold")).pack(pady=(12, 0))
    ctk.CTkLabel(win, text="ลากเพื่อย้ายรูป · ล้อเมาส์หรือแถบเลื่อนเพื่อซูมเข้า/ออก",
                 text_color=colors["text_dim"], font=(FONT, 11)).pack(pady=(0, 6))

    bar = ctk.CTkFrame(win, fg_color=colors["bg_alt"], corner_radius=0); bar.pack(side="bottom", fill="x")
    barin = ctk.CTkFrame(bar, fg_color="transparent"); barin.pack(fill="x", padx=20, pady=12)
    ctrl = ctk.CTkFrame(win, fg_color="transparent"); ctrl.pack(side="bottom", fill="x", padx=20, pady=(0, 6))

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

    ctk.CTkLabel(ctrl, text="ZOOM", text_color=colors["text"], width=50).pack(side="left")
    ctk.CTkSlider(ctrl, from_=0.1, to=3.0, variable=scale_var, command=lambda v: apply_scale(scale_var.get()),
                  progress_color=colors["accent"], button_color=colors["accent"]).pack(side="left", fill="x", expand=True)
    _btn(ctrl, "Reset", lambda: (st.update({"scale": 1.0, "cx": COMP / 2, "cy": COMP / 2}),
                                  scale_var.set(1.0), refresh()), colors,
         width=80, height=30).pack(side="left", padx=(10, 0))

    def save_and_next():
        build(COMP).save(img_path, "JPEG", quality=95, optimize=True)
        win.destroy(); done_event.set()
    _btn(barin, "Save & Next →", save_and_next, colors, kind="success", height=40,
         font=(FONT, 13, "bold")).pack(side="right")
    _btn(barin, "Skip", lambda: [win.destroy(), done_event.set()], colors, height=40,
         width=90, font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))

    win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), done_event.set()])
    refresh()


# ----------------------------- Collect preview (ทีละสินค้า) -----------------------------
def collect_preview(root, colors, plan):
    """พรีวิวทีละสินค้า: รูปต้นทาง + ปลายทางเดิม P1/P2 + เลือกแทน/ไม่แทน/ข้าม
    คืน {'allow_new': bool, 'decisions': {folder: 'replace'|'skip_dup'|'skip'}} หรือ None"""
    win = _toplevel(root, colors, "ตรวจสอบก่อนเก็บเข้าฐานข้อมูล", "940x800")
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

    ctk.CTkLabel(win, text="ตรวจสอบรูปหลัก & ปลายทางก่อนคัดลอก (ทีละสินค้า)", text_color=colors["accent"],
                 font=(FONT, 15, "bold")).pack(pady=(14, 2))
    counter_var = tk.StringVar()
    ctk.CTkLabel(win, textvariable=counter_var, text_color=colors["text_dim"],
                 font=(FONT, 12, "bold")).pack(pady=(0, 6))

    bar = ctk.CTkFrame(win, fg_color=colors["bg_alt"], corner_radius=0); bar.pack(side="bottom", fill="x")
    barin = ctk.CTkFrame(bar, fg_color="transparent"); barin.pack(fill="x", padx=20, pady=12)
    ctk.CTkCheckBox(barin, text="อนุญาตให้สร้างโฟลเดอร์ช่วงใหม่ (+)", variable=allow_new,
                    onvalue=True, offvalue=False, fg_color=colors["accent"], hover_color=colors["accent_hover"],
                    font=(FONT, 12)).pack(side="left")

    def ok():
        confirmed["ok"] = True; win.destroy()
    _btn(barin, "Confirm All →", ok, colors, kind="accent", height=40,
         font=(FONT, 13, "bold")).pack(side="right")
    _btn(barin, "Cancel", win.destroy, colors, height=40, width=90,
         font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))

    detail = ctk.CTkFrame(win, fg_color="transparent"); detail.pack(fill="both", expand=True, padx=16, pady=8)

    def _col(parent, title, img_path, status_txt=None, status_color=None, rel=None):
        f = ctk.CTkFrame(parent, fg_color=colors["card"], corner_radius=12, width=260, height=320)
        f.pack_propagate(False)
        ctk.CTkLabel(f, text=title, text_color=colors["text_dim"], font=(FONT, 12, "bold")).pack(pady=(12, 4))
        if img_path:
            try:
                img = Image.open(img_path); img.thumbnail((200, 200))
                cimg = _ctk_img(img, img.size); win._refs.append(cimg)
                ctk.CTkLabel(f, image=cimg, text="").pack(pady=6)
            except Exception:
                ctk.CTkLabel(f, text="(เปิดรูปไม่ได้)", text_color=colors["text_mute"]).pack(pady=40)
        else:
            ctk.CTkLabel(f, text="— ยังไม่มีรูปปลายทาง —\n(จะสร้างใหม่)", text_color=colors["text_mute"],
                         font=(FONT, 12)).pack(pady=60)
        if status_txt:
            ctk.CTkLabel(f, text=status_txt, text_color=status_color, font=(FONT, 12, "bold")).pack()
        if rel:
            ctk.CTkLabel(f, text=rel, text_color=colors["text_dim"], font=("Consolas", 10),
                         wraplength=230).pack(pady=(2, 0))
        return f

    def render():
        for w_ in detail.winfo_children():
            w_.destroy()
        win._refs.clear()
        item = plan[idx["i"]]
        counter_var.set(f"สินค้า {idx['i'] + 1} / {n}   ·   {item['file']}")

        cols = ctk.CTkFrame(detail, fg_color="transparent"); cols.pack()
        _col(cols, "📷 รูปต้นทาง (จะคัดลอก)", item["fpath"]).grid(row=0, column=0, padx=8)
        for c_i, key, lbl in ((1, "p1", "🗄 ปลายทาง P1 (ของเดิม)"), (2, "p2", "🗄 ปลายทาง P2 (ของเดิม)")):
            _t, rel, status = item[key]
            txt, color = status_label.get(status, (status, colors["text_dim"]))
            _col(cols, lbl, item[f"{key}_existing"], txt, color, rel).grid(row=0, column=c_i, padx=8)

        act = ctk.CTkFrame(detail, fg_color="transparent"); act.pack(pady=(14, 0), anchor="w", padx=8)
        ctk.CTkLabel(act, text="ทำอย่างไรกับสินค้านี้:", text_color=colors["text"],
                     font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 4))
        var = decisions[item["folder"]]
        for val, label in (("replace", "✓ แทนที่ — คัดลอกทับของเดิม (ถ้ามี)"),
                           ("skip_dup", "↷ ไม่แทนของเดิม — ข้ามเฉพาะปลายทางที่มีไฟล์ซ้ำ แต่ยังสร้างที่ยังไม่มี"),
                           ("skip", "✖ ข้ามสินค้านี้ — ไม่คัดลอกเลย")):
            ctk.CTkRadioButton(act, text=label, variable=var, value=val, fg_color=colors["accent"],
                               hover_color=colors["accent_hover"], font=(FONT, 12)).pack(anchor="w", pady=2)

        nav = ctk.CTkFrame(detail, fg_color="transparent"); nav.pack(fill="x", pady=(16, 0))
        if idx["i"] > 0:
            _btn(nav, "‹ Previous", lambda: go(-1), colors, height=34, width=110,
                 font=(FONT, 12, "bold")).pack(side="left")
        if idx["i"] < n - 1:
            _btn(nav, "Next ›", lambda: go(1), colors, height=34, width=110,
                 font=(FONT, 12, "bold")).pack(side="right")

    def go(d):
        idx["i"] = max(0, min(n - 1, idx["i"] + d)); render()

    render()
    root.wait_window(win)
    return ({"allow_new": allow_new.get(),
             "decisions": {k: v.get() for k, v in decisions.items()}}
            if confirmed["ok"] else None)


# ----------------------------- Import options -----------------------------
def import_options(root, colors):
    """เลือกโหมดนำเข้า คืน dict {mode, date_from, date_to, codes} หรือ None"""
    win = _toplevel(root, colors, "ตัวเลือกการนำเข้า", "560x600")
    ctk.CTkLabel(win, text="📥  ตัวเลือกการนำเข้ารูป", text_color=colors["accent"],
                 font=(FONT, 16, "bold")).pack(anchor="w", padx=24, pady=(20, 6))

    mode = tk.StringVar(value="new")
    opts = [
        ("new", "ดึงเฉพาะรูปใหม่ (จำที่เคยดึงแล้ว)", "แนะนำ — ดึงเฉพาะไฟล์ที่ยังไม่เคยนำเข้า"),
        ("all", "ดึงทั้งหมด (ไม่สนความจำ)", "ดึงทุกไฟล์ในโฟลเดอร์กล้อง รวมที่เคยดึงแล้ว"),
        ("date", "ดึงตามช่วงวันที่", "เฉพาะไฟล์ที่แก้ไขในช่วงวันที่ที่ระบุ"),
        ("codes", "ดึงเฉพาะรหัสที่ระบุ", "พิมพ์เลข 4 หลัก (หลายแบบ — ดูช่องด้านล่าง)"),
    ]
    body = ctk.CTkFrame(win, fg_color="transparent"); body.pack(fill="x", padx=22, pady=6)
    for val, title, desc in opts:
        cell = ctk.CTkFrame(body, fg_color=colors["card"], corner_radius=10); cell.pack(fill="x", pady=4)
        ctk.CTkRadioButton(cell, text=title, variable=mode, value=val, fg_color=colors["accent"],
                           hover_color=colors["accent_hover"], font=(FONT, 13, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(cell, text=desc, text_color=colors["text_dim"], font=(FONT, 11)).pack(anchor="w", padx=40, pady=(0, 10))

    extra = ctk.CTkFrame(win, fg_color="transparent"); extra.pack(fill="x", padx=24, pady=(4, 0))
    ctk.CTkLabel(extra, text="ช่วงวันที่ (กดปุ่ม 📅 หรือพิมพ์ YYYY-MM-DD):", text_color=colors["text_dim"],
                 font=(FONT, 11)).pack(anchor="w")
    drow = ctk.CTkFrame(extra, fg_color="transparent"); drow.pack(fill="x", pady=(2, 0))
    date_from = tk.StringVar(); date_to = tk.StringVar()

    def add_date_field(var):
        ctk.CTkEntry(drow, textvariable=var, width=120, font=("Consolas", 12),
                     fg_color=colors["input_bg"], border_width=0).pack(side="left")

        def pick():
            v = calendar_picker(win, colors, var.get().strip() or None)
            if v:
                var.set(v)
        _btn(drow, "📅", pick, colors, width=40, height=30).pack(side="left", padx=(4, 0))

    add_date_field(date_from)
    ctk.CTkLabel(drow, text="  ถึง  ", text_color=colors["text_dim"]).pack(side="left")
    add_date_field(date_to)
    ctk.CTkLabel(extra, text="รหัส (เช่น 1212,0789 · 1000 1001 · 1000-1005 · ปนกันได้):", text_color=colors["text_dim"],
                 font=(FONT, 11)).pack(anchor="w", pady=(8, 0))
    codes = tk.StringVar()
    ctk.CTkEntry(extra, textvariable=codes, font=("Consolas", 12), fg_color=colors["input_bg"],
                 border_width=0).pack(fill="x", pady=(2, 0))

    result = {}

    def ok():
        result.update({"mode": mode.get(), "date_from": date_from.get().strip(),
                       "date_to": date_to.get().strip(), "codes": codes.get().strip()})
        win.destroy()
    bar = ctk.CTkFrame(win, fg_color="transparent"); bar.pack(fill="x", side="bottom", padx=24, pady=16)
    _btn(bar, "Start Import →", ok, colors, kind="accent", height=42, font=(FONT, 13, "bold")).pack(side="right")
    _btn(bar, "Cancel", win.destroy, colors, height=42, width=100, font=(FONT, 12, "bold")).pack(side="right", padx=(0, 10))

    root.wait_window(win)
    return result if result else None
