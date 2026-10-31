import streamlit as st
import pandas as pd

# 假設這是某一場的排位與基礎數據
st.subheader("🎯 智能揀馬與綜合評分模型")
st.markdown("透過多維度參數（檔位、騎師、晨操評分）自動計算每匹馬的綜合勝算指數。")

# 模擬單場賽事的馬匹數據
race_df = pd.DataFrame({
    "馬號": [1, 2, 3, 4, 5],
    "馬名": ["金鑽貴人", "浪漫勇士", "加州星球", "遨遊氣泡", "直線力進"],
    "檔位": [3, 9, 1, 5, 2],
    "負磅": [135, 133, 128, 126, 123],
    "騎師": ["潘頓", "麥道朗", "艾兆禮", "布文", "巴度"],
    "近期晨操評價": ["大勇", "平穩", "省鏡", "一般", "極佳"]
})

# 讓使用者設定給分權重
st.markdown("### ⚙️ 調整評分權重參數")
col1, col2, col3 = st.columns(3)
with col1:
    w_draw =.slider("檔位利害權重", 1, 10, 5)
with col2:
    w_jockey = st.slider("騎師實力權重", 1, 10, 8)
with col3:
    w_trackwork = st.slider("晨操走勢權重", 1, 10, 9)

# 簡單的自動化評分邏輯（示範）
def calculate_score(row):
    score = 50 # 基礎分
    # 檔位分數（內檔給高分）
    if row["檔位"] <= 4:
        score += (10 * (w_draw / 5))
    # 騎師加分
    if row["騎師"] in ["潘頓", "麥道朗", "布文"]:
        score += (15 * (w_jockey / 5))
    # 晨操加分
    if row["近期晨操評價"] in ["大勇", "極佳"]:
        score += (20 * (w_trackwork / 5))
    elif row["近期晨操評價"] == "省鏡":
        score += (15 * (w_trackwork / 5))
    return round(score, 1)

if not race_df.empty:
    race_df["綜合智能指數"] = race_df.apply(calculate_score, axis=1)
    # 依綜合指數由高到低排序（即自動揀馬推薦排名）
    race_df = race_df.sort_values(by="綜合智能指數", ascending=False).reset_index(drop=True)
    
    st.markdown("### 🏆 AI 智慧揀馬推薦排序")
    st.dataframe(
        race_df.style.highlight_max(subset=["綜合智能指數"], color="#d4edda"),
        use_container_width=True
    )
