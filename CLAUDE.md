# CLAUDE.md — คู่มือโปรเจกต์ PixUp (สำหรับ Claude Code)

> ไฟล์นี้คือคำสั่ง/บริบทหลักของโปรเจกต์ อ่านก่อนเริ่มงานทุกครั้ง พร้อมกับ `HANDOFF.md`

## ภาพรวม
PixUp = เครื่องมือเตรียมรูปสินค้าเครื่องประดับของ **KH Creation** — จัดการ → รวม/ครอป → รีทัชด้วย AI → ตั้งชื่อ → เก็บเข้าฐานข้อมูล → คลัง
GUI: Tkinter สไตล์ Lightroom (3 คอลัมน์), รีทัชด้วย **ChatGPT ผ่าน Playwright** (ไม่ใช้ Gemini API แล้ว)

## เจ้าของโปรเจกต์
- ทำธุรกิจเครื่องประดับ **ไม่ใช่โปรแกรมเมอร์** — อธิบายให้เข้าใจง่าย, ตัดสินใจเชิงเทคนิคแทนได้เลย
- สื่อสาร**ภาษาไทย**
- จะทำงานผ่าน Claude Code ในโปรเจกต์นี้ต่อเนื่อง

## สถาปัตยกรรม (แยก 6 โมดูล — แก้ตรงไฟล์ที่เกี่ยว ไม่ต้องเปิดทั้งหมด)
| ไฟล์ | หน้าที่ | แก้เมื่อ |
|---|---|---|
| `pixup.py` | `PixUpApp`: UI 3 คอลัมน์, นำทางขั้น, logging, ธีม, settings/Tools | แก้หน้าตา/การนำทาง/header |
| `theme.py` | `THEMES`, `ACCENT_PRESETS`, `build_palette(theme,accent)` | แก้สี/ธีม |
| `config.py` | load/save settings + manifest (`~/.pixup/`) | แก้การบันทึกค่า |
| `dialogs.py` | image_selector, merge_editor, crop_editor, primary_chooser, collect_preview, import_options | แก้หน้าต่างย่อย |
| `workflow.py` | `phase_import/group/merge/crop/ai/rename/collect/archive(app)` | แก้ตรรกะขั้นตอน |
| `chatgpt_retouch.py` | ขั้น AI (Playwright) + โหมด `--inspect` | แก้การคุยกับ ChatGPT |

**Interface:** `workflow`/`dialogs` รับ `app`/`(root, colors)` — ไม่ import `pixup` (กัน circular). `pixup` import ทุกตัว
**เวอร์ชัน:** แก้ที่ `VERSION = "..."` บนหัว `pixup.py` ที่เดียว (build.yml grep บรรทัดนี้)

## Workflow (ลำดับขั้น)
1 นำเข้า(รวมจัดกลุ่ม) → 2 รวมรูปต่างหู → 3 ครอป → 4 AI → 5 เปลี่ยนชื่อ+เลือกหลัก → 6 เก็บเข้าฐาน → 7 คลัง
"จัดกลุ่มตามรหัส" อยู่เมนู **Tools** (ฉุกเฉิน). รวม/ครอปทำ**ก่อน** AI เพื่อส่งรูปน้อย ประหยัดโควต้า

## รายละเอียดที่ต้องรู้
- **ขั้น AI:** ChatGPT คืนรูป ~1254px → ระบบ upscale เท่าต้นฉบับ. จับรูปผลจาก `alt="ภาพที่สร้างขึ้น"/"generated image"` (อย่าใช้ "รูปใหญ่สุด" จะไปโดนรูปอัปโหลด). ต้องรอ generation เสร็จ (ปุ่ม Stop หาย) ก่อนจับ
- **Login ChatGPT:** ใช้ persistent profile `~/.pixup/chrome_profile` (ล็อกอินครั้งเดียว). Chrome รุ่นใหม่ห้าม automate โปรไฟล์หลัก — ถ้าจะใช้ต้องปิด Chrome หมดก่อน
- **Debug AI:** `python chatgpt_retouch.py --inspect` ใน Terminal จริง → ทำรีทัช 1 รูปเอง กด Enter → ได้ `debug_report.txt` (Claude อ่านได้)
- **เก็บเข้าฐาน (ขั้น 6):** เอาเฉพาะรูปหลัก (ชื่อตรงรหัสโฟลเดอร์), resolver ไม่สร้างโฟลเดอร์มั่ว (exists/nearest/new/no_category)
- **รองรับวิดีโอ** ในขั้นนำเข้า + เปลี่ยนชื่อ

## ข้อจำกัดสภาพแวดล้อมพัฒนา (สำคัญ)
- พัฒนาบน **macOS** ผ่าน Claude Code — **รัน Tkinter GUI แบบเห็นภาพจริงไม่ได้** ผ่าน tool ปกติ
- ทดสอบที่ Claude ทำได้: `py_compile`, `import`, **smoke test** (`tk.Tk(); root.withdraw(); PixUpApp(root)` + สลับขั้น/ธีม), dry-run logic (ฟังก์ชันที่ไม่ใช่ GUI), ทดสอบ JS ของ ChatGPT ผ่าน Playwright chromium กับ DOM จำลอง
- หน้าตา/คลิกจริง + ขั้น AI กับ ChatGPT จริง = **ผู้ใช้เทสบนเครื่อง**
- ติดตั้งแล้วบนเครื่อง: `playwright`+chromium, `tkinterdnd2`, `Pillow`
- ถ้าโฟลเดอร์ใน `Documents/` อ่านไม่ได้ (EPERM) = macOS TCC — ให้ผู้ใช้ปิด-เปิด Terminal ใหม่

## วิธีทำงาน (รูปแบบที่ใช้ได้ผล)
- งานใหญ่/รื้อโครงสร้าง → เข้า **plan mode** ถามจุด subjective (UI/สี/ลำดับ) ก่อน แล้วค่อยลงมือ
- แก้เสร็จทุกครั้ง: `py_compile` + import + dry-run logic ที่เกี่ยว + grep หา dangling refs
- bug ของ ChatGPT: ใช้ `--inspect` ดู DOM จริงก่อนแก้ อย่าเดา
- bump `VERSION`, อัปเดต `HANDOFF.md` (ลงวันที่ + แก้อะไร/ทดสอบอะไร/เหลือ risk อะไร)
- **git:** อยู่บน `main` (default). commit/push เมื่อผู้ใช้สั่งเท่านั้น. push `main` → GitHub Actions build .exe อัตโนมัติ (ระวัง build เวอร์ชันที่ยังไม่เทส) → ทำงานบน branch แล้วค่อย merge
- ลงท้าย commit ด้วย `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

## ความปลอดภัย/ข้อห้าม
- ห้ามฝัง API key/token/รหัสผ่านใน source
- ขั้นที่ย้าย/ลบ/เขียนทับไฟล์ ต้องมี recovery + log ที่มองเห็น (เช่น rename ใช้ `_rename_temp`, import suffix `_dup`)
