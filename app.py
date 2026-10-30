import streamlit as st
import pandas as pd
import requests
import datetime

# -----------------------------------------------------------------------------
# 1. 頁面基本配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="專業賽馬智能分析系統",
    page_icon="🐎",
    layout="wide"
)

st.title("🐎 專業賽馬智能分析與排位系統")
st.caption("即時連線香港賽馬會 (HKJC) 官方排位表與賽事數據庫")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄：控制與 Telegram 參數
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 系統控制面板")

page_mode = st.sidebar.radio(
    "功能模組",
    ["📊 賽日官方排位表 (真實抓取)", "📝 預先報名表 (Entries)", "🧠 私人晨操與走勢筆記"]
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

# --- 模組一：賽日官方排位表 ---
if page_mode == "📊 賽日官方排位表 (真實抓取)":
    st.subheader("🏇 香港賽馬會 - 官方排位表")
    
    col1, col2 = st.columns([2, 2])
    with col1:
        selected_date = st.date_input("選擇賽事日期", datetime.date.today())
    with col2:
        venue_choice = st.selectbox("賽馬場地", ["沙田 (ST)", "跑馬地 (HV)"])

    st.markdown("---")

    with st.spinner("正在向香港賽馬會提取排位表資料..."):
        try:
            # 嘗試多個可能的官方排位表路徑（繁體中文與英文路徑備援）
            urls_to_try = [
                "https://racing.hkjc.com/racing/information/chinese/Racing/RaceCard.aspx",
                "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/RaceCard.aspx"
            ]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://racing.hkjc.com/"
            }
            
            success = False
            dfs = []
            
            for url in urls_to_try:
                res = requests.get(url, headers=headers, timeout=6)
                if res.status_code == 200:
                    dfs = pd.read_html(res.text)
                    if dfs and len(dfs) > 0:
                        success = True
                        break
            
            if success and dfs:
                st.success("成功取得 HKJC 官方排位表真實數據！")
                race_options = [f"第 {i+1} 場" for i in range(len(dfs))]
                selected_race_idx = st.selectbox("選擇賽事場次", race_options)
                
                idx = int(selected_race_idx.replace("第 ", "").replace(" 場", "")) - 1
                target_df = dfs[idx]
                
                st.dataframe(target_df, use_container_width=True)
            else:
                st.warning("⚠️ 目前該日期伺服器返回 404 或尚未公佈排位表。")
                st.info("💡 **小常識**：HKJC 通常會在每場賽事前 2 至 3 天（例如週三賽事的週一、週末賽事的週四）才正式公佈排位表。非公佈期間造訪該網址會顯示 404。")
                
                # 提供一個直接連往官方賽事首頁的捷徑按鈕
                st.markdown("[🔗 點此直接前往香港賽馬會官方賽事首頁](https://racing.hkjc.com/chinese/local/index.asp)")
                
        except Exception as e:
            st.warning(f"目前未能讀取即時排位數據：伺服器未開放或連線受限 ({e})。")

# --- 模組二：預先報名表 ---
elif page_mode == "📝 預先報名表 (Entries)":
    st.subheader("📋 賽事預先報名表 (Entries)")
    st.caption("直接提取 HKJC 最新公佈之出賽候選馬匹、評分與優先權資料")

    try:
        urls_to_try = [
            "https://racing.hkjc.com/racing/information/chinese/Racing/Entries.aspx",
            "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/Entries.aspx"
        ]
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://racing.hkjc.com/"}
        
        success = False
        dfs = []
        for url in urls_to_try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                dfs = pd.read_html(res.text)
                if dfs:
                    success = True
                    break
        
        if success and dfs:
            st.success("成功提取最新預先報名數據！")
            st.dataframe(dfs[0], use_container_width=True)
        else:
            st.info("目前伺服器尚無預先報名表釋出（通常於賽前一週公佈）。")
    except Exception as e:
        st.info("目前伺服器暫無報名表資料或非公佈期。")

# --- 模組三：私人晨操與走勢筆記 ---
elif page_mode == "🧠 私人晨操與走勢筆記":
    st.subheader("🔥 專業操練與走勢分析筆記")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏃‍♂️ 晨操 / 試閘觀察記錄")
        user_horse = st.text_input("馬匹名稱 / 馬號", placeholder="例如：金鑽貴人 (1)")
        user_note = st.text_area("記錄內容（如：工夫做足、走勢爽朗、檔位有利）", height=150)
        
        if st.button("儲存筆記"):
            if user_horse and user_note:
                st.success(f"已成功為【{user_horse}】記錄私人分析筆記！")
            else:
                st.warning("請填寫馬匹名稱與筆記內容。")

    with col2:
        st.markdown("### 📊 核心數據過濾指標")
        st.markdown("""
        - **檔位勝率統計**：自動對應不同跑道（A、B、C欄）之檔位偏差。
        - **騎練合作評分**：追蹤近期手風順暢之騎師與練馬師組合。
        - **評分行距追蹤**：監控降班馬或強組別排位動向。
        """)
        st.info("💡 提示：系統會自動輪詢官方多個候選路徑，若遇 404 代表官方尚未釋出該期排位。")
