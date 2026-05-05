import requests
import json
import urllib.parse

def send_line_attendance_notification(user_info, status, time_str, line_config):
    """
    ส่งแจ้งเตือน LINE OA Flex Message (เลียนแบบ AttendanceLineNotify.ts)
    """
    if not line_config:
        return False
        
    token = line_config.get('lineChannelAccessToken')
    is_enabled = line_config.get('enableNotification', True)
    
    if not token or not is_enabled:
        print("❌ LINE Notification disabled or missing token")
        return False

    stats = user_info.get('attendanceStats', {'present': 0, 'late': 0, 'leave': 0, 'absent': 0})
    score = user_info.get('behaviorScore', 100)
    name = user_info.get('name', 'ไม่ระบุชื่อ')
    display_id = user_info.get('displayId', '-')
    grade = user_info.get('grade', '-')
    profile_url = user_info.get('profileImageUrl') or "https://ui-avatars.com/api/?name=Student&background=random"
    parent_ids = user_info.get('parentLineUserIds', [])

    # สร้าง Chart URL (Doughnut Chart) ผ่าน QuickChart.io
    chart_config = {
        'type': 'doughnut',
        'data': {
            'datasets': [{
                'data': [stats.get('present', 0), stats.get('late', 0), stats.get('absent', 0), stats.get('leave', 0)],
                'backgroundColor': ['#1DB446', '#FFC107', '#FF5722', '#00BCD4'],
                'borderWidth': 2,
                'borderColor': '#ffffff'
            }]
        },
        'options': {
            'plugins': {
                'datalabels': { 'display': False }
            }
        }
    }
    chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(json.dumps(chart_config))}&w=200&h=200"

    # Flex Message Contents
    flex_contents = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "20px",
            "backgroundColor": "#ffffff",
            "contents": [
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
                                        {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🟢", "size": "xs", "flex": 0}, {"type": "text", "text": "มาเรียน", "size": "sm", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('present', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                        {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🟡", "size": "xs", "flex": 0}, {"type": "text", "text": "สาย", "size": "sm", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('late', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                        {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🔴", "size": "xs", "flex": 0}, {"type": "text", "text": "ขาด", "size": "sm", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('absent', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]},
                                        {"type": "box", "layout": "horizontal", "contents": [{"type": "text", "text": "🔵", "size": "xs", "flex": 0}, {"type": "text", "text": "ลา", "size": "sm", "margin": "md", "flex": 4}, {"type": "text", "text": str(stats.get('leave', 0)), "size": "sm", "weight": "bold", "align": "end", "flex": 2}]}
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
                                {"type": "text", "text": f"{user_info.get('name', 'นักเรียน')} {status}แล้วเวลา {time_str} น.", "size": "sm", "color": "#166534" if status == 'มา' else "#92400e", "weight": "bold", "wrap": True},
                                {"type": "text", "text": "ทำรายการสำเร็จ" if status == 'มา' else "กรุณามาให้ทันเวลาในครั้งถัดไป", "size": "xs", "color": "#166534" if status == 'มา' else "#92400e", "margin": "xs"}
                            ]
                        }
                    ]
                }
            ]
        }
    }

    payload = {
        "messages": [
            {
                "type": "flex",
                "altText": f"รายงานการเข้าเรียน: {name}",
                "contents": flex_contents
            }
        ]
    }

    if parent_ids:
        url = "https://api.line.me/v2/bot/message/multicast"
        payload["to"] = parent_ids
    else:
        url = "https://api.line.me/v2/bot/message/broadcast"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code == 200:
            print(f"✅ LINE Notification sent successfully for {name}")
            return True
        else:
            print(f"❌ Failed to send LINE notification: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending LINE notification: {e}")
        return False
