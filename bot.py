# bot.py

import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import asyncio
import os
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))


TAIWAN_TZ = pytz.timezone("Asia/Taipei")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_economic_calendar():
    """從 Investing.com 抓今日財經日曆"""
    url = "https://www.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.investing.com/economic-calendar/",
    }
    
    # 用 API 端點抓數據
    api_url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
    today = datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d")
    
    payload = {
        "country[]": ["5", "22", "6", "4", "12", "72"],  # 美國、英國、歐元區、日本、澳洲、中國
        "importance[]": ["2", "3"],  # 中高重要性
        "timeZone": "55",  # Asia/Taipei
        "timeFilter": "timeRemain",
        "currentTab": "today",
        "submitFilters": 1,
        "limit_from": 0,
    }
    
    try:
        r = requests.post(api_url, headers=headers, data=payload, timeout=15)
        soup = BeautifulSoup(r.json().get("data", ""), "html.parser")
        
        events = []
        rows = soup.select("tr.js-event-item")
        
        for row in rows:
            try:
                time_el = row.select_one("td.time")
                currency_el = row.select_one("td.flagCur")
                importance_els = row.select("i.grayFullBullishIcon, i.redFullBullishIcon")
                event_el = row.select_one("td.event a")
                actual_el = row.select_one("td.act")
                forecast_el = row.select_one("td.fore")
                previous_el = row.select_one("td.prev")
                
                if not event_el:
                    continue
                
                importance = len(row.select("i.redFullBullishIcon"))
                
                events.append({
                    "time": time_el.text.strip() if time_el else "--",
                    "currency": currency_el.text.strip() if currency_el else "--",
                    "event": event_el.text.strip(),
                    "importance": importance,
                    "actual": actual_el.text.strip() if actual_el else "--",
                    "forecast": forecast_el.text.strip() if forecast_el else "--",
                    "previous": previous_el.text.strip() if previous_el else "--",
                })
            except:
                continue
        
        return events
    except Exception as e:
        print(f"抓取失敗: {e}")
        return []

def build_embed(events):
    """把數據做成漂亮的 Discord Embed"""
    today_str = datetime.now(TAIWAN_TZ).strftime("%Y/%m/%d")
    
    embed = discord.Embed(
        title=f"📊 今日高風險總經數據預警",
        description=f"⚠️ 今日有高影響力數據公布，請留意市場波動，嚴格控管合約倉位。",
        color=0xFF0000,
        timestamp=datetime.now(TAIWAN_TZ)
    )
    embed.set_footer(text=f"{today_str} | 總經數據預警系統・請嚴格控管交易風險")
    
    if not events:
        embed.add_field(name="今日無重大數據", value="市場相對平靜", inline=False)
        return embed
    
    importance_emoji = {3: "🔴", 2: "🟡", 1: "⚪"}
    
    for e in events[:15]:  # 最多顯示15筆
        imp = importance_emoji.get(e["importance"], "⚪")
        value = f"前值: `{e['previous']}` ➨ 預測: `{e['forecast']}`"
        if e["actual"] not in ["--", "", " "]:
            value += f"\n**實際: `{e['actual']}`**"
        
        embed.add_field(
            name=f"{e['time']} | {e['currency']} | {imp} | {e['event']}",
            value=value,
            inline=False
        )
    
    return embed

@tasks.loop(hours=24)
async def daily_calendar():
    """每天早上 6:00 台灣時間自動發送"""
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        events = get_economic_calendar()
        # 只保留高重要性（3星）
        high_impact = [e for e in events if e["importance"] >= 2]
        embed = build_embed(high_impact)
        await channel.send(embed=embed)

@daily_calendar.before_loop
async def before_daily():
    """等到早上 6:00 才開始"""
    await bot.wait_until_ready()
    now = datetime.now(TAIWAN_TZ)
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now >= target:
        # 已過今天6點，等到明天
        from datetime import timedelta
        target += timedelta(days=1)
    wait_seconds = (target - now).total_seconds()
    print(f"等待 {wait_seconds/3600:.1f} 小時後發送...")
    await asyncio.sleep(wait_seconds)

@bot.command(name="今日數據", aliases=["data", "cal"])
async def manual_calendar(ctx):
    """手動觸發：!今日數據"""
    await ctx.send("⏳ 抓取中...")
    events = get_economic_calendar()
    embed = build_embed(events)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot 已上線：{bot.user}")
    daily_calendar.start()

bot.run(DISCORD_TOKEN)
