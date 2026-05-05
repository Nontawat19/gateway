import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
from logic import get_summary_keys, get_period_status_mapping

# ==========================================
# Initialize Firebase 
# ==========================================
# ดึง Path ของโฟลเดอร์ปัจจุบัน และระบุชื่อไฟล์ JSON ให้ตรงกับที่อยู่ในเครื่อง
cred_path = os.path.join(os.path.dirname(__file__), "epp5online-firebase-adminsdk-fbsvc-f8e9e138dd.json")

if not firebase_admin._apps:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # หากหาไฟล์ไม่เจอ จะแจ้งเตือนเพื่อให้ตรวจสอบชื่อไฟล์อีกครั้ง
        raise FileNotFoundError(f"❌ ไม่พบไฟล์ Key สำหรับ Firebase ที่: {cred_path}")

db = firestore.client()
# ==========================================

def fetch_school_config(school_id):
    doc_ref = db.collection("school-settings").document(school_id)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("attendanceConfig", {})
    return {}

def get_school_info_by_code(school_code):
    """ค้นหา School UID และชื่อโรงเรียน จากรหัสโรงเรียน (schoolCode)"""
    query = db.collection("school-settings").where("schoolCode", "==", str(school_code)).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        return doc.id, data.get("schoolName") or data.get("name") or "ไม่ระบุชื่อโรงเรียน"
    return None, None

def fetch_user_info(school_id, user_id):
    # Search students
    students_ref = db.collection("school-settings").document(school_id).collection("students")
    query = students_ref.where("studentId", "==", user_id).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        data['id'] = doc.id
        data['type'] = 'student'
        return data
        
    # Search teachers
    teachers_ref = db.collection("school-settings").document(school_id).collection("teachers")
    query = teachers_ref.where("teacherId", "==", user_id).limit(1).stream()
    for doc in query:
        data = doc.to_dict()
        data['id'] = doc.id
        data['type'] = 'teacher'
        return data
        
    return None

def sync_to_firebase(school_id, user_info, status, action_type, dt):
    batch = db.batch()
    date_str = dt.strftime("%Y-%m-%d")
    user_id_internal = user_info['id']
    user_type = user_info['type']
    collection_name = "students" if user_type == "student" else "teachers"
    
    # 1. Attendance Record
    att_ref = db.collection("school-settings").document(school_id)\
                .collection(collection_name).document(user_id_internal)\
                .collection("attendance").document(date_str)
    
    att_data = {
        "schoolId": school_id,
        "date": date_str,
        "userType": user_type,
        "classLevel": user_info.get("classLevel") or user_info.get("grade") or "",
        "status": status,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "metadata": {"description": "บันทึกจากระบบใบหน้า", "isGateCheckin": True}
    }
    
    if action_type == "in":
        att_data["checkinTime"] = dt
    else:
        att_data["checkoutTime"] = dt
        
    batch.set(att_ref, att_data, merge=True)
    
    # 2. Update Summaries
    keys = get_summary_keys(dt)
    new_key = get_period_status_mapping(status)
    
    if new_key:
        updates = {new_key: firestore.Increment(1)}
        
        # Weekly, Monthly, Yearly, Semester
        for summary_type in ["Weeksummary", "Monthsummary", "Yearsummary", "Semestersummary"]:
            key = keys["weekKey"] if summary_type == "Weeksummary" else \
                  keys["monthKey"] if summary_type == "Monthsummary" else \
                  keys["yearKey"] if summary_type == "Yearsummary" else \
                  keys["semesterKey"]
            
            ref = db.collection("school-settings").document(school_id)\
                    .collection(collection_name).document(user_id_internal)\
                    .collection(summary_type).document(key)
            batch.set(ref, updates, merge=True)
            
        # Daily Summary (Todaysummary)
        today_ref = db.collection("school-settings").document(school_id)\
                      .collection("Todaysummary").document(f"{user_type}s_{date_str}")
        
        today_updates = {
            new_key: firestore.Increment(1),
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "type": f"{user_type}s",
            "date": date_str
        }
        
        # Class breakdown for students
        class_id = user_info.get("classLevel") or user_info.get("grade")
        if user_type == "student" and class_id:
            today_updates[f"classes.{class_id}.{new_key}"] = firestore.Increment(1)
            
        batch.set(today_ref, today_updates, merge=True)

    batch.commit()
    return True