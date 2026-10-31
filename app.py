import streamlit as st
import pandas as pd
import requests
import datetime
import sqlite3
import json

# -----------------------------------------------------------------------------
# 0. 初始化本地 SQLite 資料庫
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("racing_local.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 建立排位表快取表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS race_cache (
            date_str TEXT,
            venue TEXT,
            race_idx INTEGER,
            table_json TEXT,
            PRIMARY KEY (date_str, venue, race_idx)
        )
    ''')
    # 建立私人筆記表
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

st.title("🐎 專業賽馬智能分析與本地快取系統")
st.caption("內建 SQLite 資料庫引擎 | 支援離線快取、排位表追蹤與私人筆記")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄：控制與 Telegram 參數
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 官方排位表 (智慧快取)", "📝 預先報名表 (Entries)", "🧠 私人晨操與走勢筆記"]
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
# 3. 主頁面邏輯
# -----------------------------------------------------------------------------

# --- 模組一：官方排位表 (智慧快取) ---
if page_mode == "📊 官方排位表 (智慧快取)":
    st.subheader("🏇 香港賽馬會 - 官方排位表 (離線安全快取機制)")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_date = st.date_input("選擇賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])
    with col3:
        st.write("")
        st.write("")
        force_refresh = st.button("🔄 強制聯網更新")

    date_str = selected_date.strftime("%Y%m%d")
    st.markdown("---")

    target_df = None
    fetch_success = False

    # 嘗試從網路抓取
    if force_refresh:
        with st.spinner("正在強制連接 HKJC 伺服器更新數據..."):
            try:
                urls = [
                    "https://racing.hkjc.com/racing/information/chinese/Racing/RaceCard.aspx",
                    "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/RaceCard.aspx"
                ]
                headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://racing.hkjc.com/"}
                
                for url in urls:
                    res = requests.get(url, headers=headers, timeout=6)
                    if res.status_code == 200:
                        dfs = pd.read_html(res.text)
                        if dfs and len(dfs) > 0:
                            fetch_success = True
                            # 將抓到的所有場次存入 SQLite 快取
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            for idx, df in enumerate(dfs):
                                df_json = df.to_json(orient="split")
                                cursor.execute('''
                                    INSERT OR REPLACE INTO race_cache (date_str, venue, race_idx, table_json)
                                    VALUES (?, ?, ?, ?)
                                ''', (date_str, venue_choice, idx, df_json))
                            conn.commit()
                            conn.close()
                            st.success("成功從官網抓取最新排位並已寫入本地資料庫！")
                            break
            except Exception as e:
                st.warning(f"聯網更新失敗 ({e})，將自動讀取本地資料庫快取。")

    # 如果沒有強制更新，或聯網失敗，嘗試從本地 SQLite 讀取
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT race_idx, table_json FROM race_cache 
        WHERE date_str = ? AND venue = ?
    ''', (date_str, venue_choice))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # 本地快取有資料
        st.info(f"📂 目前顯示的是來自【本地 SQLite 快取】的賽事資料。")
        race_options = [f"第 {row[0]+1} 場" for row in rows]
        selected_race_idx = st.selectbox("選擇賽事場次", race_options)
        
        chosen_idx = int(selected_race_idx.replace("第 ", "").replace(" 場", "")) - 1
        for row in rows:
            if row[0] == chosen_idx:
                target_df = pd.read_json(row[1], orient="split")
                st.dataframe(target_df, use_container_width=True)
                break
    else:
        st.warning("⚠️ 本地資料庫與官網目前皆無此日期的排位表快取。")
        st.info("💡 **提示**：非賽馬日或官方尚未公佈排位時將顯示此訊息。您可以點擊上方【強制聯網更新】或切換至【私人晨操筆記】記錄資料。")

# --- 模組二：預先報名表 ---
elif page_mode == "📝 預先報名表 (Entries)":
    st.subheader("📋 賽事預先報名表 (Entries)")
    st.caption("直接提取 HKJC 最新公佈之出賽候選馬匹、評分與優先權資料")

    try:
        url = "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/Entries.aspx"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            dfs = pd.read_html(res.text)
            if dfs:
                st.success("成功提取最新預先報名數據！")
                st.dataframe(dfs[0], use_container_width=True)
            else:
                st.info("目前尚無有效的報名表數據釋出。")
        else:
            st.error("伺服器暫無報名表資料（404 或非公佈期）。")
    except Exception as e:
        st.info("目前伺服器暫無報名表資料。")

# --- 模組三：私人晨操與走勢筆記 ---
elif page_mode == "🧠 私人晨操與走勢筆記":
    st.subheader("🔥 專業操練與走勢分析筆記 (持久化資料庫)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✍️ 新增觀察筆記")
        user_horse = st.text_input("馬匹名稱 / 馬號", placeholder="例如：金鑽貴人 (1)")
        user_note = st.text_area("記錄內容（如：工夫做足、走勢爽朗、檔位有利）", height=120)
        
        if st.button("儲存至本地資料庫"):
            if user_horse and user_note:
                conn = get_db_connection()
                cursor = conn.cursor()
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute("INSERT INTO notes (horse_name, note, update_time) VALUES (?, ?, ?)", 
                               (user_horse, user_note, current_time))
                conn.commit()
                conn.close()
                st.success(f"成功將【{user_horse}】的筆記存入本地資料庫！")
            else:
                st.warning("請完整填寫馬匹名稱與筆記內容。")

    with col2:
        st.markdown("### 📂 已儲存的私人筆記列表")
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
