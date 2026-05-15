import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TAIWAN_TZ = pytz.timezone("Asia/Taipei")

def get_calendar():
    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.investing.com/economic-calendar/",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "country[]": ["5", "22", "6", "4", "12", "72"],
        "importance[]": ["2", "3"],
        "timeZone": "55",
        "timeFilter": "timeRemain",
        "currentTab": "today",
        "submitFilters": 1,
        "limit_from": 0,
    }
    try:
        r = requests.post(url, headers=headers, data=payload, timeout=15)
        soup = BeautifulSoup(r.json().get("data", ""), "html.parser")
        events = []
        for row in soup.select("tr.js-event-item"):
            try:
                time_el = row.select_one("td.time")
                currency_el = row.select_one("td.flagCur")
                event_el = row.select_one("td.event a")
                forecast_el = row.select_one("td.fore")
                previous_el = row.select_one("td.prev")
                importance = len(row.select("i.redFullBullishIcon"))
                if not event_el or importance < 2:
                    continue
                events.append({
                    "time": time_el.text.strip() if time_el else "--",
                    "currency": currency_el.text.strip() if currency_el else "--",
                    "event": event_el.text.strip(),
                    "importance": importance,
                    "forecast": forecast_el.text.strip() if forecast_el else "--",
                    "previous": previous_el.text.strip() if previous_el else "--",
                })
            except:
                continue
        return events
    except Exception as e:
        print(f"抓取失敗: {e}")
        return []

def send_to_discord(events):
    today = datetime.now(TAIWAN_TZ).strftime("%Y/%m/%d")
    imp_emoji = {3: "🔴 高", 2: "🟡 中"}

    # 標題訊息
    header = {
        "embeds": [{
            "title": "📊 今日高風險總經數據預警",
            "description": f"⚠️ 今日有高影響力數據公布，請留意市場波動，嚴格控管合約倉位。",
            "color": 15158332,
            "footer": {"text": f"{today} | 總經數據預警系統・請嚴格控管交易風險"}
        }]
    }
    requests.post(WEBHOOK_URL, json=header)

    if not events:
        requests.post(WEBHOOK_URL, json={"content": "今日無重大數據，市場相對平靜。"})
        return

    # 每個事件單獨發一則
    for e in events:
        imp_text = imp_emoji.get(e["importance"], "⚪")
        embed = {
            "embeds": [{
                "color": 15158332 if e["importance"] == 3 else 16776960,
                "fields": [
                    {
                        "name": f"🕐 {e['time']}　{e['currency']}　{imp_text}",
                        "value": f"**{e['event']}**\n前值: `{e['previous']}`　➨　預測: `{e['forecast']}`",
                        "inline": False
                    }
                ]
            }]
        }
        requests.post(WEBHOOK_URL, json=embed)

if __name__ == "__main__":
    print("開始抓取財經日曆...")
    events = get_calendar()
    print(f"找到 {len(events)} 筆數據")
    send_to_discord(events)
    print("發送完成！")
