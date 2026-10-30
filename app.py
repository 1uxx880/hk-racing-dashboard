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
            url = "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/RaceCard.aspx"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            
            res = requests.get(url, headers=headers, timeout=8)
            
            if res.status_code == 200:
                dfs = pd.read_html(res.text)
                
                if dfs and len(dfs) > 0:
                    st.success("成功取得 HKJC 官方排位表真實數據！")
                    race_options = [f"第 {i+1} 場" for i in range(len(dfs))]
                    selected_race_idx = st.selectbox("選擇賽事場次", race_options)
                    
                    idx = int(selected_race_idx.replace("第 ", "").replace(" 場", "")) - 1
                    target_df = dfs[idx]
                    
                    st.dataframe(target_df, use_container_width=True)
                else:
                    st.warning("⚠️ 目前該頁面結構中找不到排位表表格。可能當日並非賽馬日，或官方尚未公佈排位。")
            else:
                st.error(f"無法連線至賽馬會伺服器 (狀態碼: {res.status_code})")
        except Exception as e:
            st.warning("目前未能讀取即時排位數據：非賽馬日或網路連線受限。")
            st.info("💡 提示：在非賽馬日期間，您可以切換至下方的「預先報名表」或使用「私人筆記」記錄心水資料。")

# --- 模組二：預先報名表 ---
elif page_mode == "📝 預先報名表 (Entries)":
    st.subheader("📋 賽事預先報名表 (Entries)")
    st.caption("直接提取 HKJC 最新公佈之出賽候選馬匹、評分與優先權資料")

    try:
        url = "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/Entries.aspx"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url,
