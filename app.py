import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import time

# -----------------------------------------------------------------------------
# 1. 頁面基本配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="HKJC 賽馬智能分析儀表板 (SmartRacer 增強版)",
    page_icon="🐎",
    layout="wide"
)

st.title("🐎 HKJC 賽馬智能分析儀表板")
st.caption("整合香港賽馬會排位/報名表數據 + SmartRacer 走勢與晨操分析模組")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 側邊欄：控制與數據抓取設定
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 控制面板")

# 功能分頁切換
page_mode = st.sidebar.radio(
    "選擇查看模組",
    ["📊 賽日即時排位與賠率", "📝 下次賽事報名表", "🔥 SmartRacer 獨家分析指數"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Telegram 自動推播")
tg_token = st.sidebar.text_input("Bot Token", type="password", key="tg_token")
tg_chat_id = st.sidebar.text_input("Chat ID", key="tg_chat")

if st.sidebar.button("測試 Telegram 連線"):
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {"chat_id": tg_chat_id, "text": "🐎 SmartRacer HKJC 儀表板連線測試成功！"}
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
# 3. 數據抓取模組 (HKJC Scraping Helper)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)  # 快取 5 分鐘，避免過度請求 HKJC 伺服器
def fetch_hkjc_racecard():
    """
    抓取 HKJC 官方即時排位表
    """
    url = "https://racing.hkjc.com/racing/info/racing/chinese/racinginfo/RaceCard.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 解析排位表 logic（此處示範數據結構）
            # 實際可使用 BeautifulSoup 解析 .table_bd 內的馬匹資料
            return True, soup
    except Exception as e:
        return False, str(e)
    return False, "無法連線至 HKJC"

# -----------------------------------------------------------------------------
# 4. 主頁面邏輯分頁
# -----------------------------------------------------------------------------

# --- 分頁一：賽日即時排位與賠率 ---
if page_mode == "📊 賽日即時排位與賠率":
    st.subheader("🏇 今日賽事排位與即時賠率監控")
    
    col_race, col_btn = st.columns([3, 1])
    with col_race:
        selected_race = st.selectbox("選擇場次", [f"第 {i} 場" for i in range(1, 12)])
    with col_btn:
        st.write("")
        st.write("")
        refresh_btn = st.button("🔄 立即更新 HKJC 賠率")

    # 模擬/解析獲得的當前場次排位資料（含 SmartRacer 評分元素）
    mock_race_data = pd.DataFrame({
        "馬號": [1, 2, 3, 4, 5, 6],
        "馬名": ["金鑽貴人", "浪漫勇士", "加州星球", "遨遊氣泡", "直線力進", "維港智能"],
        "檔位": [3, 7, 2, 5, 1, 8],
        "負磅": [135, 133, 128, 126, 123, 120],
        "騎師": ["潘頓", "麥道朗", "艾兆禮", "布文", "巴度", "田泰安"],
        "練馬師": ["文家良", "沈集成", "告東尼", "姚本輝", "方嘉柏", "沈集成"],
        "獨贏賠率": [2.2, 3.5, 6.8, 9.1, 15.0, 22.0],
        "賠率走勢": ["📉 綠字熱門", "➡️ 穩定", "📈 獨贏落冷", "📉 大戶回落", "➡️ 穩定", "➡️ 穩定"],
        "SmartRacer 晨操指數": [92, 88, 85, 79, 90, 74]
    })

    st.dataframe(
        mock_race_data.style.highlight_max(subset=["SmartRacer 晨操指數"], color="#d4edda")
                            .highlight_min(subset=["獨贏賠率"], color="#f8d7da"),
        use_container_width=True
    )
    
    st.info(f"🕒 數據最後同步時間：{datetime.datetime.now().strftime('%H:%M:%S')}")

# --- 分頁二：下次賽事報名表 ---
elif page_mode == "📝 下次賽事報名表":
    st.subheader("📋 下次賽事預先報名表 (Entries)")
    st.caption("預先掌握報名馬匹狀態、優先權及班次分佈")

    mock_entries_data = pd.DataFrame({
        "馬名": ["超相當", "開心勇駒", "幸運有您", "包裝必勝", "美麗同享"],
        "烙號": ["J102", "H332", "G118", "H055", "E054"],
        "國際評分": [80, 75, 105, 98, 112],
        "報名班次": ["第三班 (1200米)", "第三班 (1200米)", "第一班 (1400米)", "第二班 (1200米)", "第一班 (1400米)"],
        "優先權/狀態": ["優先報名", "保護馬匹", "優先報名", "後備 1", "優先報名"],
        "練馬師": ["蔡約翰", "伍鵬志", "羅富全", "呂健威", "告東尼"]
    })

    st.dataframe(mock_entries_data, use_container_width=True)

# --- 分頁三：SmartRacer 獨家分析指數 ---
elif page_mode == "🔥 SmartRacer 獨家分析指數":
    st.subheader("🧠 SmartRacer 特色分析數據庫")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏃‍♂️ 近期晨操 / 試閘走勢焦點")
        st.markdown("""
        - **金鑽貴人 (1號)**：10/28 泥地試閘 1200 米全程扣緊，末段衝刺極佳，狀態大勇。
        - **直線力進 (5號)**：草地大跳 800 米，步幅開揚，暗火湧現，值得留意落冷。
        - **加州星球 (3號)**：晨操稍顯緊張，臨場需觀察入閘前汗濕情況。
        """)

    with col2:
        st.markdown("### 🤝 騎練合作黃金勝率")
        st.markdown("""
        - **潘頓 × 文家良**：近 10 次合作 **勝率 40%**，上名率 70%
        - **麥道朗 × 沈集成**：大賽日合作 **勝率 35%**
        - **布文 × 姚本輝**：同程同班合作 **勝率 28%**
        """)

    st.markdown("---")
    st.markdown("### 🚨 大戶異常賠率變動警告 (SmartRacer 監控)")
    st.warning("⚠️ **[第 1 場 4號 遨遊氣泡]** 獨贏賠率由 12.0 瞬間過區下壓至 9.1，請密切留意臨場 Telegram 提示！")
