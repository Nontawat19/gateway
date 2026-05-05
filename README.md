# 🚀 BMG Attendance Gateway (Face Recognition Logic)

สคริปต์ Python สำหรับรันบนเครื่อง Server (เช่น N-Tech FindFace) เพื่อรับข้อมูลใบหน้าและบันทึกลงระบบ Cloud อย่างมีประสิทธิภาพ

## 🛠 ฟีเจอร์ระดับสูง (Advanced Features)
- **Web-based Setup:** ตั้งค่ารหัสโรงเรียนผ่านหน้าเว็บได้ที่ `http://localhost:5000/config` (ไม่ต้องแก้โค้ด)
- **Performance Optimized:** ระบบ Cache Config ในแรม ลดค่าใช้จ่าย Firebase (Read) ได้มหาศาล
- **High Reliability:** มีระบบ Queue และ Auto-Retry Loop หากเน็ตหลุด ข้อมูลจะถูกส่งซ้ำจนสำเร็จ
- **Data Integrity:** ระบบเช็คสแกนซ้ำ (Deduplication) ในระดับวินาที ป้องกันขยะเข้าสู่ระบบ Cloud

---

## 📋 สิ่งที่ต้องเตรียม (Prerequisites)
1. **Python 3.9+**
2. **Libraries:** ติดตั้งผ่าน `pip install -r requirements.txt`
3. **Tailscale:** แนะนำให้ใช้เพื่อรีโมทเข้ามาดูแลจากส่วนกลาง

---

## 🚀 วิธีการใช้งาน (Running)
1. **รันสคริปต์:**
   ```bash
   python app.py
   ```
2. **ตั้งค่ารหัสโรงเรียน:**
   เปิดเบราว์เซอร์ไปที่ `http://localhost:5000/config` แล้วกรอกรหัสโรงเรียนของคุณ
3. **เชื่อมต่อ FindFace:**
   ในหน้า Webhooks ของ FindFace ให้ระบุ URL:
   `http://localhost:5000/webhook/attendance`

---

## 📡 โครงสร้างการทำงาน (Data Flow)
`FindFace -> Gateway (SQLite Check) -> Background Queue -> Firebase Cloud`

## 📁 รายละเอียดไฟล์
* `app.py`: ตัวรับ Webhook, ระบบ Config UI และ Logic หลัก
* `database.py`: ฐานข้อมูล SQLite ท้องถิ่น (Persistent Cache)
* `firebase_service.py`: การส่งข้อมูลและอัปเดตสถิติ Summary
* `logic.py`: คำนวณช่วงเวลา (Windows) เข้า-ออก และสถานะมาสาย

---
© 2026 BMG SoftTech - Attendance Intelligence System
