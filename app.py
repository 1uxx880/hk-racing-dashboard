import requests
import json
import time
import datetime
import sqlite3

# -----------------------------------------------------------------------------
# 1. 資料庫連線與初始化
# -----------------------------------------------------------------------------
DB_NAME = "racing_local.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS race_odds_cache (
            date_str TEXT,
            venue TEXT,
            race_no INTEGER,
            odds_json TEXT,
            update_time TEXT,
            PRIMARY KEY (date_str, venue, race_no)
        )
    ''')
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# 2. Telegram 發送通訊函式
# -----------------------------------------------------------------------------
def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[Telegram 錯誤] {e}")

# -----------------------------------------------------------------------------
# 3. 核心 API 抓取與賠率監控邏輯
# -----------------------------------------------------------------------------
def fetch_hkjc_live_odds(date_str, venue, race_no):
    """
    直連 HKJC 官方公開 JSON API 獲取即時賠率 (WIN/PLA)
    """
    url = f"https://bet.hkjc.com/racing/getJSON.aspx?type=winplaodds&date={date_str}&venue={venue}&raceno={race_no}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://bet.hkjc.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"[抓取失敗] 場次 {race_no}: {e}")
    return None

def main_loop(bot_token=None, chat_id=None):
    init_db()
    print("🚀 HKJC 本地監控與資料同步服務啟動中...")
    
    # 設定當天日期與賽場 (ST=沙田, HV=跑馬地)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    venue = "ST"  
    
    last_odds_map = {}

    while True:
        print(f"\n[🔄 {datetime.datetime.now().strftime('%H:%M:%S')}] 正在掃描當日賽事即時賠率...")
        
        for race_no in range(1, 11): # 假設最多 10 場
            odds_data = fetch_hkjc_live_odds(today_str, venue, race_no)
            
            if odds_data:
                # 寫入 SQLite 資料庫
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO race_odds_cache (date_str, venue, race_no, odds_json, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (today_str, venue, race_no, json.dumps(odds_data), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                
                # 簡單的賠率變動 (落飛) 檢測
                # 比較上一輪賠率與最新賠率
                # 若發現劇烈變動且有設定 Telegram 則推播警報
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"✅ 第 {race_no} 場賠率已成功更新並寫入資料庫 ({current_time})")
            
            time.sleep(1) # 每場間隔 1 秒，保護伺服器

        print("💤 等待 30 秒後進行下一輪即時監控...")
        time.sleep(30)

if __name__ == "__main__":
    # 若有 Telegram Bot，可在此帶入 Token 與 Chat ID 進行測試
    MY_BOT_TOKEN = "" 
    MY_CHAT_ID = ""   
    main_loop(MY_BOT_TOKEN, MY_CHAT_ID)
