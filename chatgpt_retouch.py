"""
PixUp - ChatGPT Auto Retouch (browser automation via Playwright)

ใช้ได้ 2 ทาง:
1. import แล้วเรียก run_retouch_blocking(tasks, url, on_log, on_result)  <- pixup.py ใช้ทางนี้ (in-process)
2. รันเป็นสคริปต์เดี่ยวเพื่อทดสอบ: python chatgpt_retouch.py '<tasks_json>' '<gpt_url>'

tasks = { folder_path: {"files": [f1, f2], "is_earring": bool}, ... }
"""
import asyncio
import base64
import json
import os
import sys
import time
import urllib.request

CDP_PORT = 9222

PROMPT = (
    "Please retouch this jewelry product photo to premium e-commerce standard. "
    "Replace background with pure white #ffffff. "
    "Keep exact jewelry design — do not alter stone count, gem shape, metal color, or proportions. "
    "Brighten naturally, preserve highlights, recover shadow detail. "
    "Remove dust, fingerprints, yellow cast, gray cast. "
    "For rings: keep shank crisp and faithful to original. "
    "For earrings: remove stands or fixtures that are not part of the product. "
    "Return only the final retouched image, no text."
)


# JS: เก็บ src ของรูปทั้งหมดบนหน้า (ใช้ทำ baseline ก่อนส่ง)
_SNAPSHOT_JS = """
() => [...document.querySelectorAll('img')].map(im => im.src).filter(s => s && s.length > 10)
"""

# JS: คืนผู้สมัคร 2 แบบในครั้งเดียว
#  gen = รูปที่ alt บอกว่า "ภาพที่สร้างขึ้น"/"generated image" (เชื่อถือได้สุด)
#  fb  = รูปใหม่ที่ใหญ่สุด ที่ "ไม่ใช่ไฟล์ที่อัปโหลด" (ใช้เป็นทางสำรองเฉพาะหลัง AI สร้างเสร็จ)
_FIND_NEW_IMAGE_JS = """
(args) => {
    const known = new Set(args.known || []);
    const uploaded = (args.uploaded || '').toLowerCase();
    const markers = ['ภาพที่สร้างขึ้น', 'สร้างขึ้น', 'generated image', 'image generated'];
    const imgs = [...document.querySelectorAll('img')];
    const rectOf = (im) => {
        const r = im.getBoundingClientRect();
        return {src: im.src, x: r.x, y: r.y, w: r.width, h: r.height,
                nw: im.naturalWidth, nh: im.naturalHeight, alt: im.alt || ''};
    };
    const isGen = (alt) => { alt = (alt || '').toLowerCase(); return markers.some(m => alt.includes(m)); };
    const looksLikeFilename = (alt) => /\\.(jpg|jpeg|png|webp|gif)$/i.test((alt || '').trim());

    // gen: รูปที่ alt บอกว่าเป็นภาพที่สร้างขึ้น (เอาตัวใหญ่สุด/ล่าสุด)
    let gen = null, gArea = 0;
    for (const im of imgs) {
        const w = im.naturalWidth || 0, h = im.naturalHeight || 0;
        if (Math.min(w, h) < 200) continue;
        if (!isGen(im.alt)) continue;
        const a = w * h;
        if (a >= gArea) { gArea = a; gen = im; }
    }

    // fb: รูปใหม่ที่ใหญ่สุด ที่ไม่ใช่ไฟล์อัปโหลด (กันไว้เป็นทางสำรอง)
    let best = null, area = 0;
    for (const im of imgs) {
        const s = im.src || '';
        if (!s || s.length < 10) continue;
        if (s.startsWith('data:image/svg')) continue;
        if (known.has(s)) continue;
        const alt = (im.alt || '').toLowerCase();
        if (looksLikeFilename(alt)) continue;        // ข้ามรูปที่ alt เป็นชื่อไฟล์ (=รูปอัปโหลด)
        if (uploaded && alt === uploaded) continue;   // ข้ามรูปที่เราอัปโหลด
        const w = im.naturalWidth || 0, h = im.naturalHeight || 0;
        if (Math.min(w, h) < 200) continue;
        const a = w * h;
        if (a > area) { area = a; best = im; }
    }
    return {gen: gen ? rectOf(gen) : null, fb: best ? rectOf(best) : null};
}
"""

# JS: นับรูปที่ "ใหญ่พอ" ทั้งหมด + ใหญ่สุด (ไว้ debug ตอนหาไม่เจอ)
_DEBUG_IMAGES_JS = """
() => {
    const imgs = [...document.querySelectorAll('img')];
    let big = 0, maxw = 0, maxh = 0;
    for (const im of imgs) {
        const w = im.naturalWidth || im.width || 0;
        const h = im.naturalHeight || im.height || 0;
        if (Math.min(w, h) >= 200) big++;
        if (w > maxw) maxw = w;
        if (h > maxh) maxh = h;
    }
    return {total: imgs.length, big: big, maxw: maxw, maxh: maxh};
}
"""

# วลีที่บ่งบอกว่า "ติดลิมิตจริง" — เลือกเฉพาะที่ไม่กำกวม (เลี่ยงคำ sidebar เช่น Upgrade)
_LIMIT_PHRASES = [
    "you've hit the", "you have hit the", "you've reached", "you have reached",
    "reached your limit", "hit your limit", "image generation limit",
    "limit for creating images", "create more images after", "able to create more",
    "try again later", "come back later", "rate limit", "too many requests",
    "ใช้งานครบ", "เกินขีดจำกัด", "ลองใหม่อีกครั้งภายหลัง", "สร้างรูปได้อีกครั้ง",
]

# JS: ดึงข้อความจาก <main> (พื้นที่สนทนา) + กล่อง dialog/alert — เลี่ยง sidebar/upsell (อยู่นอก main)
_LIMIT_TEXT_JS = """
() => {
    let parts = [];
    document.querySelectorAll('[role="dialog"], [role="alert"]').forEach(d => parts.push(d.innerText || ''));
    const main = document.querySelector('main');
    if (main) parts.push(main.innerText || '');
    return parts.join(' \\n ');
}
"""


async def _check_limit(page):
    """คืนข้อความเตือนถ้าเจอสัญญาณติดลิมิตในคำตอบ/ไดอะล็อก มิฉะนั้นคืน None"""
    try:
        txt = (await page.evaluate(_LIMIT_TEXT_JS) or "").lower()
    except Exception:
        return None
    for p in _LIMIT_PHRASES:
        if p in txt:
            idx = txt.find(p)
            snippet = txt[max(0, idx - 20): idx + 80].replace("\n", " ").strip()
            return snippet or p
    return None


async def _is_generating(page):
    """ChatGPT แสดงปุ่ม Stop ระหว่างกำลังสร้างคำตอบ"""
    for sel in ['button[aria-label*="Stop" i]', 'button[data-testid="stop-button"]',
                'button[aria-label*="หยุด" i]']:
        try:
            if await page.locator(sel).count() > 0:
                return True
        except Exception:
            pass
    return False


async def _snapshot_srcs(page):
    try:
        return await page.evaluate(_SNAPSHOT_JS)
    except Exception:
        return []


async def _wait_for_result(page, baseline, uploaded_name, on_log, timeout_s=180):
    """
    รอรูปผลลัพธ์ที่ AI สร้างจนนิ่ง
    หลักการ: ระหว่าง AI กำลังสร้าง (ปุ่ม Stop โชว์) จะไม่รับรูปใด ๆ (กันไปจับรูปอัปโหลด)
             แล้วจับรูปที่ alt = "ภาพที่สร้างขึ้น" เป็นหลัก; ถ้าไม่เจอ marker หลังสร้างเสร็จ
             สักพักค่อยใช้รูปสำรอง (fb)
    คืน ("ok", info) | ("limit", message) | ("timeout", None)
    """
    args = {"known": baseline, "uploaded": uploaded_name}
    last_src = None
    stable = 0
    waited = 0
    saw_generating = False
    no_marker_after_gen = 0
    while waited < timeout_s:
        await asyncio.sleep(2)
        waited += 2

        limit_msg = await _check_limit(page)
        if limit_msg:
            return "limit", limit_msg

        generating = await _is_generating(page)
        if generating:
            # AI กำลังสร้าง — ยังไม่รับรูป รีเซ็ตตัวนับ
            saw_generating = True
            last_src = None
            stable = 0
            continue

        try:
            res = await page.evaluate(_FIND_NEW_IMAGE_JS, args)
        except Exception:
            res = None
        gen = (res or {}).get("gen")
        fb = (res or {}).get("fb")

        # ทางหลัก: รูปที่ alt บอกว่า "ภาพที่สร้างขึ้น"
        if gen and gen.get("src"):
            if gen["src"] == last_src:
                stable += 1
                if stable >= 2:
                    return "ok", gen
            else:
                last_src = gen["src"]
                stable = 1
            continue

        # ทางสำรอง: ใช้ก็ต่อเมื่อเคยเห็น AI สร้าง (saw_generating) แล้วสร้างเสร็จ
        # แต่ยังไม่เจอ marker นานพอ (~8 วิ) — กันกรณี alt ไม่มี marker
        last_src = None
        stable = 0
        if saw_generating:
            no_marker_after_gen += 1
            if no_marker_after_gen >= 4 and fb and fb.get("src"):
                on_log("    • ไม่พบ alt 'ภาพที่สร้างขึ้น' ใช้รูปใหม่ที่ใหญ่สุดแทน", "info")
                return "ok", fb
    return "timeout", None


async def _download_image(page, info, out_path, on_log):
    src = info.get("src")
    # 1) ดึงผ่าน context ของหน้า (ใช้ cookie เดียวกัน) รองรับ blob:/data:/https
    try:
        b64 = await page.evaluate(
            """
            async (src) => {
                const resp = await fetch(src);
                const blob = await resp.blob();
                return await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }
            """,
            src,
        )
        if b64:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
    except Exception as e:
        on_log(f"    • ดาวน์โหลดแบบ fetch ไม่ได้ ({e}) ลองวิธีถ่ายภาพหน้าจอ", "info")

    # 2) Fallback: ถ่ายภาพเฉพาะกรอบรูป (ได้ผลเสมอ ไม่ติด CORS)
    try:
        rect = {"x": info["x"], "y": info["y"], "width": info["w"], "height": info["h"]}
        if rect["width"] > 5 and rect["height"] > 5:
            await page.screenshot(path=out_path, clip=rect)
            return True
    except Exception as e:
        on_log(f"    • ถ่ายภาพหน้าจอไม่สำเร็จ: {e}", "info")

    return False


async def _save_debug(page, img_path, on_log):
    """เซฟภาพหน้าจอ + รายงานจำนวนรูปบนหน้า เมื่อหารูปผลลัพธ์ไม่เจอ"""
    try:
        dbg = await page.evaluate(_DEBUG_IMAGES_JS)
        on_log(f"    • DEBUG: รูปบนหน้า={dbg['total']} | รูปใหญ่พอ(≥200px)={dbg['big']} "
               f"| ใหญ่สุด={dbg['maxw']}x{dbg['maxh']}", "warning")
    except Exception:
        pass
    try:
        shot = os.path.join(os.path.dirname(img_path),
                            "_debug_" + os.path.splitext(os.path.basename(img_path))[0] + ".png")
        await page.screenshot(path=shot, full_page=True)
        on_log(f"    • บันทึกภาพหน้าจอ debug: {os.path.basename(shot)} (ส่งให้ผู้พัฒนาดูได้)", "warning")
    except Exception:
        pass


async def _is_logged_in(page):
    """ตรวจว่าล็อกอิน ChatGPT แล้วหรือยัง (เจอช่องพิมพ์ = ล็อกอินแล้ว)"""
    for sel in ['#prompt-textarea', 'div[contenteditable="true"]',
                'button[data-testid="send-button"]', 'input[type="file"]']:
        try:
            if await page.locator(sel).count() > 0:
                return True
        except Exception:
            pass
    # มีปุ่ม Log in / Sign up เด่น = ยังไม่ล็อกอิน
    return False


async def _ensure_logged_in(page, on_log, wait_s=180):
    """ถ้ายังไม่ล็อกอิน รอให้ผู้ใช้ล็อกอินในเบราว์เซอร์ (ไม่ fail ทันที)"""
    if await _is_logged_in(page):
        return True
    on_log("    ⚠ ยังไม่ได้ล็อกอิน ChatGPT — กรุณาล็อกอินในเบราว์เซอร์ที่เปิดอยู่", "warning")
    waited = 0
    while waited < wait_s:
        await asyncio.sleep(3)
        waited += 3
        if await _is_logged_in(page):
            on_log("    ✓ ล็อกอินแล้ว ทำงานต่อ", "success")
            return True
    on_log("    ✖ ยังไม่ล็อกอินภายในเวลาที่กำหนด", "error")
    return False


async def _attach_file(page, img_path, on_log):
    """แนบไฟล์ + รอจนอัปโหลดขึ้นจริง (เน็ตช้า) คืน True/False"""
    attach_selectors = [
        'button[aria-label="Attach files"]', 'button[aria-label*="Attach" i]',
        'button[aria-label*="แนบ" i]', '[data-testid="attach-button"]',
        'button[aria-label="Add photos and files"]',
    ]
    before = await _snapshot_srcs(page)
    for sel in attach_selectors:
        btn = page.locator(sel)
        try:
            if await btn.count() > 0:
                await btn.click(); await asyncio.sleep(0.5); break
        except Exception:
            pass
    try:
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(img_path)
    except Exception as e:
        on_log(f"    • แนบไฟล์ไม่ได้: {e}", "info")
        return False
    # รอ thumbnail ของไฟล์ที่แนบขึ้น (รูปใหม่โผล่ หรือมี progressbar หาย) — สูงสุด 30 วิ
    for _ in range(30):
        await asyncio.sleep(1)
        now = await _snapshot_srcs(page)
        if len(now) > len(before):
            return True
    return True  # ไม่เจอ thumbnail ชัด แต่ปล่อยให้ลองส่งต่อ


async def _retouch_one(page, img_path, out_path, custom_gpt_url, on_log):
    """คืน (success, error, is_limit)"""
    filename = os.path.basename(img_path)
    try:
        target_url = custom_gpt_url.strip() if custom_gpt_url.strip() else "https://chatgpt.com"
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        if not await _ensure_logged_in(page, on_log):
            return False, "ยังไม่ได้ล็อกอิน ChatGPT", True  # หยุดทั้ง batch

        # ตรวจลิมิตก่อนเริ่ม (เผื่อโดนตั้งแต่เปิดหน้า)
        pre_limit = await _check_limit(page)
        if pre_limit:
            return False, f"ติดลิมิต: {pre_limit}", True

        on_log(f"    • อัปโหลด: {filename}")
        attached = await _attach_file(page, img_path, on_log)
        if not attached:
            on_log("    • ลองแนบไฟล์ใหม่อีกครั้ง...", "warning")
            await asyncio.sleep(1)
            await _attach_file(page, img_path, on_log)
        await asyncio.sleep(1)

        # baseline หลังแนบรูป (รวมรูปที่เราอัปโหลด) ก่อนกดส่ง
        baseline = await _snapshot_srcs(page)
        on_log("    • แนบไฟล์แล้ว กำลังส่ง prompt...")

        if not custom_gpt_url.strip():
            for sel in ['#prompt-textarea', 'div[contenteditable="true"][data-placeholder]', 'div[contenteditable="true"]']:
                ta = page.locator(sel).first
                if await ta.count() > 0:
                    await ta.click()
                    await ta.fill(PROMPT)
                    break

        for sel in ['button[data-testid="send-button"]', 'button[aria-label="Send message"]',
                    'button[aria-label*="Send" i]', 'button[aria-label*="ส่ง" i]']:
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.click()
                break

        on_log("    • รอ AI สร้างรูป (ไม่เกิน 3 นาที)...")
        status, info = await _wait_for_result(page, baseline, filename, on_log, timeout_s=180)

        if status == "limit":
            return False, f"ติดลิมิตการใช้งาน: {info}", True
        if status == "timeout" or not info:
            await _save_debug(page, img_path, on_log)
            return False, "Timeout: ไม่พบรูปผลลัพธ์ใหม่ในคำตอบของ AI", False

        on_log(f"    • พบรูปผลลัพธ์ ({info.get('nw')}x{info.get('nh')}) กำลังดาวน์โหลด...")
        await asyncio.sleep(1)
        ok = await _download_image(page, info, out_path, on_log)
        if ok:
            _finalize_image(out_path, img_path, on_log)
            on_log(f"    • บันทึก: {os.path.basename(out_path)}", "success")
            return True, "", False
        return False, "ดาวน์โหลดรูปไม่สำเร็จ", False
    except Exception as e:
        return False, str(e), False


def _finalize_image(out_path, original_path, on_log):
    """แปลงไฟล์ที่ดาวน์โหลด (มักเป็น WebP/PNG) ให้เป็นฟอร์แมตตามนามสกุลจริง 'เสมอ'
    + ขยายให้ด้านยาวเท่าต้นฉบับถ้าเล็กกว่า — กันปัญหาไฟล์ .jpg ที่เปิดไม่ได้"""
    try:
        from PIL import Image
        with Image.open(original_path) as orig:
            ow, oh = orig.size
        is_jpeg = out_path.lower().endswith((".jpg", ".jpeg"))
        with Image.open(out_path) as ai:
            ai.load()
            img = ai
            aw, ah = img.size
            target = max(ow, oh)
            cur = max(aw, ah)
            resized = False
            if cur < target:  # เล็กกว่าต้นฉบับ → ขยายด้วย Lanczos
                scale = target / cur
                new_size = (round(aw * scale), round(ah * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                resized = True
            # บันทึกใหม่ตามนามสกุลจริงเสมอ (รับประกันว่าเนื้อในตรงกับนามสกุล)
            if is_jpeg:
                if img.mode != "RGB":
                    img = img.convert("RGB")  # ตัด alpha/พาเลตต์ ป้องกัน JPEG เสีย
                img.save(out_path, "JPEG", quality=95, optimize=True)
            elif out_path.lower().endswith(".png"):
                img.save(out_path, "PNG")
            else:
                img.save(out_path)
        if resized:
            on_log(f"    • ขยายเป็น {img.size[0]}x{img.size[1]} ให้เท่าต้นฉบับ", "info")
    except Exception as e:
        on_log(f"    • แปลง/ขยายรูปไม่สำเร็จ (ใช้ไฟล์เดิม): {e}", "info")


def _default_profile_dir():
    return os.path.join(os.path.expanduser("~"), ".pixup", "chrome_profile")


def _cdp_alive():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=1)
        return True
    except Exception:
        return False


async def _acquire_page(p, on_log, profile_dir=None):
    """
    คืน (page, cleanup_async).
    ลำดับ: 1) ถ้ามี Chrome ที่เปิด remote-debugging (port 9222) อยู่ → ต่อกับอันนั้น
           2) เปิด Chrome ด้วยโปรไฟล์ที่กำหนด (persistent) — ล็อกอินครั้งเดียว จำตลอด
    """
    # 1) ต่อ Chrome ที่ผู้ใช้เปิดด้วย --remote-debugging-port=9222 เอง (โหมดขั้นสูง)
    if _cdp_alive():
        on_log("    • พบ Chrome remote-debugging (9222) — เชื่อมต่อกับเบราว์เซอร์ที่เปิดอยู่", "success")
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        async def cleanup():
            try:
                await page.close()
            except Exception:
                pass
        return page, cleanup

    # 2) เปิดด้วยโปรไฟล์ persistent (ค่าเริ่มต้น = โปรไฟล์ของ PixUp ที่ล็อกอินครั้งเดียว)
    profile = profile_dir.strip() if (profile_dir and profile_dir.strip()) else _default_profile_dir()
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        pass
    on_log(f"    • โปรไฟล์เบราว์เซอร์: {profile}")
    on_log("    • ครั้งแรกให้ล็อกอิน ChatGPT ในหน้าต่างนี้ครั้งเดียว ครั้งต่อไปจะจำให้อัตโนมัติ", "warning")

    async def _launch(channel=None):
        kwargs = {
            "headless": False,
            "viewport": {"width": 1366, "height": 768},
            "args": ["--disable-blink-features=AutomationControlled", "--start-maximized",
                     "--no-first-run", "--no-default-browser-check"],
        }
        if channel:
            kwargs["channel"] = channel
        return await p.chromium.launch_persistent_context(profile, **kwargs)

    try:
        ctx = await _launch(channel="chrome")
    except Exception as e:
        on_log(f"    • เปิด Google Chrome ไม่ได้ ({e})", "warning")
        if profile_dir and profile_dir.strip():
            on_log("    • ถ้าตั้งค่าโปรไฟล์ Chrome หลักไว้ ให้ปิด Chrome ให้หมดก่อนแล้วลองใหม่", "warning")
        on_log("    • ใช้ Chromium ของ Playwright แทน", "warning")
        ctx = await _launch()
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    async def cleanup():
        try:
            await ctx.close()
        except Exception:
            pass
    return page, cleanup


async def run_retouch(tasks, custom_gpt_url="", on_log=None, on_result=None, should_cancel=None,
                      profile_dir=None, on_progress=None):
    if on_log is None:
        on_log = lambda m, l="info": None
    if on_result is None:
        on_result = lambda f, s, e="": None
    if should_cancel is None:
        should_cancel = lambda: False
    if on_progress is None:
        on_progress = lambda c, t: None

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        on_log(f"ไม่พบ Playwright: {e}  (ติดตั้งด้วย: pip install playwright && playwright install chromium)", "error")
        return

    async with async_playwright() as p:
        try:
            page, cleanup = await _acquire_page(p, on_log, profile_dir)
        except Exception as e:
            on_log(f"เปิดเบราว์เซอร์ไม่ได้: {e}", "error")
            return

        total = sum(len(v["files"]) for v in tasks.values())
        done = 0
        stopped = False
        hit_limit = False
        for folder_path, info in tasks.items():
            if stopped:
                break
            folder_name = os.path.basename(folder_path)
            for filename in info["files"]:
                if should_cancel():
                    on_log("    • ได้รับคำสั่งยกเลิก หยุดการทำงาน", "warning")
                    stopped = True
                    break
                done += 1
                on_progress(done, total)
                img_path = os.path.join(folder_path, filename)
                name, ext = os.path.splitext(filename)
                out_path = os.path.join(folder_path, f"{name}_AI{ext}")
                started = time.time()
                on_log(f"[{done}/{total}] กำลังทำ: {filename} ใน {folder_name}")

                # ลองทำ + retry 1 ครั้งถ้า fail (ไม่ใช่ลิมิต)
                ok, err, is_limit = await _retouch_one(page, img_path, out_path, custom_gpt_url, on_log)
                if (not ok) and (not is_limit) and (not should_cancel()):
                    on_log("    ↻ ลองใหม่อีกครั้ง (รอบที่ 2)...", "warning")
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(2)
                    except Exception:
                        pass
                    ok, err, is_limit = await _retouch_one(page, img_path, out_path, custom_gpt_url, on_log)

                on_result(filename, ok, err)
                if ok:
                    on_log(f"    • ใช้เวลา {time.time() - started:.0f}s", "info")
                if is_limit:
                    on_log("⛔ ติดลิมิต/ล็อกอินมีปัญหา — หยุดทั้งหมด รูปที่เหลือยังไม่ถูกทำ", "error")
                    hit_limit = True
                    stopped = True
                    break
                if ok and done < total and not should_cancel():
                    on_log("    • รอ 5 วินาทีก่อนรูปถัดไป...")
                    await asyncio.sleep(5)

        await cleanup()
    if hit_limit:
        on_log("หยุดเพราะติดลิมิต/ล็อกอิน — ลองใหม่ภายหลัง", "warning")
    elif not should_cancel():
        on_log("ChatGPT retouching complete.", "success")


def run_retouch_blocking(tasks, custom_gpt_url="", on_log=None, on_result=None, should_cancel=None,
                         profile_dir=None, on_progress=None):
    asyncio.run(run_retouch(tasks, custom_gpt_url, on_log, on_result, should_cancel, profile_dir, on_progress))


# ============================ DEBUG / INSPECT MODE ============================
# JS: ลิสต์ทุก <img> บนหน้าแบบละเอียด เพื่อให้เห็นว่าระบบมองเห็นรูปอะไรบ้าง
_INSPECT_JS = """
() => {
    const inAssistant = (el) => !!el.closest('[data-message-author-role="assistant"]');
    const imgs = [...document.querySelectorAll('img')].map((im, i) => {
        const r = im.getBoundingClientRect();
        return {
            i: i,
            nw: im.naturalWidth || 0,
            nh: im.naturalHeight || 0,
            dw: Math.round(r.width),
            dh: Math.round(r.height),
            assistant: inAssistant(im),
            srcHead: (im.src || '').slice(0, 90),
            alt: (im.alt || '').slice(0, 40),
        };
    });
    const turns = document.querySelectorAll('[data-message-author-role="assistant"]');
    const lastHtml = turns.length ? turns[turns.length - 1].outerHTML.slice(0, 4000) : '(no assistant turn)';
    return {count: imgs.length, imgs: imgs, lastAssistantHtml: lastHtml};
}
"""


async def run_inspect(image_path="", custom_gpt_url="", profile_dir=None):
    """โหมดตรวจสอบ: เปิดเบราว์เซอร์ ให้ผู้ใช้ทำรีทัช 1 รูปเอง แล้ว dump สิ่งที่ระบบเห็นเป็นไฟล์ debug_report.txt"""
    def log(m, l="info"):
        print(m, flush=True)

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        print(f"ไม่พบ Playwright: {e}")
        return

    out_dir = os.path.dirname(os.path.abspath(image_path)) if image_path else os.getcwd()
    report_path = os.path.join(out_dir, "debug_report.txt")
    shot_path = os.path.join(out_dir, "debug_fullpage.png")

    async with async_playwright() as p:
        page, cleanup = await _acquire_page(p, log, profile_dir)
        target = custom_gpt_url.strip() or "https://chatgpt.com"
        await page.goto(target, wait_until="domcontentloaded", timeout=30000)

        print("\n" + "=" * 60)
        print("  PixUp INSPECT MODE")
        print("  1) ถ้ายังไม่ล็อกอิน ChatGPT ให้ล็อกอินในเบราว์เซอร์ที่เปิดขึ้น")
        print("  2) อัปโหลดรูป + สั่งรีทัช + รอจนรูปผลลัพธ์ออกมาครบ")
        print("  3) กลับมาที่หน้าต่างนี้แล้วกด Enter เพื่อเก็บข้อมูล")
        print("=" * 60 + "\n")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, ">>> กด Enter เมื่อรูปผลลัพธ์ออกมาแล้ว... ")

        try:
            data = await page.evaluate(_INSPECT_JS)
        except Exception as e:
            data = {"count": -1, "imgs": [], "lastAssistantHtml": f"(evaluate error: {e})"}

        try:
            await page.screenshot(path=shot_path, full_page=True)
        except Exception:
            pass

        lines = []
        lines.append(f"PixUp debug report")
        lines.append(f"URL: {page.url}")
        lines.append(f"จำนวน <img> ทั้งหมด: {data.get('count')}")
        lines.append("")
        lines.append("idx | natural(WxH) | shown(WxH) | inAssistant | alt | srcHead")
        lines.append("-" * 70)
        for im in data.get("imgs", []):
            lines.append(f"{im['i']:>3} | {im['nw']}x{im['nh']} | {im['dw']}x{im['dh']} | "
                         f"{im['assistant']} | {im['alt']!r} | {im['srcHead']}")
        lines.append("")
        lines.append("===== HTML ของคำตอบล่าสุดของ assistant (ตัด 4000 ตัวอักษร) =====")
        lines.append(data.get("lastAssistantHtml", ""))

        report = "\n".join(lines)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print("\n" + report[:2000])
        print("\n... (เต็มในไฟล์)")
        print(f"\n✔ บันทึกแล้ว:\n   {report_path}\n   {shot_path}")
        print("➜ ส่งเนื้อหา debug_report.txt (และรูป debug_fullpage.png ถ้าได้) ให้ผู้พัฒนา\n")

        await loop.run_in_executor(None, input, ">>> กด Enter เพื่อปิดเบราว์เซอร์... ")
        await cleanup()


if __name__ == "__main__":
    # โหมด inspect:  python chatgpt_retouch.py --inspect [image_path] [custom_gpt_url]
    if len(sys.argv) > 1 and sys.argv[1] == "--inspect":
        img = sys.argv[2] if len(sys.argv) > 2 else ""
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        asyncio.run(run_inspect(img, url))
        sys.exit(0)

    def _log(m, l="info"):
        print(json.dumps({"type": "log", "level": l, "msg": m}, ensure_ascii=False), flush=True)

    def _res(f, s, e=""):
        print(json.dumps({"type": "result", "file": f, "success": s, "error": e}, ensure_ascii=False), flush=True)

    tasks_arg = sys.argv[1] if len(sys.argv) > 1 else "{}"
    gpt_url = sys.argv[2] if len(sys.argv) > 2 else ""
    try:
        tasks = json.loads(tasks_arg)
    except Exception:
        tasks = {}
    run_retouch_blocking(tasks, gpt_url, _log, _res)
