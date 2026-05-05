import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import firebase_service as fb
import database as db_local
import logic
import notifier
from datetime import datetime, timedelta
import asyncio
import json
import os
import traceback

app = FastAPI(title="BMG Attendance Hub")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("="*50)
    print(f"❌ GLOBAL ERROR: {exc}")
    traceback.print_exc()
    print("="*50)
    return HTMLResponse(content=f"Internal Server Error: {exc}", status_code=500)

# --- Configuration & Caching ---
SCHOOLS_FILE = os.path.join(os.path.dirname(__file__), "schools_config.json")
SCHOOL_CACHE = {} # { "school_code": { "id": "UID", "name": "Name", "config": {}, "expiry": datetime } }

def load_schools():
    if os.path.exists(SCHOOLS_FILE):
        with open(SCHOOLS_FILE, "r") as f:
            return json.load(f)
    return {}

def get_tailscale_ip():
    """ตรวจหาเลข IP ของ Tailscale (100.x.x.x) จากเครื่อง"""
    try:
        import socket
        import subprocess
        # ลองใช้ hostname -I เพื่อความรวดเร็วบน Linux
        ips = subprocess.check_output(['hostname', '-I']).decode().split()
        for ip in ips:
            if ip.startswith('100.'):
                return ip
        return None
    except:
        return None

def save_schools(schools):
    with open(SCHOOLS_FILE, "w") as f:
        json.dump(schools, f)

async def refresh_school_cache(school_code):
    """โหลด/รีเฟรชค่า Config และข้อมูลโรงเรียนจาก Firebase"""
    school_id, school_name = fb.get_school_info_by_code(school_code)
    if school_id:
        config = fb.fetch_school_config(school_id)
        SCHOOL_CACHE[school_code] = {
            "id": school_id,
            "name": school_name,
            "config": config,
            "expiry": datetime.now() + timedelta(days=30)
        }
        return True
    return False

# --- Background Tasks ---

async def retry_loop():
    """ระบบตรวจหาข้อมูลที่ส่งไม่สำเร็จและส่งซ้ำทุกๆ 5 นาที"""
    while True:
        await asyncio.sleep(300)
        try:
            unsynced = db_local.get_unsynced_records()
            if unsynced:
                print(f"🔄 Retrying {len(unsynced)} unsynced records...")
                for record in unsynced:
                    sid = record.get('school_id')
                    if not sid: continue
                    
                    user_info = db_local.get_cached_user(record['user_id'])
                    if user_info:
                        dt = datetime.strptime(f"{record['scan_date']} {record['scan_time']}", "%Y-%m-%d %H:%M:%S")
                        success = fb.sync_to_firebase(sid, user_info, record['status'], record['action_type'], dt)
                        if success:
                            db_local.update_sync_status(record['id'], 1)
        except Exception as e:
            print(f"❌ Retry Loop Error: {e}")

async def midnight_cleanup_loop():
    """ระบบล้างข้อมูลอัตโนมัติเวลาเที่ยงคืน (เฉพาะรายการที่ Sync แล้ว)"""
    while True:
        now = datetime.now()
        # เช็คทุก 1 ชั่วโมง ถ้าอยู่ในช่วงเที่ยงคืน ให้ล้างข้อมูลเก่า
        if now.hour == 0:
            count = db_local.clear_old_records()
            if count > 0:
                print(f"🧹 Midnight Cleanup: Removed {count} synced records from previous days.")
        
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    db_local.init_db()
    # ล้างข้อมูลทันทีที่เปิดเครื่อง (เผื่อเปิดหลังเที่ยงคืน)
    db_local.clear_old_records()
    
    # โหลดแคชเริ่มต้น
    schools = load_schools()
    for code in schools:
        await refresh_school_cache(code)
        
    asyncio.create_task(retry_loop())
    asyncio.create_task(midnight_cleanup_loop())

def serialize_firestore_data(data):
    """แปลงข้อมูลพิเศษจาก Firestore (เช่น Timestamp) ให้เป็นข้อมูลพื้นฐานที่ JSON รองรับ"""
    if isinstance(data, dict):
        return {k: serialize_firestore_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_firestore_data(i) for i in data]
    elif hasattr(data, 'isoformat'): # สำหรับ datetime และ Timestamp
        return data.isoformat()
    return data

# --- Dashboard Routes ---

@app.get("/config", response_class=HTMLResponse)
async def get_config(request: Request):
    schools = load_schools()
    ts_ip = get_tailscale_ip()
    # ถ้าเจอ Tailscale IP ให้ใช้ IP นั้น ถ้าไม่เจอให้ใช้ Host ปกติ
    base_url = ts_ip if ts_ip else request.headers.get("host").split(':')[0]
    port = request.scope['server'][1]
    
    school_list_data = []
    for code, meta in schools.items():
        s_data = SCHOOL_CACHE.get(code)
        is_ready = s_data is not None
        school_list_data.append({
            "code": code,
            "name": s_data["name"] if is_ready else "กำลังโหลด...",
            "is_ready": is_ready,
            "added_at": meta.get('added_at', 'Unknown')[:10],
            "webhook_url": f"http://{base_url}:{port}/webhook/attendance/{code}"
        })

    schools_json = json.dumps(school_list_data)

    return f"""
    <!DOCTYPE html>
    <html lang="th" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BMG Attendance Hub</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Anuphan:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --accent-color: #00d2ff;
                --bg-dark: #0d1117;
                --card-bg: rgba(22, 27, 34, 0.8);
            }}
            body {{ font-family: 'Anuphan', sans-serif; background: var(--bg-dark); color: #c9d1d9; }}
            .glass-card {{
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border: 1px solid #30363d;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            .btn-accent {{ background: var(--accent-color); color: #000; font-weight: 600; border-radius: 8px; border: none; transition: 0.3s; }}
            .btn-accent:hover {{ background: #33e0ff; transform: translateY(-2px); }}
            .search-input {{ background: #161b22; border: 1px solid #30363d; color: #fff; border-radius: 12px; }}
            .search-input:focus {{ background: #1c2128; border-color: var(--accent-color); color: #fff; box-shadow: none; }}
            .badge-online {{ background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid rgba(63, 185, 80, 0.4); }}
            .badge-offline {{ background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.4); }}
            .copy-btn {{ cursor: pointer; transition: 0.2s; }}
            .copy-btn:hover {{ color: var(--accent-color); }}
            .extra-small {{ font-size: 0.75rem; }}
            .pagination .page-link {{ background: #161b22; border-color: #30363d; color: #c9d1d9; }}
            .pagination .page-item.active .page-link {{ background: var(--accent-color); border-color: var(--accent-color); color: #000; }}
            .pagination .page-item.disabled .page-link {{ background: #0d1117; color: #484f58; }}
        </style>
    </head>
    <body>
        <nav class="navbar border-bottom border-secondary-subtle mb-4 py-3">
            <div class="container">
                <span class="navbar-brand fw-bold text-white">🚀 BMG Hub</span>
                <div class="d-flex align-items-center gap-3">
                    <input type="text" id="searchInput" class="form-control form-control-sm search-input" placeholder="ค้นหาโรงเรียน..." style="width: 250px;">
                    <button class="btn btn-sm btn-outline-light" id="themeToggle">🌓 Mode</button>
                </div>
            </div>
        </nav>

        <div class="container">
            <div class="row g-4">
                <div class="col-lg-12">
                    <div class="glass-card mb-4">
                        <form action="/config/add" method="post" class="row g-3 align-items-end">
                            <div class="col-md-9">
                                <label class="form-label small text-secondary">ลงทะเบียนโรงเรียนใหม่</label>
                                <input type="text" name="school_code" class="form-control form-control-lg search-input" placeholder="ใส่รหัสโรงเรียน (School Code)" required>
                            </div>
                            <div class="col-md-3">
                                <button type="submit" class="btn btn-accent w-100 py-2">➕ เพิ่มโรงเรียน</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="col-lg-12">
                    <div class="glass-card">
                        <div class="table-responsive">
                            <table class="table align-middle">
                                <thead class="small text-secondary">
                                    <tr>
                                        <th>ชื่อโรงเรียน / รหัส</th>
                                        <th>สถานะ</th>
                                        <th>Webhook URL</th>
                                        <th class="text-end">จัดการ</th>
                                    </tr>
                                </thead>
                                <tbody id="schoolTableBody"></tbody>
                            </table>
                        </div>
                        <nav class="mt-4 d-flex justify-content-center">
                            <ul class="pagination pagination-sm" id="pagination"></ul>
                        </nav>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let allSchools = {schools_json};
            let filteredSchools = [...allSchools];
            let currentPage = 1;
            const itemsPerPage = 20;

            const themeToggle = document.getElementById('themeToggle');
            const html = document.documentElement;
            const savedTheme = localStorage.getItem('theme') || 'dark';
            html.setAttribute('data-bs-theme', savedTheme);

            themeToggle.addEventListener('click', () => {{
                const current = html.getAttribute('data-bs-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-bs-theme', next);
                localStorage.setItem('theme', next);
            }});

            const searchInput = document.getElementById('searchInput');
            searchInput.addEventListener('input', (e) => {{
                const term = e.target.value.toLowerCase();
                filteredSchools = allSchools.filter(s => 
                    s.name.toLowerCase().includes(term) || s.code.toLowerCase().includes(term)
                );
                currentPage = 1;
                renderTable();
            }});

            function renderTable() {{
                const start = (currentPage - 1) * itemsPerPage;
                const end = start + itemsPerPage;
                const pageItems = filteredSchools.slice(start, end);
                const tableBody = document.getElementById('schoolTableBody');
                
                tableBody.innerHTML = pageItems.map(s => `
                    <tr>
                        <td>
                            <div class="fw-bold">${{s.name}}</div>
                            <div class="extra-small text-secondary">Code: ${{s.code}} | Added: ${{s.added_at}}</div>
                        </td>
                        <td>
                            <span class="badge ${{s.is_ready ? 'badge-online' : 'badge-offline'}}">
                                ${{s.is_ready ? 'Online' : 'Loading...'}}
                            </span>
                        </td>
                        <td>
                            <div class="d-flex align-items-center gap-2">
                                <code class="small text-info bg-dark-subtle px-2 py-1 rounded">${{s.webhook_url}}</code>
                                <span class="copy-btn" onclick="copyToClipboard('${{s.webhook_url}}')">📋</span>
                            </div>
                        </td>
                        <td class="text-end">
                            <a href="/config/delete/${{s.code}}" class="btn btn-sm btn-outline-danger" onclick="return confirm('ลบโรงเรียนนี้?')">ลบ</a>
                        </td>
                    </tr>
                `).join('');

                if (pageItems.length === 0) {{
                    tableBody.innerHTML = '<tr><td colspan="4" class="text-center py-5 text-muted">ไม่พบข้อมูลโรงเรียน</td></tr>';
                }}
                renderPagination();
            }}

            function renderPagination() {{
                const totalPages = Math.ceil(filteredSchools.length / itemsPerPage);
                const pagination = document.getElementById('pagination');
                if (totalPages <= 1) {{ pagination.innerHTML = ''; return; }}

                let html = '';
                html += `<li class="page-item ${{currentPage === 1 ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(1)">หน้าแรก</a></li>`;
                html += `<li class="page-item ${{currentPage === 1 ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{currentPage - 1}})">ย้อนกลับ</a></li>`;

                for (let i = 1; i <= totalPages; i++) {{
                    if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {{
                        html += `<li class="page-item ${{currentPage === i ? 'active' : ''}}"><a class="page-link" href="#" onclick="changePage(${{i}})">${{i}}</a></li>`;
                    }} else if (i === currentPage - 3 || i === currentPage + 3) {{
                        html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
                    }}
                }}

                html += `<li class="page-item ${{currentPage === totalPages ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{currentPage + 1}})">ถัดไป</a></li>`;
                html += `<li class="page-item ${{currentPage === totalPages ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{totalPages}})">หน้าสุดท้าย</a></li>`;
                pagination.innerHTML = html;
            }}

            window.changePage = function(page) {{ currentPage = page; renderTable(); }};
            window.copyToClipboard = function(text) {{
                navigator.clipboard.writeText(text).then(() => {{ alert('คัดลอก URL เรียบร้อย!'); }});
            }};
            
            const urlParams = new URLSearchParams(window.location.search);
            const msg = urlParams.get('msg');
            const error = urlParams.get('error');
            if (msg) alert(msg);
            if (error) alert('❌ Error: ' + error);

            renderTable();
        </script>
    </body>
    </html>
    """

@app.post("/config/add")
async def add_school(school_code: str = Form(...)):
    # 1. ตรวจสอบที่ Firebase ก่อนว่ามีโรงเรียนนี้จริงไหม
    school_id, school_name = fb.get_school_info_by_code(school_code)
    
    if not school_id:
        # ถ้าไม่พบโรงเรียน ไม่ต้องบันทึก และส่ง error กลับไป
        return RedirectResponse(url="/config?error=ไม่พบรหัสโรงเรียนนี้ในระบบ Firebase", status_code=303)

    schools = load_schools()
    if school_code not in schools:
        schools[school_code] = {"added_at": str(datetime.now())}
        save_schools(schools)
        # โหลดเข้า Cache ทันที
        SCHOOL_CACHE[school_code] = {
            "id": school_id,
            "name": school_name,
            "config": fb.fetch_school_config(school_id),
            "expiry": datetime.now() + timedelta(days=30)
        }
        return RedirectResponse(url="/config?msg=เพิ่มโรงเรียนสำเร็จ", status_code=303)
    
    return RedirectResponse(url="/config?msg=โรงเรียนนี้ถูกเพิ่มไว้แล้ว", status_code=303)

@app.get("/config/delete/{school_code}")
async def delete_school(school_code: str):
    schools = load_schools()
    if school_code in schools:
        del schools[school_code]
        save_schools(schools)
        if school_code in SCHOOL_CACHE:
            del SCHOOL_CACHE[school_code]
        return RedirectResponse(url="/config?msg=ลบโรงเรียนเรียบร้อยแล้ว", status_code=303)
    return RedirectResponse(url="/config", status_code=303)

# --- Attendance Webhook ---

@app.post("/webhook/attendance/{school_code}")
async def handle_attendance(school_code: str, request: Request, background_tasks: BackgroundTasks):
    # 1. ตรวจสอบโรงเรียน
    school_data = SCHOOL_CACHE.get(school_code)
    if not school_data:
        # ลองรีเฟรชถ้าไม่มีในแคช
        success = await refresh_school_cache(school_code)
        if not success:
            return {"status": "error", "message": f"School {school_code} not found"}
        school_data = SCHOOL_CACHE[school_code]

    data = await request.json()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # 2. แกะ ID จาก FindFace
    user_id = data.get("matched_card") or data.get("person_id")
    if not user_id and "face_event" in data:
        fe = data["face_event"]
        if "matched_dossier" in fe and fe["matched_dossier"]:
            user_id = fe["matched_dossier"].get("external_id")
    
    if not user_id: return {"status": "error", "message": "No user_id found"}

    # 3. ดึงข้อมูลผู้ใช้ (เช็ค SQLite Cache ก่อน)
    school_id = school_data["id"]
    user_info = db_local.get_cached_user(user_id)
    
    if not user_info:
        user_info = fb.fetch_user_info(school_id, user_id)
        if user_info:
            # แปลงข้อมูลให้เป็น JSON-friendly ก่อนเก็บลง SQLite
            serializable_user = serialize_firestore_data(user_info)
            db_local.update_user_cache(user_id, school_id, serializable_user)
            print(f"📥 Cached new user: {user_id}")
            user_info = serializable_user
    
    if not user_info:
        return {"status": "error", "message": "User not found"}

    # 4. คำนวณสถานะ
    action_type, status = logic.calculate_status(now, school_data["config"], user_info['type'])
    if not action_type:
        return {"status": "ignored", "message": "Outside windows"}

    # 5. เช็คซ้ำใน SQLite
    if db_local.check_existing_record(user_id, today, action_type):
        return {"skipped": "ignored", "message": "Duplicate scan ignored"}

    # 6. ส่งเข้าคิวประมวลผลเบื้องหลัง
    background_tasks.add_task(process_attendance_hub, school_id, user_info, now, action_type, status)
    
    return {"status": "processing", "user_id": user_id, "school": school_code, "action": action_type}

async def process_attendance_hub(school_id, user_info, dt, action_type, status):
    user_id = user_info['studentId'] if user_info['type'] == 'student' else user_info['teacherId']
    
    # 1. บันทึก SQLite
    record_id = db_local.insert_record(
        school_id=school_id,
        user_id=user_id,
        user_type=user_info['type'],
        action_type=action_type,
        status=status,
        scan_date=dt.strftime("%Y-%m-%d"),
        scan_time=dt.strftime("%H:%M:%S")
    )
    
    # 2. บันทึก Firebase
    try:
        success = fb.sync_to_firebase(school_id, user_info, status, action_type, dt)
        if success:
            db_local.update_sync_status(record_id, 1)
            
            # --- ส่งแจ้งเตือน LINE ---
            print(f"📣 Preparing LINE notification for: {user_info.get('name')}")
            
            # 1. ลองดึงจากครูประจำชั้น
            class_id = user_info.get("classLevel") or user_info.get("grade") or user_info.get("homeroomGrade")
            line_config = fb.get_teacher_line_config(school_id, class_id)
            if line_config:
                print(f"👤 Found Teacher LINE config for class {class_id}")
            
            # 2. ถ้าไม่มีครูประจำชั้น ให้ลองดึงจากโรงเรียน (Fallback)
            if not line_config:
                school_code = next((code for code, data in SCHOOL_CACHE.items() if data['id'] == school_id), None)
                if school_code:
                    school_data = SCHOOL_CACHE[school_code]
                    line_config = school_data.get("config", {}).get("lineSettings", {}).get("school")
                    if line_config:
                        print(f"🏫 Fallback to School LINE config for {school_code}")
            
            if line_config:
                time_str = dt.strftime("%H:%M")
                notifier.send_line_attendance_notification(user_info, status, time_str, line_config)
            else:
                print(f"⚠️ NO LINE CONFIG FOUND: User: {user_info.get('name')}, Class: {class_id}")
                print(f"🔍 Debug Info - SchoolID: {school_id}")
    except Exception as e:
        print(f"❌ Hub Sync Failed or Notification Error: {e}")
        traceback.print_exc()

@app.get("/", response_class=RedirectResponse)
async def root_redirect():
    return "/config"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5050)
