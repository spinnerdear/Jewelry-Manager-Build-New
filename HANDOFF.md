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

### 2026-05-28 - Claude Code

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
