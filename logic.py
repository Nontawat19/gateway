from datetime import datetime, date
import math

def get_iso_week_key(dt):
    year, week, _ = dt.isocalendar()
    return f"{year}-W{str(week).zfill(2)}"

def get_academic_year_and_term(dt):
    month = dt.month
    year = dt.year
    be_year = year + 543
    
    term = "1"
    academic_year = be_year
    
    if 5 <= month <= 10:
        term = "1"
        academic_year = be_year
    elif month >= 11:
        term = "2"
        academic_year = be_year
    elif month <= 4:
        term = "2"
        academic_year = be_year - 1
        
    return str(academic_year), term

def get_summary_keys(dt, academic_year_override=None):
    week_key = get_iso_week_key(dt)
    month_key = dt.strftime("%Y-%m")
    
    ac_year, term = get_academic_year_and_term(dt)
    year_key = academic_year_override or ac_year
    semester_key = f"{year_key}-{term}"
    
    return {
        "weekKey": week_key,
        "monthKey": month_key,
        "yearKey": year_key,
        "semesterKey": semester_key
    }

def calculate_status(dt, config, user_type):
    """
    ตัดสินใจว่าเป็นขาเข้า/ออก และสถานะอะไร โดยอิงจาก config ที่ตั้งไว้ในระบบ
    """
    time_str = dt.strftime("%H:%M")
    prefix = "student" if user_type == "student" else "teacher"
    
    # ดึงค่า Config (พร้อมค่า Default กันเหนียว)
    checkin_start = config.get(f"{prefix}CheckinStart", "05:00")
    checkin_end = config.get(f"{prefix}CheckinEnd", "11:59")
    checkout_start = config.get(f"{prefix}CheckoutStart", "12:00")
    checkout_end = config.get(f"{prefix}CheckoutEnd", "23:59")
    
    late_time = config.get(f"{prefix}LateTime", "08:00")
    checkout_min_time = config.get(f"{prefix}CheckoutTime", "15:30")

    action_type = None
    status = "มา"

    # 1. ตรวจสอบช่วงเวลาเช็คอิน (In)
    if checkin_start <= time_str <= checkin_end:
        action_type = "in"
        if time_str > late_time:
            status = "สาย"
        else:
            status = "มา"
            
    # 2. ตรวจสอบช่วงเวลาเช็คเอาท์ (Out)
    elif checkout_start <= time_str <= checkout_end:
        action_type = "out"
        if time_str < checkout_min_time:
            status = "กลับก่อน"
        else:
            status = "มา"
    
    # 3. กรณีอยู่นอกช่วงเวลาทั้งหมด
    else:
        # อาจจะเป็นการสแกนเล่น หรือสแกนผิดเวลา
        return None, "นอกช่วงเวลา"
            
    return action_type, status

def get_period_status_mapping(status):
    if not status: return None
    s = status.lower()
    if s in ['มา', 'ontime', 'present', 'กลับก่อน', 'earlyreturn', 'early']: return 'present'
    if s in ['สาย', 'late']: return 'late'
    if s in ['ลา', 'leave'] or 'ลา' in s: return 'leave'
    if s in ['ขาด', 'absent']: return 'absent'
    if s in ['ไปราชการ', 'officialtravel']: return 'officialTravel'
    return None
