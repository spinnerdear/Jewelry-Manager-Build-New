# PixUp v2.3 — เครื่องมือเตรียมรูปสินค้าเครื่องประดับ (KH Creation)

โปรแกรมจัดการ/รีทัช/จัดเก็บรูปสินค้าเครื่องประดับ แบบ workflow เป็นขั้นตอน
UI สไตล์ Lightroom (3 คอลัมน์) เลือกธีม/สีได้ • รีทัชด้วย ChatGPT ผ่านเบราว์เซอร์

## โครงสร้างไฟล์
| ไฟล์ | หน้าที่ |
|---|---|
| `pixup.py` | ตัวหลัก + UI (โครง 3 คอลัมน์, นำทางขั้น, logging, ธีม) |
| `theme.py` | ธีมสี + accent + `build_palette()` |
| `config.py` | โหลด/บันทึก settings + manifest (ความจำการนำเข้า) |
| `dialogs.py` | หน้าต่างย่อย: เลือกรูป, รวมรูป, ครอบตัด, เลือกรูปหลัก, พรีวิว, ตัวเลือกนำเข้า |
| `workflow.py` | ตรรกะแต่ละขั้นตอน (import/merge/crop/ai/rename/collect/archive) |
| `chatgpt_retouch.py` | ขั้น AI ผ่าน Playwright (+ โหมด `--inspect` สำหรับ debug) |

## Workflow (ลำดับขั้น)
1. **นำเข้ารูปใหม่** — ดึงจากโฟลเดอร์กล้องอัตโนมัติ (โหมด: ใหม่/ทั้งหมด/ช่วงวันที่/ตามรหัส) คัดลอกแยกตามรหัส 4 หลัก ไม่ลบต้นฉบับ
2. **รวมรูปต่างหู** — รวม 2 รูป (หน้า/ข้าง) เป็นรูปเดียวก่อนส่ง AI (ประหยัดโควต้า)
3. **ครอบตัด** — ครอบ/จัดตำแหน่งก่อนส่ง AI
4. **รีทัชด้วย AI** — ส่ง ChatGPT รีทัช → ไฟล์ `_AI` (ขยายเท่าต้นฉบับ)
5. **เปลี่ยนชื่อ + เลือกรูปหลัก** — ตั้งชื่อตามรหัสโฟลเดอร์ (รวมวิดีโอ)
6. **เก็บเข้าฐานข้อมูล** — คัดลอกรูปหลักไป Photo 1/Photo 2 (พรีวิวก่อน, ไม่สร้างโฟลเดอร์มั่ว)
7. **ย้ายเข้าคลัง** — ย้ายเข้าคลังตามวันที่

**Tools (🛠):** จัดกลุ่มตามรหัส (ฉุกเฉิน), ล้างความจำการนำเข้า, เปิดโฟลเดอร์, จัดการหมวดหมู่

## ติดตั้ง
```bash
pip install -r requirements.txt
python -m playwright install chromium   # สำหรับขั้น AI
```

## รัน
```bash
python pixup.py
```
ตั้งค่า (ปุ่ม ⚙): โฟลเดอร์กล้อง, Photo 1/2, Archive, (ถ้าใช้) Custom GPT URL

## ขั้น AI (ChatGPT)
- ครั้งแรกล็อกอิน ChatGPT ในเบราว์เซอร์ที่เปิดขึ้น — ครั้งต่อไปจำ session ให้ (โปรไฟล์ `~/.pixup/chrome_profile`)
- ถ้าจะใช้โปรไฟล์ Chrome หลัก: ใส่ path ในช่อง Chrome Profile (ต้องปิด Chrome ให้หมดก่อน)
- Debug เมื่อหารูปไม่เจอ: `python chatgpt_retouch.py --inspect` (รันใน Terminal จริง) → ได้ `debug_report.txt`

## Build (.exe สำหรับ Windows)
ผ่าน GitHub Actions (`.github/workflows/build.yml`) — push ขึ้น branch `main`
เครื่องปลายทางต้องมี Playwright + Chromium สำหรับขั้น AI

## ข้อมูลที่เก็บ (`~/.pixup/`)
- `config_v2_1.json` — การตั้งค่า + ธีม
- `imported_manifest.json` — ความจำว่าดึงไฟล์ไหนไปแล้ว
- `history_log.txt` — log ย้อนหลัง
