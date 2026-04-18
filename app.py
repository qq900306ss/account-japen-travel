import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

# --- 網頁配置 ---
st.set_page_config(page_title="日本旅遊記帳助手", layout="wide")

st.title("🇯🇵 旅遊開支自動化統計")
st.info("直接貼上 Line 或對話紀錄，我會自動幫你計算總額與分類。")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 匯率與幣別")
    rate = st.number_input("日幣兌台幣匯率", value=0.215, step=0.001, format="%.3f")
    currency = st.radio("統計顯示幣別", ["日幣 (JPY)", "台幣 (TWD)"])
    st.divider()
    st.caption("小提示：程式會自動排除『你傳送了』、『已編輯』等系統字眼。")

# --- 資料輸入 ---
raw_text = st.text_area("請貼上對話內容：", height=250)

def parse_travel_data(text):
    data = []
    current_day = "未分類"
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or any(x in line for x in ["你傳送了", "已編輯", "下午", "上午", "你刪除了"]):
            continue
            
        # 偵測天數 (例如: 第六天)
        day_match = re.search(r'(第[一二三四五六七八九十\d]+天)', line)
        if day_match:
            current_day = day_match.group(1)
            continue

        # 偵測品項與數字 (例如: 鰻魚飯1740)
        # 排除包含「總共」的行，避免重複計算
        if "總共" in line:
            continue
            
        match = re.search(r'([^\d\s]+)(\d+)', line)
        if match:
            item = match.group(1)
            val = float(match.group(2))
            
            # 簡易自動分類
            category = "其他"
            if any(x in item for x in ["飯", "餐", "吃", "麵", "蕎麥", "鳥貴族", "星巴客", "汁"]):
                category = "餐飲"
            elif any(x in item for x in ["伴手禮", "貼紙", "無印", "gu"]):
                category = "購物"
            elif any(x in item for x in ["門票", "博物館"]):
                category = "景點"
            elif "機票" in item:
                category = "交通"
            elif "住宿" in item:
                category = "住宿"

            data.append({
                "日期": current_day,
                "類別": category,
                "項目": item,
                "日幣": val,
                "台幣": round(val * rate, 0)
            })
    return pd.DataFrame(data)

if raw_text:
    df = parse_travel_data(raw_text)
    
    if not df.empty:
        # --- 計算區 ---
        target_col = "日幣" if "日幣" in currency else "台幣"
        total_amount = df[target_col].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("總支出金額", f"{total_amount:,.0f} {currency[:2]}")
        col2.metric("記錄筆數", f"{len(df)} 筆")
        col3.metric("目前匯率", f"{rate}")

        # --- 圖表區 ---
        st.subheader("📊 統計圖表")
        c1, c2 = st.columns(2)
        
        with c1:
            fig_bar = px.bar(df, x="日期", y=target_col, color="類別", title="每日開銷分佈")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with c2:
            fig_pie = px.pie(df, values=target_col, names='類別', title="支出比例")
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- 表格區 ---
        st.subheader("📄 明細清單")
        st.dataframe(df, use_container_width=True)

        # --- 匯出 Excel ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 下載整理好的 Excel 表格",
            data=output.getvalue(),
            file_name="日本旅遊記帳.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("偵測不到符合格式的內容，請確認內容包含『品項+數字』。")