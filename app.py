import streamlit as st
import pandas as pd
import datetime
import sqlite3
import json

# -----------------------------------------------------------------------------
# 0. 資料庫讀取邏輯
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

st.title("🐎 專業賽馬智能分析與動態監控儀表板")
st.caption("本地爬蟲引擎 + SQLite 即時同步 | 支援落飛監控與個人筆記庫")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄控制面板
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 即時賠率與排位 (資料庫同步)", "📝 私人晨操與走勢筆記"]
)

# -----------------------------------------------------------------------------
# 3. 主頁面邏輯
# -----------------------------------------------------------------------------

# --- 模組一：即時賠率與排位 ---
if page_mode == "📊 即時賠率與排位 (資料庫同步)":
    st.subheader("🏇 賽日即時賠率監控")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        selected_date = st.date_input("選擇賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])

    date_str = selected_date.strftime("%Y-%m-%d")
    venue_code = "ST" if "沙田" in venue_choice else "HV"

    st.markdown("---")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT race_no, odds_json, update_time FROM race_odds_cache 
            WHERE date_str = ? AND venue = ?
            ORDER BY race_no ASC
        ''', (date_str, venue_code))
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()

    if rows:
        st.success(f"成功連線本地數據庫！最後同步時間：{rows[0][2]}")
        race_list = [f"第 {row[0]} 場" for row in rows]
        selected_race = st.selectbox("選擇查看場次", race_list)
        
        race_num = int(selected_race.replace("第 ", "").replace(" 場", ""))
        
        for row in rows:
            if row[0] == race_num:
                raw_json = json.loads(row[1])
                st.markdown(f"### 📋 {selected_race} 即時賠率數據")
                st.json(raw_json)
                break
    else:
        st.warning("⚠️ 目前資料庫中暫無此日期的即時賠率數據。")
        st.info("💡 **提示**：請確保您電腦中的 `scraper.py` 爬蟲腳本正在背景執行，它會自動將最新賠率寫入 `racing_local.db`。")

# --- 模組二：私人晨操與走勢筆記 ---
elif page_mode == "📝 私人晨操與走勢筆記":
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
