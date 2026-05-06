"""
📊 Semester Summary Module
ดึงข้อมูลสรุปการมาเรียนรายภาคเรียนจาก Firebase โดยตรง
แสดงผลเป็น Dashboard พร้อม Chart.js
"""
import firebase_service as fb
from logic import get_academic_year_and_term
from datetime import datetime


def fetch_class_levels(school_id: str) -> list[str]:
    """ดึงรายการระดับชั้นที่มีในโรงเรียน"""
    try:
        doc_ref = fb.db.collection("school-settings").document(school_id)
        doc_snap = doc_ref.get()
        if doc_snap.exists:
            data = doc_snap.to_dict()
            level_range = data.get("opportunityExpansionLevel", "")

            primary = ["ป.1", "ป.2", "ป.3", "ป.4", "ป.5", "ป.6"]
            junior = ["ม.1", "ม.2", "ม.3"]
            senior = ["ม.4", "ม.5", "ม.6"]

            if level_range == "ป.1-ป.6":
                return primary
            elif level_range == "ม.1-ม.6":
                return junior + senior
            elif level_range == "ป.1-ม.3":
                return primary + junior
            elif level_range == "ป.1-ม.6":
                return primary + junior + senior
            else:
                return primary + junior + senior
        return []
    except Exception as e:
        print(f"❌ Error fetching class levels: {e}")
        return []


def fetch_students_by_class(school_id: str, class_level: str, room: str = "") -> list[dict]:
    """ดึงรายชื่อนักเรียนตามห้อง"""
    try:
        students_ref = fb.db.collection("school-settings").document(school_id).collection("students")
        query = students_ref.where("classLevel", "==", class_level)
        if room:
            query = query.where("room", "==", room)

        results = []
        for doc in query.stream():
            data = doc.to_dict()
            title = data.get("title", "")
            fname = data.get("firstName", "")
            lname = data.get("lastName", "")
            full_name = f"{title}{fname} {lname}".strip()
            results.append({
                "id": doc.id,
                "fullName": full_name,
                "studentNumber": data.get("studentNumber", 0),
                "classLevel": data.get("classLevel", ""),
                "room": data.get("room", ""),
                "profileImageUrl": data.get("profileImageUrl", "")
            })

        # จัดเรียงตามเลขที่
        results.sort(key=lambda x: x.get("studentNumber", 0))
        return results
    except Exception as e:
        print(f"❌ Error fetching students: {e}")
        return []


def fetch_semester_summary(school_id: str, student_id: str, semester_key: str) -> dict:
    """ดึงข้อมูลสรุปภาคเรียนของนักเรียน 1 คน จาก Semestersummary"""
    try:
        ref = fb.db.collection("school-settings").document(school_id) \
            .collection("students").document(student_id) \
            .collection("Semestersummary").document(semester_key)
        snap = ref.get()
        if snap.exists:
            return snap.to_dict()
        return {}
    except Exception as e:
        print(f"❌ Error fetching semester summary for {student_id}: {e}")
        return {}


def fetch_class_semester_summary(school_id: str, class_level: str, room: str, semester_key: str) -> dict:
    """
    ดึงข้อมูลสรุปภาคเรียนของทั้งห้อง
    Returns: { students: [...], totals: {...}, classInfo: {...} }
    """
    students = fetch_students_by_class(school_id, class_level, room)
    results = []
    totals = {"present": 0, "late": 0, "leave": 0, "absent": 0, "officialTravel": 0, "noCheckout": 0}

    for student in students:
        data = fetch_semester_summary(school_id, student["id"], semester_key)
        present = data.get("present", 0)
        late = data.get("late", 0)
        leave = data.get("leave", 0)
        absent = data.get("absent", 0)
        official_travel = data.get("officialTravel", 0)
        no_checkout = data.get("noCheckout", 0)

        total = present + late + leave + absent + official_travel + no_checkout
        attended = present + late + no_checkout + official_travel
        percentage = round((attended / total * 100), 2) if total > 0 else 0.0

        student_stat = {
            **student,
            "present": present,
            "late": late,
            "leave": leave,
            "absent": absent,
            "officialTravel": official_travel,
            "noCheckout": no_checkout,
            "total": total,
            "percentage": percentage,
        }
        results.append(student_stat)

        # รวมยอด
        totals["present"] += present
        totals["late"] += late
        totals["leave"] += leave
        totals["absent"] += absent
        totals["officialTravel"] += official_travel
        totals["noCheckout"] += no_checkout

    grand_total = sum(totals.values())
    grand_attended = totals["present"] + totals["late"] + totals["noCheckout"] + totals["officialTravel"]
    overall_percentage = round((grand_attended / grand_total * 100), 2) if grand_total > 0 else 0.0

    return {
        "students": results,
        "totals": totals,
        "grandTotal": grand_total,
        "overallPercentage": overall_percentage,
        "classInfo": {
            "classLevel": class_level,
            "room": room,
            "semesterKey": semester_key,
            "studentCount": len(students)
        }
    }


def get_current_semester_key() -> tuple[str, str, str]:
    """
    คืนค่า (academicYear, term, semesterKey) ปัจจุบัน
    เช่น ("2569", "1", "2569-1")
    """
    now = datetime.now()
    ac_year, term = get_academic_year_and_term(now)
    return ac_year, term, f"{ac_year}-{term}"
