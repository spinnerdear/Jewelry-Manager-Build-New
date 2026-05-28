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


async def _wait_for_generated_image(page, timeout_s=120):
    selectors = [
        '[data-message-author-role="assistant"] img[src*="oaiusercontent"]',
        '[data-message-author-role="assistant"] img[src*="blob:"]',
        '.group img[alt*="Generated"]',
        '[data-message-author-role="assistant"] img',
    ]
    for _ in range(timeout_s):
        await asyncio.sleep(1)
        for sel in selectors:
            els = page.locator(sel)
            if await els.count() > 0:
                last_img = els.last
                src = await last_img.get_attribute("src")
                if src and len(src) > 20:
                    return last_img, src
    return None, None


async def _download_image(page, img_element, out_path, on_log):
    try:
        img_src = await img_element.get_attribute("src")
        b64 = await page.evaluate(
            """
            async (src) => {
                const resp = await fetch(src);
                const blob = await resp.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }
            """,
            img_src,
        )
        if b64:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
    except Exception as e:
        on_log(f"    • download (fetch) ล้มเหลว: {e}", "info")

    try:
        await img_element.hover()
        await asyncio.sleep(0.5)
        dl_btn = page.locator('[aria-label*="Download" i], [aria-label*="download" i], button[download]').last
        if await dl_btn.count() > 0:
            async with page.expect_download() as dl_info:
                await dl_btn.click()
            download = await dl_info.value
            await download.save_as(out_path)
            return True
    except Exception as e:
        on_log(f"    • download (button) ล้มเหลว: {e}", "info")

    return False


async def _retouch_one(page, img_path, out_path, custom_gpt_url, on_log):
    filename = os.path.basename(img_path)
    try:
        target_url = custom_gpt_url.strip() if custom_gpt_url.strip() else "https://chatgpt.com"
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

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

        on_log("    • รอ AI สร้างรูป (ไม่เกิน 2 นาที)...")
        img_el, src = await _wait_for_generated_image(page, timeout_s=120)
        if not img_el:
            return False, "Timeout: ไม่มีรูปกลับมาภายใน 2 นาที"

        await asyncio.sleep(2)
        on_log("    • ได้รูปแล้ว กำลังดาวน์โหลด...")
        ok = await _download_image(page, img_el, out_path, on_log)
        if ok:
            on_log(f"    • บันทึก: {os.path.basename(out_path)}", "success")
            return True, ""
        return False, "ดาวน์โหลดรูปไม่สำเร็จ"
    except Exception as e:
        return False, str(e)


def _default_profile_dir():
    return os.path.join(os.path.expanduser("~"), ".pixup", "chrome_profile")


async def run_retouch(tasks, custom_gpt_url="", on_log=None, on_result=None, user_data_dir=None):
    if on_log is None:
        on_log = lambda m, l="info": None
    if on_result is None:
        on_result = lambda f, s, e="": None

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        on_log(f"ไม่พบ Playwright: {e}  (ติดตั้งด้วย: pip install playwright && playwright install chromium)", "error")
        return

    # Persistent profile = ล็อกอิน ChatGPT ครั้งเดียว แล้วจำ session ไว้ครั้งต่อไป
    profile = user_data_dir or _default_profile_dir()
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        pass
    on_log(f"    • ใช้โปรไฟล์เบราว์เซอร์: {profile}")
    on_log("    • ครั้งแรกให้ล็อกอิน ChatGPT ในหน้าต่างที่เปิดขึ้น — ครั้งต่อไปจะจำ session ให้", "warning")

    async with async_playwright() as p:
        launch_args = {
            "headless": False,
            "viewport": {"width": 1366, "height": 768},
            "args": ["--disable-blink-features=AutomationControlled", "--start-maximized"],
        }
        try:
            # ใช้ Google Chrome ของเครื่อง (โปรไฟล์ที่ล็อกอินไว้)
            context = await p.chromium.launch_persistent_context(profile, channel="chrome", **launch_args)
        except Exception as e:
            on_log(f"    • เปิด Chrome ไม่ได้ ({e}) — ใช้ Chromium ของ Playwright แทน", "warning")
            context = await p.chromium.launch_persistent_context(profile, **launch_args)

        page = context.pages[0] if context.pages else await context.new_page()

        total = sum(len(v["files"]) for v in tasks.values())
        done = 0
        for folder_path, info in tasks.items():
            folder_name = os.path.basename(folder_path)
            for filename in info["files"]:
                done += 1
                img_path = os.path.join(folder_path, filename)
                name, ext = os.path.splitext(filename)
                out_path = os.path.join(folder_path, f"{name}_AI{ext}")
                on_log(f"[{done}/{total}] กำลังทำ: {filename} ใน {folder_name}")
                ok, err = await _retouch_one(page, img_path, out_path, custom_gpt_url, on_log)
                on_result(filename, ok, err)
                if ok and done < total:
                    on_log("    • รอ 5 วินาทีก่อนรูปถัดไป...")
                    await asyncio.sleep(5)

        await context.close()
    on_log("ChatGPT retouching complete.", "success")


def run_retouch_blocking(tasks, custom_gpt_url="", on_log=None, on_result=None):
    asyncio.run(run_retouch(tasks, custom_gpt_url, on_log, on_result))


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
