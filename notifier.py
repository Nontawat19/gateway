import requests
import json
import urllib.parse
import traceback

def send_line_attendance_notification(user_info, status, time_str, line_config):
    """
    ส่งแจ้งเตือน LINE OA Flex Message (เลียนแบบดีไซน์ Dashboard Premium 100%)
    """
    try:
        if not line_config:
            return False
            
        token = line_config.get('lineChannelAccessToken')
        is_enabled = line_config.get('enableNotification', True)
        
        if not token or not is_enabled:
            print("❌ LINE Notification disabled or missing token", flush=True)
            return False

        # 1. เตรียมข้อมูลพื้นฐาน
        name = user_info.get('name')
        if not name:
            title = user_info.get('title', '')
            fname = user_info.get('firstName', '')
            lname = user_info.get('lastName', '')
            name = f"{title}{fname} {lname}".strip() or "ไม่ระบุชื่อ"
            
        display_id = user_info.get('studentId') or user_info.get('teacherId') or user_info.get('displayId', '-')
        grade = user_info.get('classLevel') or user_info.get('grade') or user_info.get('homeroomGrade') or "-"
        profile_url = user_info.get('profileImageUrl') or "https://ui-avatars.com/api/?name=User&background=random"
        parent_ids = user_info.get('parentLineUserIds', [])

        # 2. เตรียมข้อมูลสถิติและคะแนน
        stats = user_info.get('attendanceStats', {'present': 0, 'late': 0, 'leave': 0, 'absent': 0})
        score = user_info.get('behaviorScore', 100)
        total_days = stats.get('present', 0) + stats.get('late', 0) + stats.get('absent', 0) + stats.get('leave', 0)

        # 3. สร้างกราฟวงกลม (Donut Chart) ผ่าน QuickChart.io
        chart_config = {
            'type': 'doughnut',
            'data': {
                'datasets': [{
                    'data': [stats.get('present') or 1 if total_days == 0 else stats.get('present', 0), 
                             stats.get('late', 0), 
                             stats.get('absent', 0), 
                             stats.get('leave', 0)],
                    'backgroundColor': ['#1DB446', '#FFC107', '#FF5722', '#00BCD4'],
                    'borderWidth': 2,
                    'borderColor': '#ffffff'
                }]
            },
            'options': {
                'plugins': {
                    'datalabels': { 'display': False },
                    'doughnutlabel': {
                        'labels': [
                            { 'text': str(total_days), 'font': { 'size': 26, 'weight': 'bold', 'family': 'sans-serif' }, 'color': '#333333' },
                            { 'text': 'วัน', 'font': { 'size': 14, 'family': 'sans-serif' }, 'color': '#666666' }
                        ]
                    }
                }
            }
        }
        chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(json.dumps(chart_config))}&w=200&h=200"

        # 4. สร้าง Flex Message (โครงสร้าง giga bubble เหมือนต้นฉบับ 100%)
        flex_contents = {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "20px",
                "backgroundColor": "#ffffff",
                "contents": [
                    # --- ส่วนหัว: ข้อมูลนักเรียน ---
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": "70px",
                                "height": "70px",
                                "cornerRadius": "100px",
                                "contents": [{"type": "image", "url": profile_url, "size": "full", "aspectMode": "cover"}]
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "margin": "lg",
                                "contents": [
                                    {"type": "text", "text": name, "weight": "bold", "size": "xl", "color": "#111111"},
                                    {"type": "text", "text": f"{grade} • {display_id}", "size": "sm", "color": "#666666", "margin": "xs"}
                                ]
                            }
                        ]
                    },

                    # --- ส่วนที่ 1: สถานะการเข้าเรียน (กราฟ + สถิติ) ---
                    {
                        "type": "box",
                        "layout": "vertical",
                        "paddingAll": "15px",
                        "backgroundColor": "#fcfcfc",
                        "cornerRadius": "15px",
                        "borderWidth": "1px",
                        "borderColor": "#eeeeee",
                        "margin": "xl",
                        "contents": [
                            {"type": "text", "text": "สถานะการเข้าเรียน ภาคเรียนนี้", "weight": "bold", "size": "md", "color": "#333333"},
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "lg",
                                "alignItems": "center",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "flex": 1,
                                        "spacing": "sm",
                                        "contents": [
                                            {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🟢", "size": "xs", "flex": 0}, {"type": "text", "text": "มาเรียน", "size": "sm", "color": "#666666", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('present', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                            {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🟡", "size": "xs", "flex": 0}, {"type": "text", "text": "สาย", "size": "sm", "color": "#666666", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('late', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                            {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🔴", "size": "xs", "flex": 0}, {"type": "text", "text": "ขาด", "size": "sm", "color": "#666666", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('absent', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                            {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🔵", "size": "xs", "flex": 0}, {"type": "text", "text": "ลา", "size": "sm", "color": "#666666", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('leave', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]}
                                        ]
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "width": "110px",
                                        "height": "110px",
                                        "contents": [{"type": "image", "url": chart_url, "size": "full", "aspectMode": "fit"}]
                                    }
                                ]
                            }
                        ]
                    },

                    # --- ส่วนที่ 2: สถานะปัจจุบัน (Bubble) ---
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "xl",
                        "backgroundColor": "#f0fdf4" if status == 'มา' else "#fffbeb",
                        "cornerRadius": "12px",
                        "paddingAll": "12px",
                        "alignItems": "center",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": "30px",
                                "height": "30px",
                                "backgroundColor": "#1db446" if status == 'มา' else "#fbbf24",
                                "cornerRadius": "100px",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "contents": [{"type": "text", "text": "✓" if status == 'มา' else "!", "color": "#ffffff", "size": "sm", "weight": "bold", "align": "center"}]
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "margin": "md",
                                "contents": [
                                    {"type": "text", "text": f"{name} {status}แล้วเวลา {time_str} น.", "size": "sm", "color": "#166534" if status == 'มา' else "#92400e", "weight": "bold", "wrap": True},
                                    {"type": "text", "text": "ทำรายการสำเร็จ" if status == 'มา' else "กรุณามาให้ทันเวลาในครั้งถัดไป", "size": "xs", "color": "#166534" if status == 'มา' else "#92400e", "margin": "xs"}
                                ]
                            }
                        ]
                    },

                    # --- ส่วนที่ 3: คะแนนพฤติกรรม ---
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "paddingAll": "15px",
                        "backgroundColor": "#ffffff",
                        "cornerRadius": "15px",
                        "borderWidth": "1px",
                        "borderColor": "#eeeeee",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "คะแนนพฤติกรรม ภาคเรียนนี้", "weight": "bold", "size": "sm", "color": "#333333", "flex": 4},
                                    {"type": "text", "text": "ดูย้อนหลัง", "size": "xs", "color": "#666666", "align": "end", "flex": 2}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "md",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "flex": 1,
                                        "contents": [
                                            {"type": "text", "text": f"{score}/100", "weight": "bold", "size": "xxl", "color": "#1DB446" if score >= 80 else "#EAB308"},
                                            {"type": "text", "text": "มีพฤติกรรมที่ดีมาก" if score >= 80 else "ควรปรับปรุงพฤติกรรม", "size": "xs", "color": "#888888", "margin": "xs"}
                                        ]
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "flex": 1,
                                        "spacing": "xs",
                                        "contents": [
                                            {"type": "text", "text": "ยอดใช้จ่าย: - บาท", "size": "xs", "color": "#666666", "align": "end"},
                                            {"type": "text", "text": "ยอดเงินคงเหลือ: - บาท", "size": "xs", "color": "#666666", "align": "end"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    },

                    # --- ส่วนที่ 4: ข่าวสารจากโรงเรียน ---
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {"type": "text", "text": "ข่าวสารจากโรงเรียน", "weight": "bold", "size": "sm", "color": "#333333"},
                            {
                                "type": "box",
                                "layout": "vertical",
                                "margin": "md",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "box", "layout": "horizontal", "spacing": "md", "alignItems": "center", "contents": [
                                            {"type": "text", "text": "📄", "size": "md", "flex": 0},
                                            {"type": "text", "text": "ใบแจ้งหนี้ค่าเทอม", "size": "sm", "color": "#444444", "flex": 1},
                                            {"type": "text", "text": "📑", "size": "md", "flex": 0, "color": "#aaaaaa"}
                                        ]
                                    },
                                    {
                                        "type": "box", "layout": "horizontal", "spacing": "md", "alignItems": "center", "contents": [
                                            {"type": "text", "text": "📅", "size": "md", "flex": 0},
                                            {"type": "text", "text": "ประกาศวันหยุดราชการ", "size": "sm", "color": "#444444", "flex": 1},
                                            {"type": "text", "text": "📑", "size": "md", "flex": 0, "color": "#aaaaaa"}
                                        ]
                                    },
                                    {
                                        "type": "box", "layout": "horizontal", "spacing": "md", "alignItems": "center", "contents": [
                                            {"type": "text", "text": "🖋️", "size": "md", "flex": 0},
                                            {"type": "text", "text": "ใบอนุญาตไปทัศนศึกษา", "size": "sm", "color": "#444444", "flex": 1},
                                            {"type": "text", "text": "เซ็นรับรองออนไลน์", "size": "xs", "color": "#1DB446", "weight": "bold", "flex": 0}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        # 5. เตรียม Payload สำหรับส่ง
        payload = {
            "messages": [
                {
                    "type": "flex",
                    "altText": f"รายงานการเข้าเรียน: {name}",
                    "contents": flex_contents
                }
            ]
        }

        # 6. เลือก URL (Broadcast หรือ Multicast หาผู้ปกครอง)
        if parent_ids:
            url = "https://api.line.me/v2/bot/message/multicast"
            payload["to"] = parent_ids
            print(f"🎯 Sending Dashboard Multicast to {len(parent_ids)} parents", flush=True)
        else:
            url = "https://api.line.me/v2/bot/message/broadcast"
            print(f"📢 Sending Dashboard Broadcast", flush=True)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        # 7. ส่งข้อมูล
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        if response.status_code == 200:
            print(f"✅ Dashboard LINE Notification sent successfully for {name}", flush=True)
            return True
        else:
            print(f"❌ Failed to send Dashboard LINE notification: {response.status_code} - {response.text}", flush=True)
            return False

    except Exception as e:
        print(f"❌ Error in send_line_attendance_notification: {e}", flush=True)
        traceback.print_exc()
        return False
