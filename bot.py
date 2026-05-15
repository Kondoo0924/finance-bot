import requests
import datetime
import os
import pytz

# 配置環境變數
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
API_KEY = os.environ.get("FINNHUB_API_KEY") # 記得去 GitHub 設定這個 Secret
TAIWAN_TZ = pytz.timezone("Asia/Taipei")

class EconomicCalendarBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1/calendar/economic"

    def fetch_events(self):
        # 獲取今日日期
        today = datetime.datetime.now(TAIWAN_TZ).strftime('%Y-%m-%d')
        
        params = {
            "token": self.api_key
        }
        
        try:
            # Finnhub 的 API 響應非常快且穩定
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            all_events = data.get('economicCalendar', [])
            
            # 過濾：今日數據、指定國家、重要性
            filtered_events = []
            focus_countries = ["United States", "China", "United Kingdom", "Japan", "Euro Area"]
            
            for item in all_events:
                # 檢查是否為今天且在關注清單內
                if item.get('date', '').split(' ')[0] == today and item.get('country') in focus_countries:
                    filtered_events.append(item)
            
            return filtered_events
        except Exception as e:
            print(f"抓取失敗: {e}")
            return []

    def format_and_send(self, events):
        # 建立你最喜歡的標題格式
        header_payload = {
            "embeds": [{
                "title": "🚨 華爾街日報數據雷達：今日美股預警",
                "description": "✅ 數據源已切換至專業級 Finnhub 節點，確保執行穩定。",
                "color": 15158332,
                "fields": [{"name": "【 今日重點經濟數據 】", "value": "以下為監控到的全球市場重要變動：" if events else "☕ 今日目前無重要美股經濟數據公佈。", "inline": False}],
                "footer": {"text": f"美股預警系統 • {datetime.datetime.now(TAIWAN_TZ).strftime('%Y-%m-%d')} • 數據源：Finnhub"}
            }]
        }
        requests.post(WEBHOOK_URL, json=header_payload)

        # 發送具體數據
        for e in events:
            # Finnhub 的重要性通常是 1-3
            impact = e.get('impact', 'low')
            imp_emoji = {"high": "🔴 高", "medium": "🟡 中", "low": "🔵 低"}
            flag_map = {"United States": "🇺🇸", "China": "🇨🇳", "United Kingdom": "🇬🇧", "Japan": "🇯🇵", "Euro Area": "🇪🇺"}
            
            # 轉換時間
            raw_time = e.get('date', '').split(' ')[1] # 取 HH:MM:SS
            
            field = {
                "embeds": [{
                    "color": 15158332 if impact == 'high' else 16776960,
                    "fields": [{
                        "name": f"⏰ {raw_time[:5]} | {flag_map.get(e.get('country'), '🌐')} | {imp_emoji.get(impact)} | {e.get('event')}",
                        "value": f"└ 📊 前值: `{e.get('prev', '--')}` | 預期: `{e.get('estimate', '--')}`",
                        "inline": False
                    }]
                }]
            }
            requests.post(WEBHOOK_URL, json=field)

if __name__ == "__main__":
    if not API_KEY:
        print("錯誤: 找不到 FINNHUB_API_KEY，請在 GitHub Secrets 中設定。")
    else:
        bot = EconomicCalendarBot(API_KEY)
        events = bot.fetch_events()
        bot.format_and_send(events)
