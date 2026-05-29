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

# JS: หา "รูปใหม่ที่ใหญ่พอ" ที่ยังไม่อยู่ใน baseline (known) — ไม่ผูกกับ DOM ของ assistant
_FIND_NEW_IMAGE_JS = """
(known) => {
    const set = new Set(known);
    const imgs = [...document.querySelectorAll('img')];
    let best = null, area = 0;
    for (const im of imgs) {
        const s = im.src || '';
        if (!s || s.length < 10) continue;
        if (set.has(s)) continue;
        // ข้ามไอคอน sprite/svg/อวาตาร์
        if (s.startsWith('data:image/svg')) continue;
        const w = im.naturalWidth || im.width || 0;
        const h = im.naturalHeight || im.height || 0;
        if (Math.min(w, h) < 200) continue;
        const a = w * h;
        if (a > area) { area = a; best = im; }
    }
    if (!best) return null;
    const r = best.getBoundingClientRect();
    return {src: best.src, x: r.x, y: r.y, w: r.width, h: r.height,
            nw: best.naturalWidth, nh: best.naturalHeight};
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

# JS: ดึงเฉพาะข้อความในคำตอบล่าสุดของ assistant + กล่อง dialog/alert (เลี่ยง sidebar/upsell)
_LIMIT_TEXT_JS = """
() => {
    let parts = [];
    const turns = document.querySelectorAll('[data-message-author-role="assistant"]');
    if (turns.length) parts.push(turns[turns.length - 1].innerText || '');
    document.querySelectorAll('[role="dialog"], [role="alert"]').forEach(d => parts.push(d.innerText || ''));
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


async def _wait_for_result(page, baseline, on_log, timeout_s=180):
    """
    รอรูปใหม่ (ไม่อยู่ใน baseline) จนนิ่ง
    คืน ("ok", info) | ("limit", message) | ("timeout", None)
    """
    last_src = None
    stable = 0
    waited = 0
    while waited < timeout_s:
        await asyncio.sleep(2)
        waited += 2

        limit_msg = await _check_limit(page)
        if limit_msg:
            return "limit", limit_msg

        try:
            info = await page.evaluate(_FIND_NEW_IMAGE_JS, baseline)
        except Exception:
            info = None
        generating = await _is_generating(page)

        if info and info.get("src"):
            if info["src"] == last_src and not generating:
                stable += 1
                if stable >= 2:
                    return "ok", info
            else:
                stable = 0
                last_src = info["src"]
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


async def _retouch_one(page, img_path, out_path, custom_gpt_url, on_log):
    """คืน (success, error, is_limit)"""
    filename = os.path.basename(img_path)
    try:
        target_url = custom_gpt_url.strip() if custom_gpt_url.strip() else "https://chatgpt.com"
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # ตรวจลิมิตก่อนเริ่ม (เผื่อโดนตั้งแต่เปิดหน้า)
        pre_limit = await _check_limit(page)
        if pre_limit:
            return False, f"ติดลิมิต: {pre_limit}", True

        on_log(f"    • อัปโหลด: {filename}")
        attach_selectors = [
            'button[aria-label="Attach files"]',
            'button[aria-label*="Attach" i]',
            'button[aria-label*="แนบ" i]',
            '[data-testid="attach-button"]',
            'button[aria-label="Add photos and files"]',
        ]
        for sel in attach_selectors:
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(0.5)
                break

        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(img_path)
        await asyncio.sleep(1.5)

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
        status, info = await _wait_for_result(page, baseline, on_log, timeout_s=180)

        if status == "limit":
            return False, f"ติดลิมิตการใช้งาน: {info}", True
        if status == "timeout" or not info:
            await _save_debug(page, img_path, on_log)
            return False, "Timeout: ไม่พบรูปผลลัพธ์ใหม่ในคำตอบของ AI", False

        on_log(f"    • พบรูปผลลัพธ์ ({info.get('nw')}x{info.get('nh')}) กำลังดาวน์โหลด...")
        await asyncio.sleep(1)
        ok = await _download_image(page, info, out_path, on_log)
        if ok:
            on_log(f"    • บันทึก: {os.path.basename(out_path)}", "success")
            return True, "", False
        return False, "ดาวน์โหลดรูปไม่สำเร็จ", False
    except Exception as e:
        return False, str(e), False


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


async def run_retouch(tasks, custom_gpt_url="", on_log=None, on_result=None, should_cancel=None, profile_dir=None):
    if on_log is None:
        on_log = lambda m, l="info": None
    if on_result is None:
        on_result = lambda f, s, e="": None
    if should_cancel is None:
        should_cancel = lambda: False

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        on_log(f"ไม่พบ Playwright: {e}  (ติดตั้งด้วย: pip install playwright && playwright install chromium)", "error")
        return

    async with async_playwright() as p:
        page, cleanup = await _acquire_page(p, on_log, profile_dir)

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
                img_path = os.path.join(folder_path, filename)
                name, ext = os.path.splitext(filename)
                out_path = os.path.join(folder_path, f"{name}_AI{ext}")
                on_log(f"[{done}/{total}] กำลังทำ: {filename} ใน {folder_name}")
                ok, err, is_limit = await _retouch_one(page, img_path, out_path, custom_gpt_url, on_log)
                on_result(filename, ok, err)
                if is_limit:
                    on_log("⛔ ติดลิมิตการใช้งาน ChatGPT — หยุดการทำงานทั้งหมด รูปที่เหลือยังไม่ถูกทำ", "error")
                    hit_limit = True
                    stopped = True
                    break
                if ok and done < total and not should_cancel():
                    on_log("    • รอ 5 วินาทีก่อนรูปถัดไป...")
                    await asyncio.sleep(5)

        await cleanup()
    if hit_limit:
        on_log("หยุดเพราะติดลิมิต — ลองใหม่ภายหลังเมื่อโควต้ารีเซ็ต", "warning")
    elif not should_cancel():
        on_log("ChatGPT retouching complete.", "success")


def run_retouch_blocking(tasks, custom_gpt_url="", on_log=None, on_result=None, should_cancel=None, profile_dir=None):
    asyncio.run(run_retouch(tasks, custom_gpt_url, on_log, on_result, should_cancel, profile_dir))


if __name__ == "__main__":
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
