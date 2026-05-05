import asyncio
import json
import os
from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from datetime import datetime, timedelta
import database as db_local
import firebase_service as fb
import logic

app = FastAPI()

# ไฟล์สำหรับเก็บรายการโรงเรียนทั้งหมด
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "schools_config.json")

# Global Cache Variables
# SCHOOL_CACHE = { "school_code": { "id": "...", "config": "...", "expiry": "..." } }
SCHOOL_CACHE = {}
LAST_CLEANUP_DATE = None

def load_schools():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_schools(schools: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(schools, f)

@app.on_event("startup")
async def startup_event():
    global LAST_CLEANUP_DATE, SCHOOL_CACHE
    db_local.init_db()
    
    today = datetime.now().strftime("%Y-%m-%d")
    db_local.clear_old_records(today)
    LAST_CLEANUP_DATE = today
    
    # โหลดรายการโรงเรียนและเตรียม Cache
    schools = load_schools()
    for code in schools:
        print(f"📡 Pre-loading school: {code}")
        await refresh_school_cache(code)
    
    print(f"🚀 Multi-school Hub Started ({len(schools)} schools loaded)")
    asyncio.create_task(retry_loop())

async def refresh_school_cache(school_code):
    global SCHOOL_CACHE
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

# --- [หน้าเว็บจัดการโรงเรียน - ULTIMATE DASHBOARD UI] ---
@app.get("/config", response_class=HTMLResponse)
async def get_config(request: Request):
    schools = load_schools()
    host = request.headers.get("host")
    
    # เตรียมข้อมูลสำหรับส่งให้ JavaScript จัดการต่อที่ฝั่ง Client
    school_list_data = []
    for code, meta in schools.items():
        school_data = SCHOOL_CACHE.get(code)
        is_ready = school_data is not None
        school_list_data.append({
            "code": code,
            "name": school_data["name"] if is_ready else "กำลังโหลดข้อมูล...",
            "is_ready": is_ready,
            "added_at": meta.get('added_at', 'Unknown')[:10],
            "webhook_url": f"http://{host}/webhook/attendance/{code}"
        })

    # แปลงเป็น JSON string
    schools_json = json.dumps(school_list_data)

    return f"""
    <!DOCTYPE html>
    <html lang="th" data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BMG Hub | Control Center</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Anuphan:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-body: #0a0c10;
                --bg-card: #161b22;
                --text-main: #e6edf3;
                --accent: linear-gradient(135deg, #3fb950 0%, #238636 100%);
            }}
            [data-bs-theme="light"] {{
                --bg-body: #f6f8fa;
                --bg-card: #ffffff;
                --text-main: #1f2328;
                --accent: linear-gradient(135deg, #2da44e 0%, #1a7f37 100%);
            }}
            body {{ background-color: var(--bg-body); color: var(--text-main); font-family: 'Anuphan', 'Outfit', sans-serif; transition: all 0.3s ease; }}
            .glass-card {{ background: var(--bg-card); border: 1px solid rgba(128,128,128,0.2); border-radius: 20px; padding: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
            .navbar {{ background: var(--bg-card); border-bottom: 1px solid rgba(128,128,128,0.2); }}
            .btn-accent {{ background: var(--accent); color: white; border: none; font-weight: 600; border-radius: 10px; }}
            .btn-accent:hover {{ opacity: 0.9; color: white; transform: translateY(-1px); }}
            .search-input {{ background: rgba(128,128,128,0.1); border: 1px solid rgba(128,128,128,0.3); color: var(--text-main); border-radius: 10px; }}
            .search-input:focus {{ background: rgba(128,128,128,0.15); color: var(--text-main); border-color: #2da44e; box-shadow: none; }}
            .pagination .page-link {{ background: var(--bg-card); border-color: rgba(128,128,128,0.3); color: var(--text-main); }}
            .pagination .active .page-link {{ background: #2da44e; border-color: #2da44e; }}
            .table {{ color: var(--text-main); }}
            .badge-online {{ background: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid rgba(63, 185, 80, 0.3); }}
            .badge-offline {{ background: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.3); }}
            .copy-btn {{ cursor: pointer; transition: 0.2s; }}
            .copy-btn:hover {{ color: #2da44e; }}
        </style>
    </head>
    <body>
        <nav class="navbar mb-4">
            <div class="container d-flex justify-content-between align-items-center py-2">
                <h4 class="fw-bold mb-0">🚀 BMG Attendance Hub</h4>
                <div class="d-flex gap-3 align-items-center">
                    <input type="text" id="searchInput" class="form-control search-input" placeholder="🔍 ค้นหาชื่อหรือรหัสโรงเรียน..." style="width: 280px;">
                    <button class="btn btn-outline-secondary btn-sm" id="themeToggle">🌓 สลับโหมด</button>
                </div>
            </div>
        </nav>

        <div class="container">
            <div class="row g-4">
                <!-- Add Section -->
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

                <!-- List Section -->
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
                                <tbody id="schoolTableBody">
                                    <!-- JS will inject rows here -->
                                </tbody>
                            </table>
                        </div>
                        
                        <!-- Pagination -->
                        <nav class="mt-4 d-flex justify-content-center">
                            <ul class="pagination pagination-sm" id="pagination">
                                <!-- JS will inject pagination here -->
                            </ul>
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

            // --- Theme Logic ---
            const themeToggle = document.getElementById('themeToggle');
            const html = document.documentElement;
            
            // Load saved theme
            const savedTheme = localStorage.getItem('theme') || 'dark';
            html.setAttribute('data-bs-theme', savedTheme);

            themeToggle.addEventListener('click', () => {{
                const current = html.getAttribute('data-bs-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                html.setAttribute('data-bs-theme', next);
                localStorage.setItem('theme', next);
            }});

            // --- Search Logic ---
            const searchInput = document.getElementById('searchInput');
            searchInput.addEventListener('input', (e) => {{
                const term = e.target.value.toLowerCase();
                filteredSchools = allSchools.filter(s => 
                    s.name.toLowerCase().includes(term) || 
                    s.code.toLowerCase().includes(term)
                );
                currentPage = 1;
                renderTable();
            }});

            // --- Render Logic ---
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
                if (totalPages <= 1) {{
                    pagination.innerHTML = '';
                    return;
                }}

                let html = '';
                // First & Prev
                html += `<li class="page-item ${{currentPage === 1 ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(1)">หน้าแรก</a></li>`;
                html += `<li class="page-item ${{currentPage === 1 ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{currentPage - 1}})">ย้อนกลับ</a></li>`;

                // Numbers
                for (let i = 1; i <= totalPages; i++) {{
                    if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {{
                        html += `<li class="page-item ${{currentPage === i ? 'active' : ''}}"><a class="page-link" href="#" onclick="changePage(${{i}})">${{i}}</a></li>`;
                    }} else if (i === currentPage - 3 || i === currentPage + 3) {{
                        html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
                    }}
                }}

                // Next & Last
                html += `<li class="page-item ${{currentPage === totalPages ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{currentPage + 1}})">ถัดไป</a></li>`;
                html += `<li class="page-item ${{currentPage === totalPages ? 'disabled' : ''}}"><a class="page-link" href="#" onclick="changePage(${{totalPages}})">หน้าสุดท้าย</a></li>`;

                pagination.innerHTML = html;
            }}

            window.changePage = function(page) {{
                currentPage = page;
                renderTable();
            }};

            window.copyToClipboard = function(text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert('คัดลอก URL เรียบร้อย!');
                }});
            }};

            // Initial Render
            renderTable();
        </script>
    </body>
    </html>
    """

@app.post("/config/add")
async def add_school(school_code: str = Form(...)):
    schools = load_schools()
    if school_code not in schools:
        success = await refresh_school_cache(school_code)
        if success:
            schools[school_code] = {"added_at": datetime.now().isoformat()}
            save_schools(schools)
    return RedirectResponse(url="/config", status_code=303)

@app.get("/config/delete/{school_code}")
async def delete_school(school_code: str):
    schools = load_schools()
    if school_code in schools:
        del schools[school_code]
        save_schools(schools)
        if school_code in SCHOOL_CACHE:
            del SCHOOL_CACHE[school_code]
    return RedirectResponse(url="/config", status_code=303)

# --- [Webhook Endpoint สำหรับหลายโรงเรียน] ---
@app.post("/webhook/attendance/{school_code}")
async def handle_attendance(school_code: str, request: Request, background_tasks: BackgroundTasks):
    global SCHOOL_CACHE, LAST_CLEANUP_DATE
    
    # 1. ตรวจสอบว่ารหัสโรงเรียนนี้มีในระบบไหม
    school_data = SCHOOL_CACHE.get(school_code)
    if not school_data:
        # พยายามโหลดเข้า Cache ถ้ามีในลิสต์แต่ยังไม่มีใน Cache
        schools = load_schools()
        if school_code in schools:
            success = await refresh_school_cache(school_code)
            if success: school_data = SCHOOL_CACHE[school_code]
            
    if not school_data:
        return {"status": "error", "message": f"School {school_code} not found or not configured"}

    data = await request.json()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # 2. แกะข้อมูล ID บุคคลจาก FindFace
    user_id = data.get("matched_card") or data.get("person_id")
    if not user_id and "face_event" in data:
        fe = data["face_event"]
        if "matched_dossier" in fe and fe["matched_dossier"]:
            user_id = fe["matched_dossier"].get("external_id")
    
    if not user_id: return {"status": "error", "message": "No user_id found"}

    # 3. ตรวจสอบ Cache Expiry ของ Config
    if now > school_data["expiry"]:
        await refresh_school_cache(school_code)
        school_data = SCHOOL_CACHE[school_code]

    # 4. ดึงข้อมูลผู้ใช้ (เช็ค SQLite ก่อนเพื่อประหยัดเงิน)
    school_id = school_data["id"]
    user_info = db_local.get_cached_user(user_id)
    
    if not user_info:
        # ถ้าในเครื่องไม่มีข้อมูล ค่อยไปดึงจาก Firebase 1 ครั้ง
        user_info = fb.fetch_user_info(school_id, user_id)
        if user_info:
            # ดึงมาได้แล้ว เซฟลง SQLite ไว้ใช้ในครั้งถัดไปทันที
            db_local.update_user_cache(user_id, school_id, user_info)
            print(f"📥 Cached new user: {user_id}")
    
    if not user_info:
        return {"status": "error", "message": "User not found in local or cloud"}

    action_type, status = logic.calculate_status(now, school_data["config"], user_info['type'])
    if not action_type:
        return {"status": "ignored", "message": "Outside windows"}

    # 5. เช็คซ้ำใน SQLite
    if db_local.check_existing_record(user_id, today, action_type):
        return {"status": "skipped", "message": "Duplicate scan ignored"}

    # 6. ส่งเข้าคิว
    background_tasks.add_task(process_attendance_hub, school_id, user_info, now, action_type, status)
    
    return {"status": "processing", "user_id": user_id, "school": school_code, "action": action_type}

async def process_attendance_hub(school_id, user_info, dt, action_type, status):
    user_id = user_info['studentId'] if user_info['type'] == 'student' else user_info['teacherId']
    
    # 1. บันทึก SQLite (ระบุ school_id ด้วย)
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
            # [TODO] ส่งแจ้งเตือน LINE
    except Exception as e:
        print(f"❌ Hub Sync Failed: {e}")

@app.get("/", response_class=RedirectResponse)
async def root_redirect():
    return RedirectResponse(url="/config")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse(content="", status_code=204)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5050)
