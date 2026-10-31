import streamlit as st
import pandas as pd
import requests
import datetime
import sqlite3

# -----------------------------------------------------------------------------
# 0. 本地資料庫初始化 (筆記與快取雙重保險)
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

st.title("🐎 專業賽馬智能分析系統 (多源數據抓取版)")
st.caption("具備動態多通道備援機制 | 自動抓取最新賽事排位表與馬匹數據")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄控制面板
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 即時排位表 (多源抓取)", "📝 預先報名表 (Entries)", "🧠 私人晨操與走勢筆記"]
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
# 3. 多源排位表抓取核心邏輯
# -----------------------------------------------------------------------------
def fetch_racecard_multi_source():
    """
    透過偽裝 Request Header 與多通道備援抓取真實排位數據
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://racing.hkjc.com/racing/chinese/"
    }

    # 多個潛在的排位表數據源 / 備用 URL 列表
    candidate_urls = [
        "https://racing.hkjc.com/racing/information/chinese/Racing/RaceCard.aspx",
        "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/RaceCard.aspx",
        "https://racing.hkjc.com/chinese/local/index.asp"
    ]

    for url in candidate_urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                dfs = pd.read_html(res.text)
                # 篩選有效長度的數據表格
                valid_dfs = [df for df in dfs if len(df) > 1]
                if valid_dfs:
                    return True, valid_dfs, f"成功連線自數據源: {url}"
        except Exception:
            continue

    return False, [], "目前所有備援通道均未獲取到有效排位表（可能非賽馬日或未公佈）。"

# -----------------------------------------------------------------------------
# 4. 主頁面邏輯
# -----------------------------------------------------------------------------

# --- 模組一：即時排位表 (多源抓取) ---
if page_mode == "📊 即時排位表 (多源抓取)":
    st.subheader("🏇 賽日排位表 (自動備援抓取)")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_date = st.date_input("賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])
    with col3:
        st.write("")
        st.write("")
        refresh_btn = st.button("🔄 重新線上擷取")

    st.markdown("---")

    with st.spinner("正在透過多重通道獲取最新賽事排位..."):
        success, dfs, msg = fetch_racecard_multi_source()

    if success and dfs:
        st.success(msg)
        race_options = [f"第 {i+1} 場" for i in range(len(dfs))]
        selected_race_idx = st.selectbox("選擇賽事場次", race_options)
        
        chosen_idx = int(selected_race_idx.replace("第 ", "").replace(" 場", "")) - 1
        target_df = dfs[chosen_idx]
        
        st.dataframe(target_df, use_container_width=True)
    else:
        st.warning(f"⚠️ {msg}")
        st.info("💡 **排位表公佈時間提示**：賽馬會通常於比賽前 2 天正式公佈排位（週三賽事前於週一、週末賽事前於週四）。非公佈期時可先利用【私人晨操與走勢筆記】進行分析。")

# --- 模組二：預先報名表 ---
elif page_mode == "📝 預先報名表 (Entries)":
    st.subheader("📋 賽事預先報名表 (Entries)")
    st.caption("自動連線擷取 HKJC 最新公佈之出賽候選馬匹與優先權資料")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    entries_urls = [
        "https://racing.hkjc.com/racing/information/chinese/Racing/Entries.aspx",
        "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/Entries.aspx"
    ]
    
    found = False
    for url in entries_urls:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                dfs = pd.read_html(res.text)
                if dfs:
                    st.success(f"成功提取報名數據 (來源: {url})")
                    st.dataframe(dfs[0], use_container_width=True)
                    found = True
                    break
        except Exception:
            continue
            
    if not found:
        st.info("目前伺服器暫無預先報名表資料（通常於賽前數天公佈）。")

# --- 模組三：私人晨操與走勢筆記 ---
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
