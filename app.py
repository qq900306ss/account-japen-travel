import streamlit as st
import pandas as pd
import re
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="旅遊記帳分析助手", layout="wide")

st.title("📊 旅遊開支自動化統計工具")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("💱 匯率與幣別設定")
    rate = st.number_input("日幣兌台幣匯率 (例 0.215)", value=0.215, step=0.001, format="%.3f")
    st.divider()
    st.write("💡 **邏輯說明：**")
    st.write("1. 預設天數為 **第一天**。")
    st.write("2. 自動排除「你傳送了」、「總共」等雜訊。")
    st.write("3. 若偵測到「台幣/臺幣」，會自動反推日幣金額。")

# --- 解析核心邏輯 ---
def parse_travel_data(text, exchange_rate):
    data = []
    # 預設從第一天開始
    current_day_str = "第一天"
    
    # 用於排序的映射
    day_map = {"第一天": 1, "第二天": 2, "第三天": 3, "第四天": 4, "第五天": 5, "第六天": 6, "第七天": 7, "第八天": 8}

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or any(x in line for x in ["你傳送了", "已編輯", "下午", "上午", "你刪除了"]):
            continue
            
        # 1. 更新目前天數 (偵測「第六天」或「第一天」)
        day_match = re.search(r'(第[一二三四五六七八九十\d]+天)', line)
        if day_match:
            current_day_str = day_match.group(1)
            # 如果這行只有寫「第六天」，就跳過不抓品項
            if len(line) <= 4:
                continue

        # 2. 判斷是否為總計行 (排除掉「總共16541」這類會導致重複計算的行)
        if "總共" in line:
            continue

        # 3. 抓取品項與數字 (格式：品項1234)
        match = re.search(r'([^\d\s]+)(\d+)', line)
        if match:
            item = match.group(1)
            raw_val = float(match.group(2))
            
            # 4. 判斷幣別 (如果品項包含台幣/臺幣，則將其視為台幣，反推日幣)
            if "台幣" in item or "臺幣" in item:
                twd = raw_val
                jpy = round(raw_val / exchange_rate, 0)
                item = item.replace("台幣", "").replace("臺幣", "") # 清除字眼
            else:
                jpy = raw_val
                twd = round(raw_val * exchange_rate, 0)

            data.append({
                "排序": day_map.get(current_day_str, 99),
                "日期": current_day_str,
                "項目": item,
                "日幣(JPY)": jpy,
                "台幣(TWD)": twd
            })
            
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=["排序"]).drop(columns=["排序"])
    return df

# --- 介面呈現 ---
raw_text = st.text_area("請貼上對話紀錄內容：", height=300, placeholder="直接貼上即可，一開始沒寫也會自動歸為第一天...")

if raw_text:
    df = parse_travel_data(raw_text, rate)
    
    if not df.empty:
        # 指標卡
        total_jpy = df["日幣(JPY)"].sum()
        total_twd = df["台幣(TWD)"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("總支出 (日幣)", f"¥ {total_jpy:,.0f}")
        c2.metric("總支出 (台幣)", f"$ {total_twd:,.0f}")

        # 分頁顯示
        t1, t2, t3 = st.tabs(["📊 統計圖表", "📋 明細表格", "📥 導出 Excel"])
        
        with t1:
            # 每日統計圖
            daily_sum = df.groupby("日期")["日幣(JPY)"].sum().reset_index()
            # 重新按天數排序圖表
            day_order = ["第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天"]
            daily_sum['日期'] = pd.Categorical(daily_sum['日期'], categories=day_order, ordered=True)
            daily_sum = daily_sum.sort_values('日期')
            
            fig = px.bar(daily_sum, x="日期", y="日幣(JPY)", title="每日開支總額 (日幣)", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # 項目佔比圖
            fig_pie = px.pie(df, values="日幣(JPY)", names="項目", title="支出項目比例")
            st.plotly_chart(fig_pie, use_container_width=True)

        with t2:
            st.dataframe(df, use_container_width=True)

        with t3:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("點此下載 Excel 檔案", output.getvalue(), "旅遊花費統計.xlsx")
    else:
        st.info("尚未偵測到有效的花費數據。請確認格式為『品項名稱+金額』。")