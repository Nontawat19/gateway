"""
🎨 Dashboard HTML Template Generator
สร้างหน้าเว็บ Semester Summary Dashboard พร้อม Chart.js
"""
import json

def render_dashboard(school_name: str, school_code: str, class_levels: list, summary_data: dict = None, selected_class: str = "", selected_room: str = "", selected_term: str = "1", academic_year: str = "") -> str:
    summary_json = json.dumps(summary_data or {}, ensure_ascii=False)
    levels_json = json.dumps(class_levels, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="th" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>สรุปภาคเรียน - {school_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Anuphan:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f1117;
            --bg-card: #1a1d27;
            --bg-card-hover: #22263a;
            --border: #2a2e3d;
            --text-primary: #e8eaf0;
            --text-secondary: #8b8fa3;
            --accent: #6366f1;
            --accent-glow: rgba(99,102,241,0.25);
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --blue: #3b82f6;
            --orange: #f97316;
            --indigo: #818cf8;
        }}
        [data-theme="light"] {{
            --bg-primary: #f1f5f9;
            --bg-card: #ffffff;
            --bg-card-hover: #f8fafc;
            --border: #e2e8f0;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Anuphan',sans-serif; background:var(--bg-primary); color:var(--text-primary); min-height:100vh; }}
        .navbar {{ background:var(--bg-card); border-bottom:1px solid var(--border); padding:12px 24px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:50; backdrop-filter:blur(12px); }}
        .navbar h1 {{ font-size:18px; font-weight:700; display:flex; align-items:center; gap:8px; }}
        .navbar .controls {{ display:flex; gap:8px; align-items:center; }}
        .btn {{ padding:8px 16px; border-radius:10px; border:1px solid var(--border); background:var(--bg-card); color:var(--text-primary); cursor:pointer; font-family:inherit; font-size:13px; transition:all .2s; }}
        .btn:hover {{ background:var(--bg-card-hover); transform:translateY(-1px); }}
        .btn-accent {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
        .btn-accent:hover {{ box-shadow:0 4px 20px var(--accent-glow); }}
        .container {{ max-width:1400px; margin:0 auto; padding:24px; }}

        /* Filter Bar */
        .filter-bar {{ background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:20px; margin-bottom:24px; display:flex; flex-wrap:wrap; gap:16px; align-items:end; }}
        .filter-group {{ display:flex; flex-direction:column; gap:4px; }}
        .filter-group label {{ font-size:12px; color:var(--text-secondary); font-weight:500; }}
        .filter-group select, .filter-group input {{ padding:8px 12px; border-radius:8px; border:1px solid var(--border); background:var(--bg-primary); color:var(--text-primary); font-family:inherit; font-size:14px; outline:none; min-width:140px; }}
        .filter-group select:focus, .filter-group input:focus {{ border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-glow); }}

        /* Summary Cards */
        .summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin-bottom:24px; }}
        .summary-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:16px; text-align:center; transition:all .3s; position:relative; overflow:hidden; }}
        .summary-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px; }}
        .summary-card.green::before {{ background:var(--green); }}
        .summary-card.yellow::before {{ background:var(--yellow); }}
        .summary-card.blue::before {{ background:var(--blue); }}
        .summary-card.red::before {{ background:var(--red); }}
        .summary-card.orange::before {{ background:var(--orange); }}
        .summary-card.indigo::before {{ background:var(--indigo); }}
        .summary-card:hover {{ transform:translateY(-3px); box-shadow:0 8px 25px rgba(0,0,0,0.2); }}
        .summary-card .label {{ font-size:13px; color:var(--text-secondary); margin-bottom:4px; }}
        .summary-card .value {{ font-size:28px; font-weight:700; }}
        .summary-card.green .value {{ color:var(--green); }}
        .summary-card.yellow .value {{ color:var(--yellow); }}
        .summary-card.blue .value {{ color:var(--blue); }}
        .summary-card.red .value {{ color:var(--red); }}
        .summary-card.orange .value {{ color:var(--orange); }}
        .summary-card.indigo .value {{ color:var(--indigo); }}

        /* Charts */
        .charts-row {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px; }}
        .chart-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:16px; padding:20px; }}
        .chart-card h3 {{ font-size:15px; font-weight:600; margin-bottom:16px; display:flex; align-items:center; gap:8px; }}
        .chart-container {{ position:relative; width:100%; }}

        /* Table */
        .table-card {{ background:var(--bg-card); border:1px solid var(--border); border-radius:16px; overflow:hidden; }}
        .table-card h3 {{ padding:16px 20px; font-size:15px; font-weight:600; border-bottom:1px solid var(--border); }}
        table {{ width:100%; border-collapse:collapse; }}
        th {{ padding:12px 16px; text-align:center; font-size:12px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; background:var(--bg-primary); border-bottom:1px solid var(--border); }}
        th:first-child {{ text-align:left; padding-left:20px; }}
        td {{ padding:10px 16px; text-align:center; font-size:14px; border-bottom:1px solid var(--border); }}
        td:first-child {{ text-align:left; padding-left:20px; }}
        tr:hover {{ background:var(--bg-card-hover); }}
        .student-name {{ display:flex; align-items:center; gap:10px; }}
        .student-name img {{ width:32px; height:32px; border-radius:50%; object-fit:cover; border:2px solid var(--border); }}
        .student-name span {{ font-weight:500; }}
        .badge {{ padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }}
        .badge-green {{ background:rgba(34,197,94,0.15); color:var(--green); }}
        .badge-yellow {{ background:rgba(234,179,8,0.15); color:var(--yellow); }}
        .badge-red {{ background:rgba(239,68,68,0.15); color:var(--red); }}

        .overall-banner {{ background:linear-gradient(135deg,var(--accent),#8b5cf6); border-radius:16px; padding:24px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; color:#fff; }}
        .overall-banner .big {{ font-size:42px; font-weight:700; }}
        .overall-banner .label {{ font-size:14px; opacity:0.8; }}

        .empty-state {{ text-align:center; padding:60px 20px; color:var(--text-secondary); }}
        .empty-state .icon {{ font-size:48px; margin-bottom:12px; }}
        .spinner {{ display:inline-block; width:20px; height:20px; border:3px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:spin .6s linear infinite; }}
        @keyframes spin {{ to {{ transform:rotate(360deg); }} }}

        @media(max-width:768px) {{
            .charts-row {{ grid-template-columns:1fr; }}
            .filter-bar {{ flex-direction:column; }}
            .summary-grid {{ grid-template-columns:repeat(3,1fr); }}
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>📊 สรุปการมาเรียน - {school_name}</h1>
        <div class="controls">
            <a href="/config" class="btn">← กลับหน้าหลัก</a>
            <button class="btn" onclick="toggleTheme()">🌓</button>
        </div>
    </nav>

    <div class="container">
        <form class="filter-bar" method="GET" id="filterForm">
            <div class="filter-group">
                <label>ชั้นเรียน</label>
                <select name="class_level" id="classLevel" onchange="document.getElementById('filterForm').submit()">
                    {"".join(f'<option value="{c}" {"selected" if c == selected_class else ""}>{c}</option>' for c in class_levels)}
                </select>
            </div>
            <div class="filter-group">
                <label>ห้อง</label>
                <select name="room" id="roomSelect" onchange="document.getElementById('filterForm').submit()">
                    <option value="">ทุกห้อง</option>
                    {"".join(f'<option value="{i}" {"selected" if str(i) == selected_room else ""}>{i}</option>' for i in range(1, 21))}
                </select>
            </div>
            <div class="filter-group">
                <label>ภาคเรียน</label>
                <select name="term" onchange="document.getElementById('filterForm').submit()">
                    <option value="1" {"selected" if selected_term == "1" else ""}>ภาคเรียนที่ 1</option>
                    <option value="2" {"selected" if selected_term == "2" else ""}>ภาคเรียนที่ 2</option>
                </select>
            </div>
            <div class="filter-group">
                <label>ปีการศึกษา (พ.ศ.)</label>
                <input type="text" name="year" value="{academic_year}" style="width:100px;">
            </div>
            <button type="submit" class="btn btn-accent">🔍 ค้นหา</button>
        </form>

        <div id="content">
            {"" if not summary_data or not summary_data.get("students") else render_summary_section(summary_data, selected_class, selected_room, selected_term, academic_year)}
            {"<div class='empty-state'><div class='icon'>📋</div><p>เลือกชั้นเรียนและกดค้นหาเพื่อดูข้อมูลสรุปภาคเรียน</p></div>" if not summary_data or not summary_data.get("students") else ""}
        </div>
    </div>

    <script>
        const summaryData = {summary_json};

        function toggleTheme() {{
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
            localStorage.setItem('theme', html.getAttribute('data-theme'));
            // Re-render charts with new colors
            if (summaryData && summaryData.students && summaryData.students.length > 0) {{
                setTimeout(() => {{ renderCharts(); }}, 100);
            }}
        }}

        // Load saved theme
        const saved = localStorage.getItem('theme');
        if (saved) document.documentElement.setAttribute('data-theme', saved);

        function renderCharts() {{
            if (!summaryData || !summaryData.students || summaryData.students.length === 0) return;
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDark ? '#e8eaf0' : '#1e293b';
            const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

            // Donut Chart
            const donutCtx = document.getElementById('donutChart');
            if (donutCtx) {{
                if (window._donutChart) window._donutChart.destroy();
                const t = summaryData.totals;
                window._donutChart = new Chart(donutCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['มา', 'สาย', 'ลา', 'ขาด', 'ไม่ลงเวลาออก', 'ไปราชการ'],
                        datasets: [{{
                            data: [t.present, t.late, t.leave, t.absent, t.noCheckout || 0, t.officialTravel],
                            backgroundColor: ['#22c55e', '#eab308', '#3b82f6', '#ef4444', '#f97316', '#818cf8'],
                            borderWidth: 2,
                            borderColor: isDark ? '#1a1d27' : '#ffffff',
                            hoverOffset: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        cutout: '60%',
                        plugins: {{
                            legend: {{ position: 'bottom', labels: {{ color: textColor, padding: 16, usePointStyle: true, pointStyleWidth: 10, font: {{ family: 'Anuphan', size: 13 }} }} }}
                        }}
                    }}
                }});
            }}

            // Bar Chart (Top 15 students)
            const barCtx = document.getElementById('barChart');
            if (barCtx) {{
                if (window._barChart) window._barChart.destroy();
                const top15 = summaryData.students.slice(0, 15);
                const labels = top15.map(s => s.fullName.length > 12 ? s.fullName.substring(0,12)+'...' : s.fullName);
                window._barChart = new Chart(barCtx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [
                            {{ label: 'มา', data: top15.map(s => s.present), backgroundColor: '#22c55e', borderRadius: 4 }},
                            {{ label: 'สาย', data: top15.map(s => s.late), backgroundColor: '#eab308', borderRadius: 4 }},
                            {{ label: 'ลา', data: top15.map(s => s.leave), backgroundColor: '#3b82f6', borderRadius: 4 }},
                            {{ label: 'ขาด', data: top15.map(s => s.absent), backgroundColor: '#ef4444', borderRadius: 4 }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ labels: {{ color: textColor, usePointStyle: true, font: {{ family: 'Anuphan', size: 12 }} }} }}
                        }},
                        scales: {{
                            x: {{ stacked: true, ticks: {{ color: textColor, font: {{ family: 'Anuphan', size: 10 }}, maxRotation: 45 }}, grid: {{ display: false }} }},
                            y: {{ stacked: true, ticks: {{ color: textColor }}, grid: {{ color: gridColor }} }}
                        }}
                    }}
                }});
            }}

            // Percentage Line Chart
            const lineCtx = document.getElementById('lineChart');
            if (lineCtx) {{
                if (window._lineChart) window._lineChart.destroy();
                const sorted = [...summaryData.students].sort((a,b) => b.percentage - a.percentage);
                window._lineChart = new Chart(lineCtx, {{
                    type: 'line',
                    data: {{
                        labels: sorted.map((s,i) => `#${{i+1}}`),
                        datasets: [{{
                            label: 'ร้อยละการมาเรียน',
                            data: sorted.map(s => s.percentage),
                            borderColor: '#6366f1',
                            backgroundColor: 'rgba(99,102,241,0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: 3,
                            pointBackgroundColor: '#6366f1'
                        }}, {{
                            label: 'เกณฑ์ 80%',
                            data: sorted.map(() => 80),
                            borderColor: '#ef4444',
                            borderDash: [5, 5],
                            pointRadius: 0,
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ labels: {{ color: textColor, usePointStyle: true, font: {{ family: 'Anuphan', size: 12 }} }} }}
                        }},
                        scales: {{
                            x: {{ ticks: {{ color: textColor, font: {{ size: 10 }} }}, grid: {{ display: false }} }},
                            y: {{ min: 0, max: 100, ticks: {{ color: textColor }}, grid: {{ color: gridColor }} }}
                        }}
                    }}
                }});
            }}
        }}

        // Initial render
        if (summaryData && summaryData.students && summaryData.students.length > 0) {{
            setTimeout(renderCharts, 200);
        }}
    </script>
</body>
</html>"""


def render_summary_section(data: dict, class_level: str, room: str, term: str, year: str) -> str:
    """สร้าง HTML section สำหรับแสดงผลข้อมูลสรุป"""
    t = data.get("totals", {})
    students = data.get("students", [])
    overall = data.get("overallPercentage", 0)
    room_label = f"/{room}" if room else ""

    cards_html = f"""
    <div class="overall-banner">
        <div>
            <div class="label">ภาคเรียนที่ {term} ปีการศึกษา {year} • {class_level}{room_label} • {len(students)} คน</div>
            <div class="big">{overall}%</div>
            <div class="label">อัตราการมาเรียนรวม</div>
        </div>
        <div style="font-size:64px;">{"🎉" if overall >= 90 else "⚠️" if overall >= 80 else "🚨"}</div>
    </div>

    <div class="summary-grid">
        <div class="summary-card green"><div class="label">มาเรียน</div><div class="value">{t.get('present',0)}</div></div>
        <div class="summary-card yellow"><div class="label">สาย</div><div class="value">{t.get('late',0)}</div></div>
        <div class="summary-card blue"><div class="label">ลา</div><div class="value">{t.get('leave',0)}</div></div>
        <div class="summary-card red"><div class="label">ขาด</div><div class="value">{t.get('absent',0)}</div></div>
        <div class="summary-card orange"><div class="label">ไม่ลงเวลาออก</div><div class="value">{t.get('noCheckout',0)}</div></div>
        <div class="summary-card indigo"><div class="label">ไปราชการ</div><div class="value">{t.get('officialTravel',0)}</div></div>
    </div>

    <div class="charts-row">
        <div class="chart-card">
            <h3>🍩 สัดส่วนสถานะภาพรวม</h3>
            <div class="chart-container" style="max-width:350px;margin:auto;"><canvas id="donutChart"></canvas></div>
        </div>
        <div class="chart-card">
            <h3>📈 ร้อยละการมาเรียนแต่ละคน</h3>
            <div class="chart-container" style="height:300px;"><canvas id="lineChart"></canvas></div>
        </div>
    </div>

    <div class="chart-card" style="margin-bottom:24px;">
        <h3>📊 สถิติรายบุคคล (15 คนแรก)</h3>
        <div class="chart-container" style="height:350px;"><canvas id="barChart"></canvas></div>
    </div>
    """

    # Table
    rows_html = ""
    for i, s in enumerate(students, 1):
        pct = s.get("percentage", 0)
        badge_class = "badge-green" if pct >= 90 else "badge-yellow" if pct >= 80 else "badge-red"
        profile = s.get("profileImageUrl") or "https://ui-avatars.com/api/?name=S&background=6366f1&color=fff&size=32"
        rows_html += f"""<tr>
            <td style="text-align:center;color:var(--text-secondary);">{i}</td>
            <td><div class="student-name"><img src="{profile}" alt="" onerror="this.src='https://ui-avatars.com/api/?name=S&background=6366f1&color=fff&size=32'"><span>{s['fullName']}</span></div></td>
            <td style="color:var(--green);font-weight:600;">{s['present']}</td>
            <td style="color:var(--yellow);font-weight:600;">{s['late']}</td>
            <td style="color:var(--blue);font-weight:600;">{s['leave']}</td>
            <td style="color:var(--red);font-weight:600;">{s['absent']}</td>
            <td style="color:var(--orange);font-weight:600;">{s['noCheckout']}</td>
            <td style="color:var(--indigo);font-weight:600;">{s['officialTravel']}</td>
            <td>{s['total']}</td>
            <td><span class="badge {badge_class}">{pct}%</span></td>
        </tr>"""

    table_html = f"""
    <div class="table-card">
        <h3>📋 ตารางสรุปรายบุคคล</h3>
        <div style="overflow-x:auto;">
            <table>
                <thead><tr>
                    <th style="text-align:center;">ที่</th><th>ชื่อ-นามสกุล</th><th>มา</th><th>สาย</th><th>ลา</th><th>ขาด</th><th>ไม่ลงเวลา</th><th>ไปราชการ</th><th>รวม</th><th>ร้อยละ</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>"""

    return cards_html + table_html
