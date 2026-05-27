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
