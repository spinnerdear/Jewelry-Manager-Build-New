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

## Current Status

### 2026-05-26 - Gemini CLI

Changed files:
- `jewelry_manager.py` -> `pixup.py`
- `GEMINI.md`
- `README.md`
- `HANDOFF.md`

Summary:
- **Project Rebranding:** Renamed everything from "Jewelry Manager" to **PixUp**.
- **Version Release:** Upgraded to **v2.1 Beta 1**.
- **Interactive Features:** 
    - Added **1.6 Earring Merge** (Interactive scale, swap, and 2000x2000 canvas).
    - Added **1.7 Smart Crop** (Interactive zoom, pan, and 2000x2000 canvas).
- **UI Refresh:** Rearranged AI tools (1.5, 1.6, 1.7) into a single compact row for better UX.
- **Infrastructure:** Updated config directory to `.pixup` and standardized config file to `config_v2_1.json`.

Validation:
- Passed: `python3 -m py_compile pixup.py`.
- Verified all title and brand references in UI and Docs.

Remaining risks:
- Local config from older versions (`.jewelry_manager`) will not be automatically migrated; users need to re-enter paths or manually move files to `.pixup`.

---

### 2026-05-26 - Gemini CLI (Previous Updates)
- Removed local retouching fallback.
- Added Gemini Error handling (Quota/Auth).
- Added 1.5 Visual Selection.

### 2026-05-26 - Codex (Original Updates)
- Investigated build size (removed rembg/opencv).
- Added gemini-2.5-flash-image support.
- Security updates (no hardcoded keys).
