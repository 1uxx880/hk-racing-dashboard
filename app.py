import streamlit as st
import pandas as pd
import requests
import datetime
import sqlite3
import json

# -----------------------------------------------------------------------------
# 0. 初始化本地 SQLite 資料庫（用於儲存筆記與 API 快取）
# -----------------------------------------------------------------------------
def get_db_connection():
    return sqlite3.connect("racing_local.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            horse_name TEXT,
            note TEXT,
            update_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# 1. 頁面基本配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="專業賽馬智能分析系統",
    page_icon="🐎",
    layout="wide"
)

st.title("🐎 專業賽馬智能分析系統 (官方 JSON API 版)")
st.caption("直接對接香港賽馬會官方 API 接口 | 支援即時賠率查詢與私人筆記")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄控制面板
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 官方即時賠率 API 查詢", "🧠 私人晨操與走勢筆記"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Telegram 自動推播")
tg_token = st.sidebar.text_input("Bot Token", type="password", key="tg_token")
tg_chat_id = st.sidebar.text_input("Chat ID", key="tg_chat")

if st.sidebar.button("測試 Telegram 連線"):
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {"chat_id": tg_chat_id, "text": "🐎 賽馬分析系統連線測試成功！"}
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                st.sidebar.success("發送成功！")
            else:
                st.sidebar.error("發送失敗，請檢查設定。")
        except Exception as e:
            st.sidebar.error(f"連線異常: {e}")
    else:
        st.sidebar.warning("請先輸入 Token 與 Chat ID")

# -----------------------------------------------------------------------------
# 3. 核心 API 請求函式
# -----------------------------------------------------------------------------
def fetch_hkjc_json_odds(date_str, venue, race_no):
    """
    透過官方 JSON 接口獲取即時賠率 (WIN/PLA)
    url 格式: https://bet.hkjc.com/racing/getJSON.aspx?type=winplaodds&date=YYYY-MM-DD&venue=ST&raceno=1
    """
    url = f"https://bet.hkjc.com/racing/getJSON.aspx"
    params = {
        "type": "winplaodds",
        "date": date_str,
        "venue": venue,
        "raceno": race_no
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://bet.hkjc.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=6)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"伺服器返回狀態碼: {response.status_code}"
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# 4. 主頁面邏輯
# -----------------------------------------------------------------------------

# --- 模組一：官方即時賠率 API 查詢 ---
if page_mode == "📊 官方即時賠率 API 查詢":
    st.subheader("📡 香港賽馬會 - 即時賠率 API 檢索")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_date = st.date_input("選擇賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])
    with col3:
        race_no = st.number_input("賽事場次", min_value=1, max_value=12, value=1, step=1)

    date_str = selected_date.strftime("%Y-%m-%d")
    venue_code = "ST" if "沙田" in venue_choice else "HV"

    st.markdown("---")

    if st.button("🚀 立即向 HKJC API 提取數據"):
        with st.spinner(f"正在連線至官方 API 獲取 {date_str} 第 {race_no} 場資料..."):
            success, result = fetch_hkjc_json_odds(date_str, venue_code, race_no)
            
            if success:
                st.success("成功取得官方 API 即時數據！")
                
                # 簡單展示回傳的 JSON 結構
                st.json(result)
                
                # 如果回傳的資料包含馬匹賠率陣列，可以嘗試轉為 DataFrame 呈現
                try:
                    # 視官方 JSON 的實際結構進行解析呈現
                    if isinstance(result, dict):
                        st.write("📋 數據摘要解析：")
                        st.write(result)
                except Exception as parse_err:
                    st.info(f"原始 JSON 已展開，結構解析提示: {parse_err}")
            else:
                st.warning(f"⚠️ 無法取得資料：{result}")
                st.info("💡 **小叮嚀**：若當天並非賽馬日，或該場次尚未開售，官方 API 通常會返回空白或錯誤代碼。")

# --- 模組二：私人晨操與走勢筆記 ---
elif page_mode == "🧠 私人晨操與走勢筆記":
    st.subheader("🔥 專業操練與走勢分析筆記")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✍️ 新增觀察筆記")
        user_horse = st.text_input("馬匹名稱 / 馬號", placeholder="例如：金鑽貴人 (1)")
        user_note = st.text_area("記錄內容（如：工夫做足、走勢爽朗、檔位有利）", height=120)
        
        if st.button("儲存筆記"):
            if user_horse and user_note:
                conn = get_db_connection()
                cursor = conn.cursor()
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute("INSERT INTO notes (horse_name, note, update_time) VALUES (?, ?, ?)", 
                               (user_horse, user_note, current_time))
                conn.commit()
                conn.close()
                st.success(f"成功為【{user_horse}】儲存筆記！")
            else:
                st.warning("請填寫馬匹名稱與內容。")

    with col2:
        st.markdown("### 📂 私人筆記庫")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT horse_name, note, update_time FROM notes ORDER BY id DESC")
        all_notes = cursor.fetchall()
        conn.close()

        if all_notes:
            for h_name, n_text, u_time in all_notes:
                with st.expander(f"🐎 {h_name} ({u_time})"):
                    st.write(n_text)
        else:
            st.info("目前尚無儲存的筆記。")
