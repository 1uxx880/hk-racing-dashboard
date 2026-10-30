import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import datetime

# 頁面基本設定
st.set_page_config(
    page_title="HKJC 賽馬智能儀表板",
    page_icon="🐎",
    layout="wide"
)

st.title("🐎 香港賽馬會 (HKJC) 即時賽馬分析儀表板")
st.markdown("---")

# 側邊欄設定
st.sidebar.header("⚙️ 系統控制面板")
auto_refresh = st.sidebar.checkbox("開啟自動重新整理 (模擬)", value=False)
refresh_interval = st.sidebar.slider("重新整理頻率 (秒)", 10, 60, 30)

# Telegram 推播設定區
st.sidebar.markdown("---")
st.sidebar.subheader("📢 Telegram 通知設定")
tg_token = st.sidebar.text_input("Bot Token", type="password")
tg_chat_id = st.sidebar.text_input("Chat ID")

if st.sidebar.button("測試發送 Telegram 訊息"):
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {"chat_id": tg_chat_id, "text": "🐎 HKJC 儀表板連線測試成功！"}
            res = requests.post(url, json=payload)
            if res.status_code == 200:
                st.sidebar.success("推播成功！")
            else:
                st.sidebar.error("推播失敗，請檢查 Token 與 Chat ID。")
        except Exception as e:
            st.sidebar.error(f"發生錯誤: {e}")
    else:
        st.sidebar.warning("請先輸入 Bot Token 與 Chat ID")

# 主頁面內容：模擬賽馬數據與即時賠率
st.subheader("📊 即時賠率與賽事追蹤")

# 模擬一個賽事資料表格
data = {
    "場次": ["第 1 場", "第 1 場", "第 1 場", "第 2 場", "第 2 場"],
    "馬號": [1, 2, 3, 1, 5],
    "馬名": ["金鑽貴人", "浪漫勇士", "加州星球", "遨遊氣泡", "直線力進"],
    "獨贏賠率": [2.5, 3.8, 6.2, 4.1, 12.0],
    "位置賠率": [1.3, 1.5, 2.1, 1.6, 3.5],
    "狀態": ["正常", "正常", "臨場變動", "正常", "熱門急升"]
}

df = pd.DataFrame(data)

# 顯示表格
st.dataframe(df, use_container_width=True)

# 顯示最後更新時間
current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.info(f"🕒 資料最後更新時間: {current_time}")

# 簡易即時刷新模擬
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
