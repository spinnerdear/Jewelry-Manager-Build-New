"""
PixUp - Workflow (ตรรกะแต่ละขั้นตอน)
ทุกฟังก์ชันรับ `app` (PixUpApp) เป็น context — อ่าน Tk vars / log / progress ผ่าน app
heavy work รันใน threading.Thread, อัปเดต widget ผ่าน app.*_threadsafe เท่านั้น
"""
import os
import re
import time
import shutil
import threading
from datetime import datetime

import dialogs

try:
    import chatgpt_retouch
    HAS_CHATGPT = True
except Exception:
    HAS_CHATGPT = False

EXCLUDE_DIRS = ("ai_retouched", "_rename_temp")


# ----------------------------- helpers -----------------------------
def _folders(app, src):
    return sorted([os.path.join(src, d) for d in os.listdir(src)
                   if os.path.isdir(os.path.join(src, d)) and d not in EXCLUDE_DIRS])


def _summary(app, name, ok=0, fail=0, skip=0, t0=None):
    parts = [f"สำเร็จ {ok}"]
    if fail:
        parts.append(f"ล้มเหลว {fail}")
    if skip:
        parts.append(f"ข้าม {skip}")
    if t0 is not None:
        parts.append(f"ใช้เวลา {time.time() - t0:.1f}s")
    cat = "error" if fail and not ok else "success"
    app.log_threadsafe(f"[{name}] เสร็จสิ้น — {', '.join(parts)}", cat)


def _check_drive(app, paths):
    missing = [p for p in paths if p and not os.path.exists(p)]
    return missing


def _disk_free_gb(path):
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except Exception:
        return None


# ----------------------------- Phase: Import (หลายโหมด) -----------------------------
def phase_import(app):
    cam = app.camera_source.get()
    dst = app.source_dir.get()
    if not cam or not os.path.exists(cam):
        app.error("ยังไม่ได้ตั้งค่า 'โฟลเดอร์กล้อง' หรือหาไม่พบ\nไปตั้งค่าในหน้า ⚙ Settings", "E001")
        return
    if not dst:
        app.error("ยังไม่ได้เลือกโฟลเดอร์ Workspace ปลายทาง")
        return
    if not os.path.exists(dst):
        try:
            os.makedirs(dst)
        except Exception as e:
            app.error(str(e)); return

    opt = dialogs.import_options(app.root, app.colors)
    if not opt:
        app.log("ขั้นนำเข้า: ยกเลิก", "warning")
        return

    def task():
        t0 = time.time()
        app.set_running("import", True)
        app.set_progress_threadsafe(0, 100)
        manifest = app.load_manifest()
        mode = opt["mode"]
        app.log_threadsafe(f"[นำเข้า] โหมด: {mode} | กล้อง: {cam}", "highlight")

        try:
            all_files = [f for f in os.listdir(cam)
                         if os.path.isfile(os.path.join(cam, f)) and app.is_media_file(f)]
        except Exception as e:
            app.log_threadsafe(f"อ่านโฟลเดอร์กล้องไม่ได้: {e}", "error", "E003")
            app.set_running("import", False); return

        # filter ตามโหมด
        date_from = date_to = None
        if mode == "date":
            date_from = _parse_date(opt.get("date_from"))
            date_to = _parse_date(opt.get("date_to"), end=True)
        wanted_codes = None
        if mode == "codes":
            wanted_codes = {c.strip() for c in opt.get("codes", "").split(",") if c.strip()}
            if not wanted_codes:
                app.log_threadsafe("ไม่ได้ระบุรหัส — ยกเลิก", "warning")
                app.set_running("import", False); return

        candidates = []
        for f in all_files:
            full = os.path.join(cam, f)
            try:
                st = os.stat(full)
                sig = f"{f}|{st.st_size}|{int(st.st_mtime)}"
            except Exception:
                continue
            if mode == "new" and sig in manifest:
                continue
            if mode == "date":
                if date_from and st.st_mtime < date_from:
                    continue
                if date_to and st.st_mtime > date_to:
                    continue
            if mode == "codes":
                m = re.search(r'(\d{4})', f)
                if not (m and m.group(1) in wanted_codes):
                    continue
            candidates.append((f, full, sig))

        if not candidates:
            app.log_threadsafe("ไม่มีไฟล์ตรงเงื่อนไขให้นำเข้า", "warning")
            app.set_running("import", False); return

        app.log_threadsafe(f"[นำเข้า] พบ {len(candidates)} ไฟล์ กำลังคัดลอก...", "highlight")
        ok = fail = 0
        total = len(candidates)
        for i, (f, full, sig) in enumerate(candidates):
            app.set_count_threadsafe(i + 1, total)
            m = re.search(r'(\d{4})', f)
            code = m.group(1) if m else "_ungrouped"
            target_dir = os.path.join(dst, code)
            try:
                os.makedirs(target_dir, exist_ok=True)
                dest = os.path.join(target_dir, f)
                if os.path.exists(dest):
                    name, ext = os.path.splitext(f)
                    dest = os.path.join(target_dir, f"{name}_dup{ext}")
                shutil.copy2(full, dest)
                manifest.add(sig); ok += 1
                app.log_threadsafe(f"  ({i+1}/{total}) {f} → {code}/", "info")
            except Exception as e:
                fail += 1
                app.log_threadsafe(f"คัดลอกไม่สำเร็จ {f}: {e}", "error", "E007")
            app.set_progress_threadsafe((i + 1) / total * 100)

        app.save_manifest(manifest)
        app.log_threadsafe("ต้นฉบับยังอยู่ที่เดิม (คัดลอก ไม่ย้าย)", "info")
        _summary(app, "นำเข้า", ok=ok, fail=fail, t0=t0)
        app.mark_completed("import")
        app.set_count_threadsafe(0, 0)
        app.set_running("import", False)
    threading.Thread(target=task, daemon=True).start()


def _parse_date(s, end=False):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            if end:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.timestamp()
        except Exception:
            continue
    return None


# ----------------------------- Phase: Group by code (Tools/ฉุกเฉิน) -----------------------------
def phase_group(app):
    src = app.source_dir.get()
    if not src or not os.path.exists(src):
        app.error("ไม่พบ Workspace", "E001"); return
    files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
    if not files:
        app.error("ไม่พบไฟล์ใน Workspace", "E002"); return

    def task():
        t0 = time.time(); app.set_running("group", True)
        ok = fail = 0; total = len(files)
        for i, f in enumerate(files):
            app.set_count_threadsafe(i + 1, total)
            m = re.search(r'(\d{4})', f)
            if m:
                c = m.group(1); t = os.path.join(src, c)
                os.makedirs(t, exist_ok=True)
                try:
                    shutil.move(os.path.join(src, f), os.path.join(t, f)); ok += 1
                except Exception as e:
                    fail += 1
                    app.log_threadsafe(f"ย้ายไม่สำเร็จ {f}: {e}", "error", "E007")
            app.set_progress_threadsafe((i + 1) / total * 100)
        _summary(app, "จัดกลุ่ม", ok=ok, fail=fail, t0=t0)
        app.set_count_threadsafe(0, 0)
        app.set_running("group", False)
    threading.Thread(target=task, daemon=True).start()


# ----------------------------- Phase: Merge (รวมรูปต่างหู) -----------------------------
def phase_merge(app):
    src = app.source_dir.get()
    if not src or not os.path.exists(src):
        app.error("ไม่พบ Workspace", "E001"); return
    folders = _folders(app, src)
    if not folders:
        app.error("ยังไม่มีโฟลเดอร์ ทำขั้นนำเข้าก่อน"); return

    sel = dialogs.image_selector(app.root, app.colors, folders, 2,
                                 "เลือก 2 รูปต่อโฟลเดอร์เพื่อรวม (Merge)",
                                 "เลือกรูปหน้า/ข้าง ในแต่ละโฟลเดอร์ที่จะรวม แล้วกดยืนยัน")
    if not sel:
        app.log("ขั้นรวมรูป: ยกเลิก", "warning"); return
    merge_list = [(k, v) for k, v in sel.items() if len(v) == 2]
    if not merge_list:
        app.error("ต้องเลือกครบ 2 รูปในโฟลเดอร์ที่จะรวม"); return

    def task():
        t0 = time.time(); app.set_running("merge", True)
        total = len(merge_list); ok = 0
        app.log_threadsafe(f"[รวมรูป] เริ่ม {total} โฟลเดอร์", "highlight")
        for i, (f_path, files) in enumerate(merge_list):
            app.set_count_threadsafe(i + 1, total)
            f_n = os.path.basename(f_path)
            paths = [os.path.join(f_path, f) for f in files]
            app.log_threadsafe(f"  ({i+1}/{total}) รวม: {f_n}", "info")
            ev = threading.Event()
            app.root.after(0, lambda p=paths, d=f_path, n=f_n, idx=i + 1, tot=total, e=ev:
                           dialogs.merge_editor(app.root, app.colors, p, d, n, idx, tot, e))
            ev.wait()
            ok += 1
            app.set_progress_threadsafe((i + 1) / total * 100)
        _summary(app, "รวมรูป", ok=ok, t0=t0)
        app.mark_completed("merge")
        app.set_count_threadsafe(0, 0)
        app.set_running("merge", False)
    threading.Thread(target=task, daemon=True).start()


# ----------------------------- Phase: Crop -----------------------------
def phase_crop(app):
    src = app.source_dir.get()
    if not src or not os.path.exists(src):
        app.error("ไม่พบ Workspace", "E001"); return
    folders = _folders(app, src)
    if not folders:
        app.error("ยังไม่มีโฟลเดอร์ ทำขั้นนำเข้าก่อน"); return

    sel = dialogs.image_selector(app.root, app.colors, folders, None,
                                 "เลือกรูปที่จะครอบตัด (เลือกได้หลายรูป)",
                                 "ติ๊กเลือกรูปที่ต้องการครอบตัด แล้วกดยืนยัน — ระบบจะดึงมาให้ครอบตัดทีละรูป")
    if not sel:
        app.log("ขั้นครอบตัด: ยกเลิก", "warning"); return
    crop_list = [(os.path.join(fp, f), fp, f) for fp, files in sel.items() for f in files]
    if not crop_list:
        return

    def task():
        t0 = time.time(); app.set_running("crop", True)
        total = len(crop_list); ok = 0
        app.log_threadsafe(f"[ครอบตัด] เริ่ม {total} รูป", "highlight")
        for i, (img_path, out_dir, fname) in enumerate(crop_list):
            app.set_count_threadsafe(i + 1, total)
            app.log_threadsafe(f"  ({i+1}/{total}) ครอบตัด: {fname}", "info")
            ev = threading.Event()
            app.root.after(0, lambda p=img_path, d=out_dir, n=fname, idx=i + 1, tot=total, e=ev:
                           dialogs.crop_editor(app.root, app.colors, p, d, n, idx, tot, e))
            ev.wait()
            ok += 1
            app.set_progress_threadsafe((i + 1) / total * 100)
        _summary(app, "ครอบตัด", ok=ok, t0=t0)
        app.mark_completed("crop")
        app.set_count_threadsafe(0, 0)
        app.set_running("crop", False)
    threading.Thread(target=task, daemon=True).start()


# ----------------------------- Phase: AI Retouch (ChatGPT) -----------------------------
def phase_ai(app):
    src = app.source_dir.get()
    if not src or not os.path.exists(src):
        app.error("ไม่พบ Workspace", "E001"); return
    if not HAS_CHATGPT:
        app.error("โหลดโมดูล chatgpt_retouch ไม่ได้ (ตรวจไฟล์ chatgpt_retouch.py)")
        return
    folders = _folders(app, src)
    if not folders:
        app.error("ยังไม่มีโฟลเดอร์ ทำขั้นนำเข้าก่อน"); return

    sel = dialogs.image_selector(app.root, app.colors, folders, None,
                                 "เลือกรูปสำหรับรีทัช AI",
                                 "ติ๊กเลือกรูปที่จะส่งเข้า ChatGPT (ควรรวม/ครอปก่อนแล้ว) แล้วกดยืนยัน")
    if not sel:
        app.log("ขั้น AI: ยกเลิก", "warning"); return
    tasks = {k: {"files": v} for k, v in sel.items() if v}
    if not tasks:
        return
    app.ai_tasks = tasks
    total = sum(len(v["files"]) for v in tasks.values())
    app.log(f"[AI] เริ่มรีทัช {total} รูป ใน {len(tasks)} โฟลเดอร์", "highlight")
    app.ai_cancel_event.clear()
    app.set_running("ai", True)
    app.ai_set_cancel_ui()
    threading.Thread(target=lambda: _ai_worker(app), daemon=True).start()


def _ai_worker(app):
    t0 = time.time()
    gpt_url = app.chatgpt_url.get().strip()
    profile = app.chrome_profile_dir.get().strip()
    counters = {"ok": 0, "fail": 0}

    def on_log(msg, level="info"):
        app.log_threadsafe(msg, level)

    def on_result(fname, success, error=""):
        if success:
            counters["ok"] += 1
            app.log_threadsafe(f"  ✓ รีทัชสำเร็จ: {fname}", "success")
        else:
            counters["fail"] += 1
            app.log_threadsafe(f"  ✖ ล้มเหลว {fname}: {error}", "error")

    def on_progress(cur, total):
        app.set_count_threadsafe(cur, total)
        app.set_progress_threadsafe(cur, total)

    try:
        chatgpt_retouch.run_retouch_blocking(
            app.ai_tasks, gpt_url, on_log, on_result,
            should_cancel=app.ai_cancel_event.is_set,
            profile_dir=profile, on_progress=on_progress)
    except Exception as e:
        app.log_threadsafe(f"AI automation error: {e}", "error")

    if app.ai_cancel_event.is_set():
        app.log_threadsafe("[AI] ยกเลิกแล้ว", "warning")
    else:
        _summary(app, "AI", ok=counters["ok"], fail=counters["fail"], t0=t0)
        app.mark_completed("ai")
    app.set_count_threadsafe(0, 0)
    app.ai_restore_ui()
    app.set_running("ai", False)


# ----------------------------- Phase: Rename & Primary -----------------------------
def phase_rename(app):
    src = app.source_dir.get()
    if not src or not os.path.exists(src):
        app.error("ไม่พบ Workspace", "E001"); return
    folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d not in EXCLUDE_DIRS]
    if not folders:
        app.error("ไม่พบโฟลเดอร์ ทำขั้นนำเข้าก่อน"); return

    def task():
        t0 = time.time(); app.set_running("rename", True)
        total = len(folders); ok = 0
        for i, folder_name in enumerate(folders):
            app.set_count_threadsafe(i + 1, total)
            base_path = os.path.join(src, folder_name)
            files = sorted([f for f in os.listdir(base_path) if app.is_media_file(f)])
            if files:
                ev = threading.Event()
                app.root.after(0, lambda f=files, n=folder_name, b=base_path, e=ev:
                               _do_rename(app, b, f, n, e))
                ev.wait()
                ok += 1
            app.set_progress_threadsafe((i + 1) / total * 100)
        _summary(app, "เปลี่ยนชื่อ", ok=ok, t0=t0)
        app.mark_completed("rename")
        app.set_count_threadsafe(0, 0)
        app.set_running("rename", False)
    threading.Thread(target=task, daemon=True).start()


def _do_rename(app, base_path, files, folder_name, done_event):
    """ทำงานบน main thread (มี dialog) แล้ว set event"""
    try:
        images = [f for f in files if app.is_image_file(f)]
        if images:
            main_file = dialogs.primary_chooser(app.root, app.colors, base_path, images, folder_name, app.log)
            if not main_file:
                return
        else:
            main_file = files[0] if files else None
        if not main_file:
            return

        temp_dir = os.path.join(base_path, "_rename_temp")
        if os.path.exists(temp_dir):
            app.log(f"พบ _rename_temp ของ {folder_name} อยู่แล้ว ข้ามเพื่อกันไฟล์กู้คืนถูกเขียนทับ", "error", "E007")
            return
        os.makedirs(temp_dir)
        planned = {}
        ext = os.path.splitext(main_file)[1].lower()
        planned[main_file] = f"{folder_name}{ext}"
        counter = 2
        for f in files:
            if f == main_file:
                continue
            e = os.path.splitext(f)[1].lower()
            planned[f] = f"{folder_name}-{counter}{e}"; counter += 1
        for f in files:
            shutil.move(os.path.join(base_path, f), os.path.join(temp_dir, f))
        for original, final in planned.items():
            final_path = os.path.join(base_path, final)
            if os.path.exists(final_path):
                os.replace(final_path, os.path.join(temp_dir, f"existing_{final}"))
            shutil.copy2(os.path.join(temp_dir, original), final_path)
        shutil.rmtree(temp_dir)
        app.log(f"เปลี่ยนชื่อสำเร็จ: {folder_name} ({len(planned)} ไฟล์)", "success")
    except Exception as e:
        app.log(f"เปลี่ยนชื่อไม่สำเร็จ {folder_name}: {e}. ไฟล์กู้คืนอยู่ใน _rename_temp", "error", "E007")
    finally:
        done_event.set()


# ----------------------------- Phase: Collect to DB -----------------------------
def get_range(num):
    start = ((num - 1) // 200) * 200 + 1
    return f"{start:03d}-{start + 199:03d}"


def _nearest_range_dir(cat_dir, r_v):
    if not os.path.isdir(cat_dir):
        return None
    best, best_d = None, None
    for d in os.listdir(cat_dir):
        full = os.path.join(cat_dir, d)
        if not os.path.isdir(full):
            continue
        mm = re.search(r'(\d+)\s*-\s*(\d+)', d)
        if not mm:
            continue
        lo, hi = int(mm.group(1)), int(mm.group(2))
        if lo <= r_v <= hi:
            return full
        dist = min(abs(r_v - lo), abs(r_v - hi))
        if best_d is None or dist < best_d:
            best_d, best = dist, full
    return best


def resolve_dest(app, dest_base, f_n):
    """คืน (target_dir, rel, status): exists|nearest|new|no_category"""
    p_t = app.type_mapping.get(f_n[0].upper(), "Other")
    m = re.search(r'(\d+)', f_n); r_v = int(m.group(1)) if m else 0
    if "-VN-" in f_n.upper():
        rel = os.path.join("Vincentio", p_t)
        target = os.path.join(dest_base, rel)
        if os.path.isdir(target):
            return target, rel, "exists"
        return target, rel, ("new" if os.path.isdir(os.path.join(dest_base, "Vincentio")) else "no_category")
    cat_dir = os.path.join(dest_base, p_t)
    exact_rel = os.path.join(p_t, f"{p_t} {get_range(r_v)}")
    exact = os.path.join(dest_base, exact_rel)
    if os.path.isdir(exact):
        return exact, exact_rel, "exists"
    if not os.path.isdir(cat_dir):
        return exact, exact_rel, "no_category"
    near = _nearest_range_dir(cat_dir, r_v)
    if near:
        return near, os.path.relpath(near, dest_base), "nearest"
    return exact, exact_rel, "new"


def phase_collect(app):
    src, p1, p2 = app.source_dir.get(), app.photo1_dir.get(), app.photo2_dir.get()
    if not all([src, p1, p2]):
        app.error("กรุณาตั้งค่า Photo 1 และ Photo 2 ในหน้า ⚙ Settings"); return
    missing = _check_drive(app, [src, p1, p2])
    if missing:
        app.error(f"{app.error_codes['E005']}\n" + "\n".join(missing)); return
    for d in (p1, p2):
        free = _disk_free_gb(d)
        if free is not None and free < 0.5:
            app.log(f"⚠ พื้นที่เหลือน้อยใน {d} ({free:.2f} GB)", "warning")

    plan = []
    for f_n in sorted([d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)) and d not in EXCLUDE_DIRS]):
        f_p = os.path.join(src, f_n)
        primaries = [f for f in os.listdir(f_p)
                     if app.is_image_file(f) and os.path.splitext(f)[0].lower() == f_n.lower()]
        if not primaries:
            continue
        plan.append({"folder": f_n, "file": primaries[0], "fpath": os.path.join(f_p, primaries[0]),
                     "p1": resolve_dest(app, p1, f_n), "p2": resolve_dest(app, p2, f_n)})
    if not plan:
        app.error("ไม่พบรูปหลัก (ทำขั้นเปลี่ยนชื่อก่อน)"); return

    result = dialogs.collect_preview(app.root, app.colors, plan)
    if not result:
        app.log("ขั้นเก็บเข้าฐานข้อมูล: ยกเลิก", "warning"); return
    allow_new = result["allow_new"]

    def task():
        t0 = time.time(); app.set_running("collect", True)
        ok = fail = skip = 0; total = len(plan)
        for i, item in enumerate(plan):
            app.set_count_threadsafe(i + 1, total)
            f_n, f_src, fname = item["folder"], item["fpath"], item["file"]
            for key in ("p1", "p2"):
                target, rel, status = item[key]
                if status == "no_category":
                    app.log_threadsafe(f"ข้าม {f_n} → ไม่พบหมวดใน {key.upper()} ({rel})", "warning"); skip += 1; continue
                if status == "new" and not allow_new:
                    app.log_threadsafe(f"ข้าม {f_n} → ปลายทางใหม่ ({rel}) ยังไม่อนุญาตสร้าง", "warning"); skip += 1; continue
                try:
                    os.makedirs(target, exist_ok=True)
                    shutil.copy2(f_src, os.path.join(target, fname)); ok += 1
                except Exception as e:
                    fail += 1
                    app.log_threadsafe(f"คัดลอกล้มเหลว {f_n} → {target}: {e}", "error", "E007")
            app.set_progress_threadsafe((i + 1) / total * 100)
        _summary(app, "เก็บเข้าฐานข้อมูล", ok=ok, fail=fail, skip=skip, t0=t0)
        app.mark_completed("collect")
        app.set_count_threadsafe(0, 0)
        app.set_running("collect", False)
    threading.Thread(target=task, daemon=True).start()


# ----------------------------- Phase: Archive -----------------------------
def phase_archive(app):
    src, arc = app.source_dir.get(), app.archive_dir.get()
    if not all([src, arc]) or not os.path.exists(src):
        app.error("ไม่พบ Workspace หรือคลัง", "E001"); return
    if not app.confirm("ยืนยันย้ายเข้าคลัง", f"ย้ายทุกโฟลเดอร์ใน Workspace เข้าคลัง?\n(เป็นการ 'ย้าย' ไฟล์ออกจาก Workspace)"):
        return

    def task():
        t0 = time.time(); app.set_running("archive", True)
        now = datetime.now()
        path = os.path.join(arc, now.strftime("%Y"), now.strftime("%m-%Y"), now.strftime("%d-%m-%Y"))
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            app.log_threadsafe(f"สร้างโฟลเดอร์คลังไม่ได้: {e}", "error", "E007")
            app.set_running("archive", False); return
        folders = [d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))]
        ok = fail = 0; total = len(folders)
        for i, f_n in enumerate(folders):
            app.set_count_threadsafe(i + 1, total)
            try:
                shutil.move(os.path.join(src, f_n), os.path.join(path, f_n)); ok += 1
            except Exception as e:
                fail += 1
                app.log_threadsafe(f"ย้ายเข้าคลังล้มเหลว {f_n}: {e}", "error", "E007")
            app.set_progress_threadsafe((i + 1) / max(total, 1) * 100)
        _summary(app, "คลัง", ok=ok, fail=fail, t0=t0)
        app.mark_completed("archive")
        app.set_count_threadsafe(0, 0)
        app.set_running("archive", False)
    threading.Thread(target=task, daemon=True).start()
