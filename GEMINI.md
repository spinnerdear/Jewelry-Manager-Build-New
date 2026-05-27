# PixUp - Project Instructions

โปรเจคนี้เป็นเครื่องมือเตรียมรูปสินค้า (Retouching & Organizing) สำหรับ Kh Creation โดยใช้เทคโนโลยี Cloud AI และระบบจัดการไฟล์อัตโนมัติ

## 🏗 Architectural Overview
- **Version:** v2.1 Beta 1 (Cloud AI Edition)
- **Primary AI Agent:** Gemini image editing API (`gemini-2.5-flash-image`)
- **GUI:** Tkinter (Custom Dark Theme)
- **Libraries:** `google-genai`, `pillow`, `tkinterdnd2`
- **Deployment Strategy:** Unified Release (Single Commit) via GitHub Actions

## 🎯 AI Retouching Standards (Critical Checklist)
ทุกการประมวลผลผ่าน AI Agent ต้องเป็นไปตามกฎเหล็กของ Kh Creation ดังนี้:
1.  **Shank Reconstruction (Ring):** ก้านแหวนส่วนที่เบลอจากการถ่ายมาโคร ต้องวาดใหม่ให้คมชัด 100%
2.  **Object Removal (Earring):** ต้องลบขาตั้ง หรืออุปกรณ์ช่วยห้อยต่างหูออกให้หมด และเจนส่วนก้านหู (Post/Hook) ขึ้นมาเติมให้สมบูรณ์
3.  **Automatic Montage (Earring):** เมื่อตรวจพบรูปหน้า-ข้าง ของรหัสต่างหู (E) ต้องรวมเป็นรูปเดียวอัตโนมัติ (หน้า:ซ้าย, ข้าง:ขวา) บนพื้นหลังขาว
4.  **Color Integrity:** ห้ามปรับค่า Saturation เกิน 8-10% เพื่อป้องกันสีพลอยเพี้ยนจากตัวจริง
5.  **Defect Cleaning:** สแกนและลบรอยนิ้วมือหรือฝุ่นจิ๋วบนชิ้นงาน (ถ้ามี)
6.  **Design Preservation QA:** ตรวจสอบโครงสร้างหลัก (จำนวนเพชร, ทรงพลอย) ห้ามผิดเพี้ยนไปจากรูปต้นฉบับ

## ⚙️ Operational Logic
- **Cloud Processing (1.5):** ส่งรูปขึ้น Cloud AI เพื่อรีทัชตามเช็คลิสต์ **(Mandatory: ระบบจะหยุดทำงานทันทีหาก Cloud AI ไม่พร้อมใช้งานหรือโควต้าเต็ม เพื่อรักษาคุณภาพงาน)**
- **Visual Selection (2.0):** แสดงหน้าจอแกลเลอรี่แบบ Compact (160x160 px, 5 คอลัมน์) เพื่อเลือกรูปหลัก
- **Sync & Backup (3.0):** ก๊อปปี้ไฟล์ไปยัง Photo 1 (Main) และ Photo 2 (Backup) พร้อมกัน โดยตรวจสอบสถานะไดรฟ์ (E005) ก่อนเริ่ม
- **Centralized Error Codes:** ใช้รหัสรหัส E001-E007 พร้อมคำอธิบายภาษาไทยใน Log และแจ้งเตือนด้วย Message Box เมื่อเกิด Critical AI Error

## ⚡ Engineering & Windows Standards
- **Lazy Loading:** โหลดไลบรารี AI เฉพาะเมื่อมีการเรียกใช้งานครั้งแรก เพื่อลดเวลาการเปิดโปรแกรม
- **Non-blocking UI:** กระบวนการหนัก (AI, Copying) ต้องรันบน `threading.Thread` เพื่อป้องกันหน้าจอ GUI ค้าง
- **File System:** ใช้ `os.path.normpath` และจัดการปัญหา "File already exists" บน Windows โดยการลบไฟล์เดิมก่อน Rename
- **Secrets:** ห้ามฝัง API key/token ใน source code หรือ README ให้ใช้ environment variable `GOOGLE_API_KEY` หรือกรอกผ่าน UI เท่านั้น
- **Handoff:** ก่อนเริ่มงานให้อ่าน `HANDOFF.md` และเมื่อทำเสร็จให้เพิ่มบันทึกว่าแก้อะไร ทดสอบอะไร และยังเหลือ risk อะไร

---
*อัปเดตล่าสุด: 2026-05-26 - v2.0 Beta 19 QA/QC handoff rules*
