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
        today = datetime.now(pytz.timezone("America/New_York")).strftime("%m-%d-%Y")
        
        events = []
        for item in data:
            if item.get("date", "") != today:
                continue
            if item.get("impact", "") not in ["High", "Medium"]:
                continue
            
            # 時間轉換成台灣時間
            try:
                et_time = datetime.strptime(
                    f"{item['date']} {item['time']}", "%m-%d-%Y %I:%M%p"
                )
                et = pytz.timezone("America/New_York")
                et_time = et.localize(et_time)
                tw_time = et_time.astimezone(TAIWAN_TZ).strftime("%H:%M")
            except:
                tw_time = item.get("time", "--")

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
        print(f"抓取失敗: {e}")
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
            "footer": {"text": f"{today} | 總經數據預警系統・請嚴格控管交易風險"}
        }]
    }
    requests.post(WEBHOOK_URL, json=header)

    if not events:
        requests.post(WEBHOOK_URL, json={"content": "今日無重大數據，市場相對平靜。"})
        return

    for e in events:
        imp = e["impact"]
        embed = {
            "embeds": [{
                "color": imp_color.get(imp, 8421504),
                "fields": [{
                    "name": f"🕐 {e['time']}　{e['currency']}　{imp_emoji.get(i
