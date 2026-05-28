# PixUp Handoff Log

Use this file as the shared handoff point between Codex, Gemini CLI, and human edits.

## Working Rules

- Primary local repo: `/Users/ksdear/Documents/PixUp`
- Remote: `https://github.com/spinnerdear/Jewelry-Manager-Build-New.git`
- Before changing code, read `git status`, this file, and `GEMINI.md`.
- Do not hardcode API keys, tokens, passwords, or customer data.
- Prefer small commits with clear messages over one large mixed change.
- If a phase moves, deletes, or overwrites files, keep recovery behavior and visible error logging.
- When handing off, add a dated note below with: author/tool, files changed, tests run, and remaining risk.

### 2026-05-28 (PM) - Claude Code — v2.2 Beta 1 (รื้อใหญ่)

Changed files:
- `pixup.py` (เขียนใหม่เกือบทั้งไฟล์), `chatgpt_retouch.py`, `requirements.txt`, `GEMINI.md`
- ลบ `check_quota.py` (helper ของ API)

Summary:
- **ลบ Gemini API ออกทั้งหมด:** เอา `google-genai`, `retouch_with_gemini_image`, `gemini_agent_process`, `extract_code`, `execute_local_retouch_code`, `merge_earring_views`, ตัวแปร `gemini_key`/`ai_mode`, error E006, ช่อง API key UI ออก (free tier image model โควต้า = 0)
- **เพิ่มขั้นตอนที่ 0 — Import New (BETA):** ดึงรูปใหม่จาก Camera Source (`D:/gemlight box`) อัตโนมัติ
    - จำไฟล์ที่เคยดึงด้วย signature `filename|size|mtime` ใน `~/.pixup/imported_manifest.json` → ไม่ดึงซ้ำ
    - **Copy** (ไม่ move) แยกตามรหัส 4 หลักทันที, ไฟล์ไม่มีรหัสไป `_ungrouped`, ชนชื่อใช้ suffix `_dup`
    - ปุ่ม Reset Import Memory ในหน้า Settings
    - **คงปุ่มขั้นตอนที่ 1 (Group) ไว้** สำหรับเคสดาวน์โหลดเอง
- **1.5 = ChatGPT only:** เลือกรูป → `chatgpt_retouch.py` (Playwright) อัปโหลด/รีทัช/ดาวน์โหลดเป็น `_AI`
- **1.6 Merge:** ปรับให้เลือก 2 รูป/โฟลเดอร์เองผ่าน selector (เลิกผูกกับ ai_tasks/is_earring)
- **1.7 Crop:** ปรับให้เลือกรูปที่จะ crop ก่อน (หลายรูป) แล้ววน crop ทีละรูป
- **UI ใหม่ทั้งหมด — Wizard/Stepper:** Header+ปุ่ม ⚙ Settings, แถบ Workspace, stepper แนวนอนคลิกได้ (0..4) มี pulse/✓/spinner, content panel ต่อขั้น, log console พับได้, Settings เป็นหน้าต่างแยก, palette ใหม่
- bump เป็น **v2.2 Beta 1**

Validation (บน macOS — รัน GUI จริงไม่ได้):
- Passed: `python3 -m py_compile pixup.py chatgpt_retouch.py`
- grep ไม่เหลือ reference ของสัญลักษณ์ที่ลบทั้งหมด
- Dry-run logic ขั้นตอน 0 ผ่าน: รอบแรก copy 4 ไฟล์ (ข้าม .txt), จัดกลุ่ม 0789/1212/_ungrouped ถูกต้อง, ต้นฉบับยังอยู่ (copy ไม่ move), รอบสอง copy 0 (จำได้), เพิ่มไฟล์ใหม่ copy เฉพาะไฟล์ใหม่, manifest JSON round-trip ผ่าน

Remaining risks:
- **ยังไม่ได้ทดสอบ GUI จริง** — ต้องเปิดบน Windows เพื่อยืนยันหน้าตา/stepper/animation/selectors
- `chatgpt_retouch.py` พึ่ง DOM ของ ChatGPT — ถ้า ChatGPT เปลี่ยน UI selector อาจต้องปรับ; การดาวน์โหลดรูปยังไม่ได้ทดสอบกับ ChatGPT จริง
- **Build exe:** ต้องรวม `chatgpt_retouch.py` เข้า bundle และเครื่องปลายทางต้องติดตั้ง Playwright + Chromium (`pip install playwright && playwright install chromium`) — ตรวจ `.github/workflows/build.yml` ก่อน release
- Camera Source default ว่าง — ผู้ใช้ต้องตั้งค่า `D:/gemlight box` ในหน้า Settings บนเครื่อง Windows


Changed files:
- `pixup.py`
- `HANDOFF.md`

Summary:
- **Critical AI Fix (v2.1 Beta 14):** แก้ปัญหาหลักที่ทำให้ขั้นตอน AI Retouch (1.5) ใช้งานไม่ได้เลย
    - **ปัญหา 1 - ใช้ Model ผิด:** เปลี่ยนจาก `gemini-2.5-flash` (text-only model) เป็น `gemini-2.0-flash-preview-image-generation` ซึ่งเป็น image editing model ที่รับภาพเข้าและคืนภาพที่แก้แล้วออกมาได้จริง
    - **ปัญหา 2 - Dead Code:** โค้ดที่รับภาพกลับ (lines 748-765 เดิม) อยู่หลัง `return` จึงไม่รันเลย ลบออกและเขียน image output parsing ใหม่ให้ถูกต้อง
    - **ปัญหา 3 - Code Generation Approach:** วิธีให้ AI เขียน Python code แล้ว execute local ไม่ทำงานเพราะ PIL ไม่มีความสามารถลบ background ลบทิ้ง ใช้ direct image I/O แทน
    - **ปรับ API Format:** ใช้ `types.Part.from_bytes()` และ `types.GenerateContentConfig(response_modalities=["IMAGE","TEXT"])` ตามมาตรฐาน google-genai SDK ใหม่
    - **Parse Response ใหม่:** อ่านภาพจาก `response.candidates[0].content.parts` → `part.inline_data.data` (bytes) → แปลงกลับเป็น PIL Image

Validation:
- Passed: `python3 -m py_compile pixup.py`

Remaining risks:
- `gemini-2.0-flash-preview-image-generation` ยังเป็น preview model อาจมีการเปลี่ยน API หรือ deprecate ในอนาคต
- Rate limit ของ model นี้อาจแตกต่างจาก gemini-2.5-flash ให้ monitor ถ้าเจอ 429 บ่อย

### 2026-05-27 - Gemini CLI

Changed files:
- `pixup.py`
- `GEMINI.md`
- `HANDOFF.md`

Summary:
- **Rate Limit & Stability Fixes (v2.1 Beta 4):**
    - **Exponential Backoff:** Added a retry loop in `retouch_with_gemini_image`. It now retries up to 5 times (4 retries + 1 initial) with doubling wait times (4s, 8s, 16s, 32s) when hitting 429/RESOURCE_EXHAUSTED errors.
    - **Throttling:** Added a 3.5-second sleep between image requests in `gemini_agent_process` to stay within the 15 RPM Free Tier limit.
    - **Image Optimization:** 
        - Reduced thumbnail size to **1200px** (from 1600px) before upload to save Tokens Per Minute (TPM).
        - Added JPEG quality compression at **85%** and `optimize=True` when saving retouched results.
- **Improved Logging:** Enhanced the log messages to show retry attempts and throttling status.
- **Bug Fix:** Fixed `NameError` where `api_key` was used instead of `key` in the AI process thread.

Validation:
- Passed: `python3 -m py_compile pixup.py`.
- Logical verification of retry loop and throttling timer.

Remaining risks:
- Persistent network issues or a completely exhausted daily quota (1500 RPD) will still result in a critical error after retries.

## Current Status

### 2026-05-26 - Codex (Original Updates)
- Investigated build size (removed rembg/opencv).
- Added gemini-2.5-flash-image support.
- Security updates (no hardcoded keys).
