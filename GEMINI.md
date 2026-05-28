# PixUp - Project Instructions

โปรเจคนี้เป็นเครื่องมือเตรียมรูปสินค้า (Retouching & Organizing) สำหรับ Kh Creation โดยใช้เทคโนโลยี Cloud AI และระบบจัดการไฟล์อัตโนมัติ

## 🏗 Architectural Overview
- **Version:** v2.2 Beta 1 (Wizard UI + ChatGPT Edition)
- **Primary AI Agent:** ChatGPT Custom GPT ผ่าน browser automation (Playwright) — ไฟล์ `chatgpt_retouch.py`
  - **เลิกใช้ Gemini API แล้ว** เนื่องจาก free tier ของ `gemini-2.5-flash-image` มีโควต้า = 0 (ต้องเปิด billing)
- **GUI:** Tkinter — Wizard/Stepper (แถบขั้นตอน 0→1→1.5→1.6→1.7→2→3→4 + พื้นที่ทำงานทีละขั้น + log)
- **Libraries:** `pillow`, `tkinterdnd2`, `playwright`
- **Deployment Strategy:** Unified Release (Single Commit) via GitHub Actions
  - ⚠️ exe ที่ build ต้องมี `chatgpt_retouch.py` ติดไปด้วย และเครื่องปลายทางต้องมี Playwright + Chromium (`playwright install chromium`)

## 🎯 AI Retouching Standards (Critical Checklist)
ทุกการประมวลผลผ่าน AI Agent ต้องเป็นไปตามกฎเหล็กของ Kh Creation ดังนี้:
1.  **Shank Reconstruction (Ring):** ก้านแหวนส่วนที่เบลอจากการถ่ายมาโคร ต้องวาดใหม่ให้คมชัด 100%
2.  **Object Removal (Earring):** ต้องลบขาตั้ง หรืออุปกรณ์ช่วยห้อยต่างหูออกให้หมด และเจนส่วนก้านหู (Post/Hook) ขึ้นมาเติมให้สมบูรณ์
3.  **Automatic Montage (Earring):** เมื่อตรวจพบรูปหน้า-ข้าง ของรหัสต่างหู (E) ต้องรวมเป็นรูปเดียวอัตโนมัติ (หน้า:ซ้าย, ข้าง:ขวา) บนพื้นหลังขาว
4.  **Color Integrity:** ห้ามปรับค่า Saturation เกิน 8-10% เพื่อป้องกันสีพลอยเพี้ยนจากตัวจริง
5.  **Defect Cleaning:** สแกนและลบรอยนิ้วมือหรือฝุ่นจิ๋วบนชิ้นงาน (ถ้ามี)
6.  **Design Preservation QA:** ตรวจสอบโครงสร้างหลัก (จำนวนเพชร, ทรงพลอย) ห้ามผิดเพี้ยนไปจากรูปต้นฉบับ

## ⚙️ Operational Logic (Workflow)
- **0. Import New (BETA):** ดึงรูปใหม่จาก Camera Source (เช่น `D:/gemlight box`) อัตโนมัติ
    - **Import Memory:** จำไฟล์ที่เคยดึงด้วย signature `filename|size|mtime` เก็บใน `~/.pixup/imported_manifest.json` → ไม่ดึงไฟล์เก่าซ้ำ
    - **Copy ไม่ Move:** คัดลอกเฉพาะไฟล์ใหม่เข้ากลุ่มตามรหัส 4 หลัก โดยต้นฉบับยังอยู่ที่เดิม
    - มีปุ่ม Reset Import Memory ในหน้า Settings
- **1. Group by Code:** จัดกลุ่มไฟล์ใน Workspace ตามรหัส 4 หลัก (สำหรับเคสดาวน์โหลดเอง)
- **1.5 AI Retouch (ChatGPT):** เลือกรูป (สูงสุด 2/โฟลเดอร์) → เปิดเบราว์เซอร์ผ่าน Playwright → อัปโหลดเข้า ChatGPT Custom GPT → ดาวน์โหลดผลเป็นไฟล์ `_AI`
    - Custom GPT URL ตั้งใน Settings (เว้นว่าง = ใช้ chatgpt.com ปกติ พร้อมส่ง prompt มาตรฐาน)
- **1.6 Merge:** เลือก 2 รูป/โฟลเดอร์ → หน้าจัดวาง (scale/swap) → บันทึก `<code>-merged.jpg` บนพื้นขาว 2000x2000
- **1.7 Crop:** เลือกรูปที่จะครอบตัด (หลายรูป) → ปรับ zoom/ตำแหน่ง ทีละรูป
- **2. Rename & Primary:** เลือกรูปหลัก (gallery 160x160, 5 คอลัมน์) → เปลี่ยนชื่อตามรหัส (มี `_rename_temp` กู้คืน)
- **3. Collect to DB:** ก๊อปปี้ไป Photo 1 (Main) + Photo 2 (Backup) พร้อมกัน ตรวจไดรฟ์ (E005) ก่อน
- **4. Archive:** ย้ายเข้าคลังตามปี/เดือน/วัน
- **Centralized Error Codes:** E001-E007 พร้อมคำอธิบายภาษาไทยใน Log + Message Box

## ⚡ Engineering & Windows Standards
- **Non-blocking UI:** กระบวนการหนัก (AI, Copying, Import) ต้องรันบน `threading.Thread` และอัปเดต widget ผ่าน `root.after`/`*_threadsafe` เท่านั้น
- **File System:** ใช้ `os.path.normpath` และจัดการปัญหา "File already exists" บน Windows (Rename ใช้ `_rename_temp`, Import ใช้ suffix `_dup`)
- **Secrets:** ไม่มี API key แล้ว — การยืนยันตัวตน ChatGPT ใช้ session ในเบราว์เซอร์ (ผู้ใช้ล็อกอินเอง) ห้ามฝัง token ใดๆ ใน source
- **Handoff:** ก่อนเริ่มงานให้อ่าน `HANDOFF.md` และเมื่อทำเสร็จให้เพิ่มบันทึกว่าแก้อะไร ทดสอบอะไร และยังเหลือ risk อะไร

---
*อัปเดตล่าสุด: 2026-05-28 - v2.2 Beta 1 (Wizard UI + ChatGPT, ลบ Gemini API, เพิ่ม Step 0 Import)*
