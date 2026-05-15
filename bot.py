import requests
from datetime import datetime
import pytz
import os

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TAIWAN_TZ = pytz.timezone("Asia/Taipei")

def get_calendar():
    url = "https://economic-calendar.tradingview.com/events"
    today = datetime.now(pytz.timezone("America/New_York"))
    
    params = {
        "from": today.strftime("%Y-%m-%dT00:00:00+0000"),
        "to": today.strftime("%Y-%m-%dT23:59:59+0000"),
        "countries": "US,GB,EU,JP,CN,AU,CA,CH,DE",
        "minImportance": 1,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        print("狀態碼: " + str(r.status_code))
        data = r.json()
        results = data.get("result", [])
        print("回傳 " + str(len(results)) + " 筆數據")
        
        events = []
        for item in results:
            importance = item.get("importance", 0)
            if importance < 1:  # 0=低, 1=中, 2=高
                continue
            
            print("數據: " + str(importance) + " | " + item.get("title","?"))
            
            try:
                dt = datetime.fromisoformat(item.get("date","").replace("Z", "+00:00"))
                tw_time = dt.astimezone(TAIWAN_TZ).strftime("%H:%M")
            except:
                tw_time = "--"
            
            events.append({
                "time": tw_time,
                "currency": item.get("currency", "--"),
                "event": item.get("title", "--"),
                "importance": importance,
                "forecast": str(item.get("forecast_value") or "--"),
                "previous": str(item.get("prev_value") or "--"),
            })
        
        return events
    except Exception as e:
        print("抓取失敗: " + str(e))
        return []

def send_to_discord(events):
    today = datetime.now(TAIWAN_TZ).strftime("%Y/%m/%d")
    imp_emoji = {2: "🔴 高", 1: "🟡 中", 0: "⚪ 低"}
    imp_color = {2: 15158332, 1: 16776960, 0: 8421504}

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
        imp = e["importance"]
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
    events = get_calendar()
    # 只保留中高重要性
    high_events = [e for e in events if e["importance"] >= 1]
    print("篩選後找到 " + str(len(high_events)) + " 筆中高影響數據")
    send_to_discord(high_events)
    print("發送完成！")
