import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 数据库初始化 ---
conn = sqlite3.connect('my_life.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS logs 
             (date TEXT, category TEXT, content TEXT, mood INTEGER)''')
conn.commit()

# --- 核心逻辑 ---
st.set_page_config(page_title="虚无之镜", layout="wide")
st.title("🕯️ 虚无之镜：人生存根")

# 侧边栏：人生进度条
st.sidebar.header("⏳ 寿命沙漏")
birth_date = st.sidebar.date_input("你的生日", datetime(2000, 1, 1))
expectancy = st.sidebar.slider("预期寿命", 60, 120, 85)
total_days = expectancy * 365
lived_days = (datetime.now().date() - birth_date).days
progress = min(lived_days / total_days, 1.0)
st.sidebar.progress(progress)
st.sidebar.write(f"你已走完人生的 {progress:.2%}，剩余 {total_days - lived_days} 天。")

# 主界面：记录
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ 刻下瞬间")
    category = st.selectbox("维度", ["重要里程碑", "碎碎念", "灵感闪现", "至暗时刻"])
    mood = st.select_slider("情绪能量值", options=range(1, 11), value=5)
    content = st.text_area("发生了什么？", placeholder="记录这一刻的真实...")
    
    if st.button("封存入库"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO logs VALUES (?, ?, ?, ?)", (now, category, content, mood))
        conn.commit()
        st.success("已存档。")

with col2:
    st.subheader("📜 往事回响")
    data = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    if not data.empty:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("这里还是一片虚无。")

# 底部：可视化
if not data.empty:
    st.divider()
    st.subheader("📈 情绪波动走势")
    st.line_chart(data.set_index('date')['mood'])
