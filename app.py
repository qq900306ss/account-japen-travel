import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="旅遊開支神助手 V3", layout="wide")
st.title("📊 旅遊開支自動化統計 (全格式相容版)")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("💱 匯率設定")
    rate = st.number_input("日幣兌台幣匯率 (例 0.215)", value=0.215, step=0.001, format="%.3f")
    st.divider()
    st.info("💡 此版本已優化：\n1. 支援「數字+品項」與「品項+數字」。\n2. 自動偵測「台幣」並反推日幣。\n3. 自動排序與天數歸類。")

# --- 強大解析邏輯 ---
def parse_v3(text, exchange_rate):
    data = []
    current_day = "第一天"
    day_order = ["第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天", "第八天", "第九天", "第十天"]

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        # 跳過通訊軟體雜訊
        if not line or any(x in line for x in ["你傳送了", "已編輯", "下午", "上午", "你刪除了"]):
            continue
        
        # 1. 更新天數 (偵測「第幾天開始」或「第幾天」)
        day_match = re.search(r'(第[一二三四五六七八九十\d]+天)', line)
        if day_match:
            current_day = day_match.group(1)
            if len(line) <= 5: continue # 如果整行只有天數就跳過

        # 2. 排除總計行 (避免重複計算)
        if "總共" in line: continue

        # 3. 核心抓取邏輯 (數字在前或在後)
        # 格式 A: 品項1234 (例如：鰻魚飯1740)
        # 格式 B: 1234品項 (例如：6249無印)
        val = None
        item = ""
        
        nums = re.findall(r'\d+', line)
        if nums:
            val = float(nums[-1]) # 抓最後一個數字 (防止日期干擾)
            item = line.replace(str(int(val)), "").strip()
        
        if val and item:
            # 4. 雙向幣別換算
            if "台幣" in item or "臺幣" in item:
                twd = val
                jpy = round(val / exchange_rate, 0)
                item = item.replace("台幣", "").replace("臺幣", "")
            else:
                jpy = val
                twd = round(val * exchange_rate, 0)

            data.append({
                "天數": current_day,
                "項目": item,
                "日幣(JPY)": jpy,
                "台幣(TWD)": twd,
                "sort_idx": day_order.index(current_day) if current_day in day_order else 99
            })
            
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=["sort_idx"]).drop(columns=["sort_idx"])
    return df

# --- 介面呈現 ---
raw_input = st.text_area("請貼上對話內容：", height=400, placeholder="無印6249\n第一天 1740鰻魚飯...")

if raw_input:
    df = parse_v3(raw_input, rate)
    
    if not df.empty:
        total_jpy = df["日幣(JPY)"].sum()
        total_twd = df["台幣(TWD)"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("總計 (日幣)", f"¥ {total_jpy:,.0f}")
        c2.metric("總計 (台幣)", f"$ {total_twd:,.0f}")

        st.subheader("📋 支出清單")
        st.dataframe(df, use_container_width=True)

        # 下載按鈕
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 下載 Excel 表格", output.getvalue(), "旅遊支出統計_V3.xlsx")

        # 圖表
        st.subheader("📊 每日分析")
        fig = px.bar(df.groupby("天數")["日幣(JPY)"].sum().reset_index(), x="天數", y="日幣(JPY)", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("目前還抓不到內容，請確認內容包含「品項+金額」或「金額+品項」。")