# PixUp Handoff Log

บันทึกการส่งต่องาน — ปัจจุบันพัฒนาผ่าน **Claude Code** เป็นหลัก

## Working Rules

- Primary local repo: `/Users/ksdear/Documents/PixUp`
- Remote: GitHub `spinnerdear/PixUp`
- **คู่มือโปรเจกต์หลัก = `CLAUDE.md`** (อ่านก่อนเริ่มงานทุกครั้ง พร้อมไฟล์นี้). `GEMINI.md` เก็บไว้เป็นบันทึกประวัติ
- Before changing code, read `git status`, this file, and `CLAUDE.md`.
- Do not hardcode API keys, tokens, passwords, or customer data.
- Prefer small commits with clear messages over one large mixed change.
- If a phase moves, deletes, or overwrites files, keep recovery behavior and visible error logging.
- When handing off, add a dated note below with: author/tool, files changed, tests run, and remaining risk.

### 2026-05-30 (#5) - Claude Code — v2.4 (แก้ตามฟีดแบ็กเทส Windows)

ต่อบน `customtkinter-ui` หลังผู้ใช้เทส .exe Beta 1 บน Windows (เปิดได้ ✓)
- เอา "Beta" ออก → version = **2.4**
- **แก้ขั้นที่ 7 หาย:** ลด step button height 40→34/pady, log 210→140, window 1160x840 → 7 ขั้นแสดงครบ
- **ปุ่ม Crop เว้นระยะแปลก:** เอา emoji ✂️ ออกจากปุ่ม Start (ใช้ "▶ Start {sub}" ทุกขั้น) → ระยะเท่ากัน
- **ปุ่มทั้งหมดเป็นอังกฤษ** (sidebar=sub อังกฤษ, Settings/Select Folder/Start/Previous/Next/Open.../Add/Delete,
  section headers, dialog buttons Confirm/Cancel/Save&Next/Skip/Swap/Reset) — **หัวข้อ/คำอธิบาย/tips/log คงไทย**
- **แก้ไอคอนหน้าต่างผิด:** bundle `app_icon.ico` เข้า .exe (`--add-data`) + ยิง `iconbitmap` ซ้ำ 200/500/1000/1800ms
  ให้ชนะที่ CTk รีเซ็ต (เดิมไม่ได้ bundle .ico → resource_path หาไม่เจอ → ใช้ไอคอน default)

### 2026-05-30 (#4) - Claude Code — v2.4 Beta 1 (แปลงทั้งโปรแกรมเป็น CustomTkinter)

branch: `customtkinter-ui` (แตกจาก improve-7-features). **แผนสำรอง:** Beta 3 ยังอยู่ครบที่
branch `improve-7-features` + Release v2.3_Beta_3-105 — ถ้า CTk มีปัญหา ใช้ของเดิมได้

- **เปลี่ยน GUI toolkit:** tkinter ดิบ → **customtkinter 5.2.2** (ปุ่มมุมโค้ง/ธีมดำเนียน/เรนเดอร์สีเท่ากัน Mac+Win)
- **คงตรรกะทั้งหมด:** `pixup_workflow.py`/`config.py`/`chatgpt_retouch.py` ไม่แตะ. flow/ขั้นเดิมครบ
- **`pixup.py` เขียนใหม่:** CTkFrame/CTkButton/CTkEntry/CTkProgressBar/CTkTextbox/CTkSwitch/CTkScrollableFrame.
  root = `make_root()` ใช้ mixin `ctk.CTk + TkinterDnD.DnDWrapper` (DnD ยังใช้ได้; fallback ctk.CTk).
  รายการขั้น = ปุ่ม pill (active=accent), settings/category = CTkToplevel.
  Gotchas ที่จัดการแล้ว: `CTkProgressBar.set()` ใช้สัดส่วน 0..1 (เก็บ `_progress_max`), log ใช้
  `CTkTextbox._textbox.tag_config` คงสี, iconbitmap ตั้งหลัง after(280) ให้ชนะ CTk, DnD register บน `_entry`
- **`dialogs.py` เขียนใหม่:** 7 ไดอะล็อกเป็น ctk. **merge/crop คง tk.Canvas + ตรรกะ build/drag/zoom เดิม**
  เปลี่ยนแค่ปุ่ม/แถบ→CTkSlider. รูปย่อใช้ CTkImage. radio/checkbox→CTkRadioButton/CTkCheckBox
- **Build:** requirements เพิ่ม `customtkinter`; build.yml เพิ่ม `--collect-all customtkinter --collect-all darkdetect`
  (CTk มี asset ที่ PyInstaller ลืม → ไม่ใส่ = .exe เด้งปิด) **ต้องเทส build จริงว่าเปิดได้**

QA: py_compile pixup/dialogs ผ่าน, smoke สร้าง CTk root+app+7 ขั้น+log สี+progress ผ่าน,
render 7 ไดอะล็อก (auto-close) ผ่านหมด, **screenshot บน mac เห็นจริง** (หน้าหลัก + import dialog สวย โค้งมน teal).
**ต้องทำต่อ:** เทส build .exe จาก branch ว่าเปิดได้ไม่เด้งปิด → ส่งผู้ใช้เทส Windows (DnD, canvas, AI)

### 2026-05-30 (#3) - Claude Code — v2.3 Beta 3 (รื้อ UI ให้คลีน + โลโก้)

branch: `improve-7-features` (ต่อจาก Beta 2 — ยังไม่ merge main)

- **โลโก้/ไอคอน:** logo.png (เพชรเทอร์คอยซ์) + app_icon.ico, ใส่ใน .exe (`--icon`) + หน้าต่าง/taskbar
  (`resource_path` + `_set_window_icon`). bundle logo.png เข้า .exe ผ่าน `--add-data`
- **ธีมเดียว midnight + accent teal:** ปรับพาเลตต์ `theme.py` midnight ให้คลีน, ตั้งคงที่ใน `pixup.py`
  เอา dropdown สลับธีม + ปุ่มเลือกสี (color picker) ออก, ลบ `change_theme/pick_accent/_rebuild_ui` + import colorchooser
  รวมสีทุกขั้นเป็น accent เดียว (เลิกใช้ purple/orange/highlight ต่อขั้น)
- **Header:** เอา "KH CREATION" ออก, ใส่โลโก้รูป + "PixUp" + เวอร์ชัน, เหลือปุ่ม ⚙ อย่างเดียว, เส้นคั่นบาง
- **ลดขนาด + log ใหญ่ขึ้น:** 1320x900→1140x800, minsize 980x680, คอลัมน์ซ้าย230→196 ขวา300→250,
  log height 8→13 (fill both expand)
- **ตัวเลือกฝั่งขวาต่อขั้น (`_render_panel`):** ออกแบบใหม่ต่อขั้น — import: กล้อง/Workspace/จัดกลุ่มตามรหัส/ล้างความจำ ·
  collect: **Photo 1 + Photo 2** + Workspace · ai: Workspace + ตั้งค่า ChatGPT · archive: คลัง + Workspace
- **ย้าย "จัดกลุ่มตามรหัส"** จาก Settings → ขั้น 1 ฝั่งขวา (เอาออกจาก Settings tools)
- **คลีนอัป UI:** รายการขั้นมีแถบ accent ซ้ายตอน active, การ์ดกลางกระชับ (badge ขั้น+sub), ปุ่ม nav/panel hover เนียน

QA: py_compile pixup/theme ผ่าน, smoke สร้าง UI+วน 7 ขั้น+open_settings+category manager ผ่าน, grep ไม่เหลือ
dangling (change_theme/pick_accent/theme_var/_rebuild_ui/KH CREATION/colorchooser). **ถ่าย screenshot จริงบน mac
ตรวจเลย์เอาต์ผ่าน** (header/steps/panel/log วางถูก) — หมายเหตุ: ปุ่ม tk.Button ไม่รับสี bg บน macOS (โชว์เทา)
แต่บน Windows จะเป็น teal ปกติ. **ผู้ใช้เทสจริงบน Windows:** สีปุ่ม/ความสวย/สัดส่วน

### 2026-05-30 - Claude Code — v2.3 Beta 2 (ปรับปรุงตามฟีดแบ็กผู้ใช้ 7 เรื่อง)

branch: `improve-7-features` (ยังไม่ merge/push — รอผู้ใช้เทส GUI)

**บริบท workflow จริง (ยืนยันกับผู้ใช้):** ชื่อไฟล์กล้อง `UN-8009_<uuid>.original.jpg` — "UN" เป็นแค่ชื่อไฟล์
ไม่ใช่รหัสสินค้า. นำเข้าจัดกลุ่มตาม **เลข 4 หลัก (8009)** เท่านั้น. รหัสสินค้าจริง (เช่น `R-54321-00-S00`)
ผู้ใช้ **ตั้งชื่อโฟลเดอร์เอง** ก่อนขั้นเปลี่ยนชื่อ → ระบบอ่านประเภทจากตัวอักษรนำหน้า (R=แหวน) ตอนเก็บเข้าฐาน

**สิ่งที่แก้:**
- **(ข้อ0/รากฐาน)** `pixup_workflow.py`: `import_number`/`folder_code` (จัดกลุ่มนำเข้าตามเลข 4 หลัก),
  `product_type_number` (แยกประเภท+เลขจากรหัสที่ผู้ใช้ตั้งเอง รองรับหลายตัวอักษร),
  `parse_codes_input` (รองรับ `,`/เว้นวรรค/ช่วง `1000-1005`/ปนกัน)
- **(ข้อ1)** เปลี่ยนข้อความ error จาก "ทำขั้นนำเข้าก่อน" เป็นกลาง — ชี้ Workspace ที่มีรูปแล้วกดขั้นไหนก็ทำได้
- **(ข้อ2a)** `resolve_dest` ใช้ `product_type_number` อ่านตัวอักษรนำหน้ารหัสโฟลเดอร์แทน `f_n[0]`
  → รองรับประเภทหลายตัวอักษร. dry-run: `R-54321-00-S00`→Ring หา range เจอ="exists" ✓ · นำเข้า `UN-8009...`→โฟลเดอร์ `8009` ✓
- **(ข้อ2b)** `pixup.py`: ยุบเมนู Tools เข้าไปในหน้า ⚙ Settings (ทำ body เลื่อนได้) + เอาปุ่ม Tools/คำว่า "ฉุกเฉิน" ออก + ลบ `open_tools`
- **(ข้อ3)** `dialogs.collect_preview` รื้อใหม่เป็น **ทีละสินค้า** (‹ ›) โชว์รูปต้นทาง + รูปปลายทางเดิม P1/P2
  + radio แทนที่/ไม่แทนของเดิม(skip_dup)/ข้ามสินค้า. `phase_collect` ส่ง `*_existing` + เคารพ `decisions`
- **(ข้อ4)** `dialogs.calendar_picker` ปฏิทินทำเอง (ไม่เพิ่ม lib) ผูกในโหมดนำเข้าตามวันที่ (ปุ่ม 📅, พิมพ์เองได้)
- **(ข้อ5)** โหมดนำเข้าตามรหัสใช้ `parse_codes_input` + อัปเดตข้อความช่วย
- **(ข้อ6)** `chatgpt_retouch.py`: `_upscale_to_match` → `_finalize_image` — **re-encode ตามนามสกุลจริงเสมอ**
  (JPEG→convert RGB) แก้ไฟล์ .jpg ที่จริงเป็น WebP/PNG เปิดไม่ได้. dry-run: ไฟล์ปลอม PNG/WebP→JPEG จริงผ่าน ✓
- **(ข้อ7)** `pixup.py` `play_done_sound()` ข้ามแพลตฟอร์ม (mac afplay / win MessageBeep / fallback bell)
  เรียกท้ายขั้นที่ใช้เวลานาน (นำเข้า/AI/เก็บเข้าฐาน/คลัง) + สวิตช์ `sound_enabled` ใน Settings/config

QA: py_compile 5 ไฟล์ผ่าน, smoke test สร้าง UI+สลับ 7 ขั้นผ่าน, dry-run parse_code/parse_codes_input/resolve_dest
ด้วยชื่อไฟล์จริงผ่าน, _finalize_image แก้ format ผ่าน, render dialogs ใหม่ (collect/calendar/import) ไม่ error.
grep ไม่พบ dangling ref (open_tools/_upscale_to_match/f_n[0]).
**Risk/ผู้ใช้ต้องเทสบนเครื่อง:** หน้าตา/คลิกจริง, ปฏิทินเลือกวัน, collect ทีละสินค้า, เสียงแจ้งเตือน,
ขั้น AI กับ ChatGPT จริง. นำเข้ายังจัดกลุ่มตามเลข 4 หลัก (โฟลเดอร์ `8009` เหมือนเดิม) — ไม่กระทบ flow เดิม

### 2026-05-29 (PM-4) - Claude Code — v2.3 Beta 1 (รื้อใหญ่: Lightroom UI + แยกโมดูล)

**เปลี่ยนสถาปัตยกรรมเป็น 6 โมดูล:** `pixup.py`(UI/หลัก) · `theme.py` · `config.py` · `dialogs.py` · `workflow.py` · `chatgpt_retouch.py`
(เดิม pixup.py ไฟล์เดียว ~1400 บรรทัด → แยกเพื่อแก้ง่าย/ประหยัด token)

**UI ใหม่ — Lightroom 3 คอลัมน์:** ซ้าย=STEPS+Workspace, กลาง=card ขั้นปัจจุบัน+ปุ่มเริ่ม, ขวา=panel(เปิดโฟลเดอร์/คำแนะนำ), footer=progress+"x/N"+log. Header มี dropdown ธีม (graphite/midnight/slate) + ปุ่มเลือกสี accent (colorchooser) + Tools + ⚙. **กดขั้นในคอลัมน์ซ้าย→โชว์การ์ด, กดปุ่มเริ่ม=ทำงานเลย** (ขั้นที่มี dialog/preview ถือว่า confirm ในตัว; Archive มี confirm เพราะย้ายไฟล์)

**ลำดับ workflow ใหม่:** 1.นำเข้า → 2.รวมรูป → 3.ครอป → 4.AI → 5.เปลี่ยนชื่อ → 6.เก็บเข้าฐาน → 7.คลัง. "จัดกลุ่มตามรหัส" ย้ายไป Tools (ฉุกเฉิน). เหตุผล: รวม/ครอปก่อน AI = ส่งรูปน้อยลง ประหยัดโควต้า

**ฟีเจอร์ใหม่:**
- นำเข้าหลายโหมด (ใหม่/ทั้งหมด/ช่วงวันที่/ตามรหัส — รองรับดึงซ้ำ/แก้ไข) via `dialogs.import_options`
- ธีม + เลือกสี accent (เก็บใน config) — `theme.build_palette`
- ตัวนับ "x/N" ทุกขั้นที่วนหลายชิ้น + สรุปท้ายขั้น (สำเร็จ/ล้มเหลว/ข้าม/เวลา)
- ปุ่มเปิดโฟลเดอร์ (workspace/กล้อง/Photo1/log) + ตรวจพื้นที่ว่างก่อน collect
- Tools menu: จัดกลุ่ม, ล้าง import memory, เปิดโฟลเดอร์, หมวดหมู่
- รองรับวิดีโอ (นำเข้า/เปลี่ยนชื่อ)
- **AI ทนทานขึ้น:** ตรวจล็อกอิน(รอผู้ใช้), ตรวจ upload สำเร็จ+แนบใหม่ถ้าพลาด, retry รายรูป 1 ครั้ง, จับ exception ต่อรูป(ไม่ล้ม batch), หยุดทันทีเมื่อลิมิต, on_progress→UI

**คงของเดิมที่ทำงานแล้ว:** detection จับ alt "ภาพที่สร้างขึ้น" + รอ generation เสร็จ, upscale เท่าต้นฉบับ, merge frame-model, crop cover, preview=ภาพจริงย่อ, collect resolver (exists/nearest/new/no_category) ไม่สร้างโฟลเดอร์มั่ว, ไฮไลต์ _AI

**build.yml:** เปลี่ยน version grep เป็น `^VERSION = "..."` (เดิม self.version)

QA: ดู HANDOFF QA section ด้านล่าง / py_compile+import 6 โมดูลผ่าน, smoke test สร้าง UI+สลับขั้น+เปลี่ยนธีมบน Mac ผ่าน, app.* ที่ workflow ใช้ครบ. **ผู้ใช้ต้องเทส GUI คลิกจริง + ขั้น AI กับ ChatGPT**

### 2026-05-29 (PM-3) - Claude Code — v2.2 Beta 9 (upscale + ไฮไลต์ _AI)

ยืนยันจาก log 12:00: 1.5 จับรูปถูกทั้ง 2 ใบ (1254x1254 = รูป AI จริง). ตรวจไฟล์: ต้นฉบับ 2000/2160px, AI 1254px
- **Upscale รูป AI:** `_upscale_to_match(out_path, original_path)` ใน chatgpt_retouch — หลังดาวน์โหลด ขยายรูป AI ด้วย Lanczos ให้ด้านยาวเท่าต้นฉบับ (1254→2000/2160) เฉพาะเมื่อเล็กกว่า. ทดสอบผ่าน
- **ไฮไลต์ _AI ในขั้นตอน 2:** `choose_main_file_visual` เรียงไฟล์ `*_AI` ขึ้นก่อน + กรอบเขียว + ป้าย "✨ AI" + ชื่อสีเน้น เพื่อให้เลือกรูปที่รีทัชแล้วง่าย ไม่เผลอเลือกต้นฉบับ

Validation: py_compile + import + ทดสอบ upscale ผ่าน

### 2026-05-29 (PM-2) - Claude Code — v2.2 Beta 8 (1.5 รอ generation + Phase 3 preview/no-autocreate)

Changed files: `pixup.py`, `chatgpt_retouch.py`

จาก log จริง: รูปที่ 2 (1212.jpg) จับได้ 2000x2000 ใน 6 วิ = **รูปอัปโหลด** เพราะ AI ยังสร้างไม่เสร็จ + มีสำเนา upload ที่ alt='' เลยไม่ถูกกรอง
1. **1.5 รอ generation จริง:** `_wait_for_result` เขียนใหม่ — ระหว่างปุ่ม Stop โชว์ (`_is_generating`) จะ **ไม่รับรูปใด ๆ** (รีเซ็ตตัวนับ). จับรูปที่ alt = marker ("ภาพที่สร้างขึ้น"/"generated image") เป็นหลัก. fallback (รูปใหม่ใหญ่สุดที่ไม่ใช่ไฟล์อัปโหลด) ใช้เฉพาะหลังเห็น generation จบแล้ว ~8 วิ ยังไม่เจอ marker. `_FIND_NEW_IMAGE_JS` คืน `{gen, fb}`, กรอง alt ที่ลงท้าย .jpg/.png (=ชื่อไฟล์อัปโหลด). ทดสอบ DOM จำลอง (กำลังสร้าง→ไม่จับ, เสร็จ→จับ 1254 marker) ผ่าน
2. **Phase 3 preview + ไม่สร้างโฟลเดอร์ใหม่อัตโนมัติ:** เพิ่ม `_resolve_dest` (exists/nearest/new/no_category) + `_nearest_range_dir` (เดาช่วงใกล้เคียง) + dialog `open_phase3_preview` (thumbnail รูปหลัก + ปลายทาง P1/P2 + สถานะ + checkbox "อนุญาตสร้างโฟลเดอร์ใหม่" default OFF). ไม่พบหมวด=ข้าม+แจ้ง, ช่วงไม่ตรง=ใช้ใกล้เคียง, ใหม่=สร้างต่อเมื่อติ๊ก. ทดสอบ resolver: ไม่สร้างโฟลเดอร์ใหม่ระหว่าง resolve ผ่าน

Validation: py_compile + import + ทดสอบ logic (detection JS, phase3 resolver) ผ่านบนเครื่อง Mac จริง

### 2026-05-29 (PM) - Claude Code — v2.2 Beta 7 (แก้ 1.5 จาก debug จริง + crop/merge preview)

Changed files: `pixup.py`, `chatgpt_retouch.py` + เพิ่มโหมด `--inspect`

**ใช้โหมด `--inspect` เก็บ DOM จริงของ ChatGPT (debug_report.txt) แล้วเจอ root cause:**
- รูปผลลัพธ์ alt = "ภาพที่สร้างขึ้น: ..." ขนาด 1254x1254; **รูปที่อัปโหลด alt = ชื่อไฟล์ "1212.jpg" ขนาด 2000x2000** → ระบบเก่าเลือก "ใหญ่สุด" จึงจับรูปอัปโหลดผิด
- `data-message-author-role="assistant"` **ใช้ไม่ได้แล้ว** (inAssistant=False ทุกรูป, "no assistant turn")

**แก้:**
- `_FIND_NEW_IMAGE_JS` ใหม่: Pass 1 จับจาก alt marker ("ภาพที่สร้างขึ้น"/"generated image") = แม่นสุด; Pass 2 สำรอง = รูปใหม่ใหญ่สุดที่ไม่ใช่ไฟล์อัปโหลด (ข้าม alt==ชื่อไฟล์) ส่ง `{known, uploaded}` เข้า JS
- `_LIMIT_TEXT_JS` เปลี่ยนไปอ่าน `<main>` + dialog/alert (ไม่พึ่ง assistant role ที่พังแล้ว, เลี่ยง sidebar "Upgrade")
- ทดสอบ JS กับ DOM จำลองตาม debug จริง: เลือกรูปผลลัพธ์ถูก + ไม่ false-positive limit
- โหมด inspect: `python3 chatgpt_retouch.py --inspect` → ทำรีทัชเอง 1 รูป กด Enter → ได้ debug_report.txt + debug_fullpage.png
- crop/merge: refresh วาดที่ COMP แล้วย่อมาโชว์ → **preview ตรงกับไฟล์ที่ save 100%**
- ติดตั้งจริงบนเครื่อง Mac: `playwright` 1.60.0 + chromium แล้ว (รัน --inspect ต้องใช้ Terminal จริง ไม่ใช่ `!` ใน Claude Code เพราะต้องกด Enter)

Validation: py_compile + import ผ่าน, ทดสอบ detection JS กับ DOM จำลองผ่าน. **ยังควรรัน 1.5 จริงผ่านปุ่มในแอปอีกครั้งเพื่อยืนยัน end-to-end download**

### 2026-05-29 - Claude Code — v2.2 Beta 5 (1.5 detection ใหม่ + limit + merge sliders)

Changed files: `pixup.py`, `chatgpt_retouch.py`

1. **1.5 "ไม่มีรูปกลับมา" (เขียน detection ใหม่):** เดิมเดา selector ของ assistant DOM → เปลี่ยนเป็น **baseline + รูปใหม่**: เก็บ src รูปทั้งหมดก่อนกดส่ง (`_SNAPSHOT_JS`), หลังส่งหา "รูปใหม่ที่ไม่อยู่ใน baseline + ด้านสั้น ≥200px" (`_FIND_NEW_IMAGE_JS`) รอจน stream จบ (ปุ่ม Stop หาย) + นิ่ง 2 รอบ. ดาวน์โหลด: fetch→fallback `screenshot(clip=rect)`. ถ้าหาไม่เจอ เซฟ `_debug_<ชื่อ>.png` (full page) + log จำนวนรูป/ขนาดใหญ่สุด เพื่อ debug
2. **ตรวจจับลิมิตแล้วหยุด:** `_check_limit` อ่านเฉพาะ **คำตอบล่าสุดของ assistant + dialog/alert** (ไม่อ่าน sidebar กัน false-positive จากคำ "Upgrade"), วลีลิมิตที่ไม่กำกวม. `_retouch_one` คืน `(ok, err, is_limit)`; loop หยุดทันทีเมื่อ `is_limit` + แจ้ง "⛔ ติดลิมิต หยุดทั้งหมด"
3. **1.6 merge:** ยืนยัน frame model (Canva-style 2 กรอบ, ครอปในกรอบ ไม่ล้นกลาง) + เพิ่ม **แถบ ZOOM แยกซ้าย/ขวา + ปุ่มสลับ + รีเซ็ต** (เดิมมีแต่ wheel) — ล้อเมาส์เลือกฝั่งอัตโนมัติตามตำแหน่งเคอร์เซอร์. หมายเหตุ: อาการที่ผู้ใช้รายงาน (รูปล้นกลาง/ขยับไม่ได้) เป็นพฤติกรรม Beta 3 — แปลว่าเทสเวอร์ชันเก่า ต้องรันไฟล์ล่าสุด

หมายเหตุ TCC: ระหว่าง session ที่แล้ว macOS ถอนสิทธิ์อ่านไฟล์ใน Documents กลางคัน แก้ด้วยปิด-เปิด terminal ใหม่

Validation: `py_compile` + import ผ่าน. **1.5 ยังต้องทดสอบกับ ChatGPT จริง** — ถ้ายังไม่ได้รูป ให้ดูไฟล์ `_debug_*.png` + บรรทัด DEBUG ใน log

### 2026-05-28 (PM-3) - Claude Code — v2.2 Beta 4 (วิดีโอ + frame merge + crop จริง + 1.5 download)

Changed files: `pixup.py`, `chatgpt_retouch.py`

แก้ 6 ปัญหา:
1. **1.5 ไม่ได้รูปกลับ ("ไม่มีรูปกลับมา"):** เขียน detection ใหม่ (`_wait_for_result` + `_FIND_RESULT_JS`) หา "รูปใหญ่สุดในคำตอบล่าสุดของ assistant" (min side ≥200px) รอจน stream จบ (ปุ่ม Stop หาย) + นิ่ง 2 รอบ. ดาวน์โหลด: fetch ผ่าน context → fallback `page.screenshot(clip=rect)` (กัน CORS/blob)
2. **1.6 preview≠ผลลัพธ์ + อยากได้กรอบแบบ Canva:** เปลี่ยนเป็น **frame model** 2 กรอบครึ่งจอ — รูปถูกครอปให้อยู่ในกรอบของตัวเอง (paste ลง tile ขนาดกรอบ ส่วนเกินถูกตัด) ลาก/ซูมภายในกรอบ, preview ใช้สูตรเดียวกับ save (s=PV vs s=COMP) จึงตรงกัน, เส้นแบ่ง+กรอบวาดบน canvas เท่านั้น (ไฟล์ที่ save ไม่มีเส้น)
3. **Phase 2 preview ไม่โชว์ชื่อไฟล์:** เพิ่ม label ชื่อไฟล์ใต้ thumbnail + ทำ gallery ให้ scroll ได้
4. **Phase 2 ไม่เปลี่ยนชื่อวิดีโอ:** รวมไฟล์วิดีโอเข้ากระบวนการ (รูปหลักต้องเป็นรูปภาพ, วิดีโอ+รูปอื่น → `-2,-3`)
5. **Phase 0 ไม่ดึงวิดีโอ:** เปลี่ยน filter เป็น `is_media_file` (เพิ่ม `VIDEO_EXTENSIONS`, `is_video_file`, `is_media_file`)
6. **Phase 3 ก๊อปทุกไฟล์:** เปลี่ยนเป็นเอาเฉพาะรูปหลัก (ชื่อไฟล์ตรงรหัสโฟลเดอร์พอดี เช่น `1212.jpg` ไม่เอา `1212-2.jpg`)

Validation: `py_compile` ผ่าน, import ผ่าน, dry-run rename/phase3 logic ผ่าน (วิดีโอถูก rename, phase3 เลือก primary รูปเดียว). **ยังต้องทดสอบ GUI จริงบน Windows โดยเฉพาะ 1.5 download กับ ChatGPT จริง**

### 2026-05-28 (PM-2) - Claude Code — v2.2 Beta 2 (แก้ selector/merge/crop/browser)

Changed files: `pixup.py`, `chatgpt_retouch.py`

Summary:
- **Selector (1.5/1.6/1.7) กดยืนยันไม่ได้ → แก้:** ปุ่มยืนยัน/ยกเลิกถูก pack ลำดับผิดจนถูกบัง ย้ายแถบปุ่มไป `side="bottom"` pack ก่อนพื้นที่ scroll + เพิ่มตัวนับ "เลือกแล้ว N รูป" + ไฮไลต์รูปที่เลือกด้วยกรอบ (ไม่ทับรูป)
- **Merge UI (1.6) ปุ่มหาย + ขยับไม่ได้ → แก้:** เดิม canvas 800px สูงเกินหน้าต่างทำให้ปุ่ม Save หลุดจอ → ลด canvas เป็น 640, pin แถบปุ่มล่างสุด, เพิ่ม **ลากย้าย (drag) + ซูมด้วยล้อเมาส์ (wheel)** ต่อรูป, เลือกปรับรูปซ้าย/ขวา, สลับซ้าย-ขวา, render เต็มความละเอียด 2000px ตอน save
- **Crop UI (1.7) เหมือนกัน → แก้:** ลด canvas 640 + pin ปุ่ม + **ลากย้าย + ซูม (ล้อเมาส์/สไลเดอร์)** + รีเซ็ต
- **1.5 Cancel button:** ปุ่ม AI กลายเป็น "■ ยกเลิก" สีแดงระหว่างทำงาน (ยกเลิกหลังรูปปัจจุบันผ่าน threading.Event)
- **1.5 Browser:** เปลี่ยน acquire strategy — (1) ต่อ Chrome ที่เปิด `--remote-debugging-port=9222` อยู่ผ่าน CDP (2) เปิด Chrome ของเครื่องเองด้วย debug port + โปรไฟล์ PixUp (ล็อกอินครั้งเดียว จำตลอด) (3) fallback persistent context. หมายเหตุ: Chrome รุ่นใหม่ห้ามเปิด debug port บนโปรไฟล์หลัก จึงใช้โปรไฟล์แยกของ PixUp — ผู้ใช้ล็อกอินครั้งเดียว
- bump → **v2.2 Beta 2**

Validation: `py_compile` ทั้งคู่ผ่าน, import chatgpt_retouch ผ่าน (ไม่มี playwright ก็ได้), ไม่เหลือ dangling ref. **ยังต้องทดสอบ GUI จริงบน Windows**

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
