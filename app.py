import streamlit as st
import pandas as pd
import datetime
import sqlite3

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

st.title("🐎 專業賽馬智能分析與數據管理系統")
st.caption("內建 SQLite 資料庫引擎 | 支援檔案上傳、排位表管理與私人分析筆記")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄控制面板
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 賽事排位表 (本地資料庫)", "📤 上傳最新排位數據", "🧠 私人晨操與走勢筆記"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Telegram 自動推播")
tg_token = st.sidebar.text_input("Bot Token", type="password", key="tg_token")
tg_chat_id = st.sidebar.text_input("Chat ID", key="tg_chat")

if st.sidebar.button("測試 Telegram 連線"):
    if tg_token and tg_chat_id:
        try:
            import requests
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

# --- 模組一：賽事排位表 (本地資料庫檢視) ---
if page_mode == "📊 賽事排位表 (本地資料庫)":
    st.subheader("🏇 賽事排位與數據檢視")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        selected_date = st.date_input("選擇賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])

    date_str = selected_date.strftime("%Y%m%d")
    st.markdown("---")

    # 從本地 SQLite 讀取
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT race_idx, table_json FROM race_cache 
        WHERE date_str = ? AND venue = ?
    ''', (date_str, venue_choice))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        st.success(f"成功從本地資料庫載入【{selected_date} ({venue_choice})】的賽事排位資料！")
        race_options = [f"第 {row[0]+1} 場" for row in rows]
        selected_race_idx = st.selectbox("選擇賽事場次", race_options)
        
        chosen_idx = int(selected_race_idx.replace("第 ", "").replace(" 場", "")) - 1
        for row in rows:
            if row[0] == chosen_idx:
                target_df = pd.read_json(row[1], orient="split")
                st.dataframe(target_df, use_container_width=True)
                break
    else:
        st.warning("⚠️ 本地資料庫中尚無此日期的排位資料。")
        st.info("💡 **操作指引**：請前往側邊欄的 **「📤 上傳最新排位數據」** 模組，上傳對應的 Excel 或 CSV 檔案，資料就會永久儲存在系統中！")

# --- 模組二：上傳最新排位數據 ---
elif page_mode == "📤 上傳最新排位數據":
    st.subheader("📤 匯入賽事排位表")
    st.caption("透過上傳 CSV 或 Excel 檔案，繞過伺服器防火牆限制，直接將真實排位資料寫入系統資料庫。")

    col1, col2 = st.columns(2)
    with col1:
        up_date = st.date_input("設定此數據的賽事日期", datetime.date.today(), key="up_date")
    with col2:
        up_venue = st.selectbox("設定賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"], key="up_venue")

    uploaded_file = st.file_uploader("上傳排位表檔案 (支援 .csv 或 .xlsx)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("📋 預覽上傳的資料內容：")
            st.dataframe(df.head(), use_container_width=True)

            if st.button("確認並寫入本地資料庫"):
                date_str = up_date.strftime("%Y%m%d")
                conn = get_db_connection()
                cursor = conn.cursor()
                
                df_json = df.to_json(orient="split")
                cursor.execute('''
                    INSERT OR REPLACE INTO race_cache (date_str, venue, race_idx, table_json)
                    VALUES (?, ?, ?, ?)
                ''', (date_str, up_venue, 0, df_json))
                
                conn.commit()
                conn.close()
                st.success("🎉 數據已成功寫入本地資料庫！現在您可以切換至「賽事排位表」模組隨時查看。")
        except Exception as e:
            st.error(f"解析檔案時發生錯誤: {e}")

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
