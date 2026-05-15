import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TAIWAN_TZ = pytz.timezone("Asia/Taipei")

def get_calendar():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        
        # 今天的日期（美東時間，格式 2026-05-15）
        today = datetime.now(pytz.timezone("America/New_York")).strftime("%Y-%m-%d")
        print("比對日期: " + today)
        
        events = []
        for item in data:
            item_date = item.get("date", "")
            # API 日期格式是 2026-05-15T09:15:00-04:00，取前10碼比對
            if item_date[:10] != today:
                continue
            if item.get("impact", "") not in ["High", "Medium"]:
                continue
            
            # 時間轉換
            try:
                dt = datetime.fromisoformat(item_date)
                tw_time = dt.astimezone(TAIWAN_TZ).strftime("%H:%M")
            except:
                tw_time = "--"

            events.append({
                "time": tw_time,
                "currency": item.get("country", "--"),
                "event": item.get("title", "--"),
                "impact": item.get("impact", "--"),
                "forecast": item.get("forecast", "--") or "--",
                "previous": item.get("previous", "--") or "--",
            })
        
        return events
    except Exception as e:
        print("抓取失敗: " + str(e))
        return []

def send_to_discord(events):
    today = datetime.now(TAIWAN_TZ).strftime("%Y/%m/%d")
    imp_emoji = {"High": "🔴 高", "Medium": "🟡 中"}
    imp_color = {"High": 15158332, "Medium": 16776960}

    header = {
        "embeds": [{
            "title": "📊 今日高風險總經數據預警",
            "description": "⚠️ 今日有高影響力數據公布，請留意市場波動，嚴格控管合約倉位。",
            "color": 15158332,
            "footer": {"text": today + " | 總經數據預警系統・請嚴格控管交易風險"}
        }]
    }
    requests.post(WEBHOOK_URL, json=header)

    if not events:
        requests.post(WEBHOOK_URL, json={"content": "今日無重大數據，市場相對平靜。"})
        return

    for e in events:
        imp = e["impact"]
        name_str = "🕐 " + e["time"] + "　" + e["currency"] + "　" + imp_emoji.get(imp, "⚪")
        value_str = "**" + e["event"] + "**\n前值: `" + e["previous"] + "`　➨　預測: `" + e["forecast"] + "`"
        embed = {
            "embeds": [{
                "color": imp_color.get(imp, 8421504),
                "fields": [{
                    "name": name_str,
                    "value": value_str,
                    "inline": False
                }]
            }]
        }
        requests.post(WEBHOOK_URL, json=embed)
        print("已發送: " + e["event"])

if __name__ == "__main__":
    print("開始抓取財經日曆...")

    # 診斷用：看 API 回傳什麼
    r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15)
    data = r.json()
    print("API 共回傳 " + str(len(data)) + " 筆本週數據")

    today_et = datetime.now(pytz.timezone("America/New_York")).strftime("%m-%d-%Y")
    print("今天美東日期: " + today_et)

    dates = list(set([item.get("date", "") for item in data]))
    print("API 裡有的日期: " + str(dates))

    events = get_calendar()
    print("篩選後找到 " + str(len(events)) + " 筆今日高影響數據")
    send_to_discord(events)
    print("發送完成！")
