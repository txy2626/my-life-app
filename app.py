import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. 基础配置与自修复数据库 ---
UPLOAD_FOLDER = 'life_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """全自动修复数据库：检测缺失列并补齐"""
    with get_connection() as conn:
        # 创建基础表
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, mood INTEGER)''')
        
        # 检查并补齐 image_path 和 is_featured 列
        cursor = conn.execute("PRAGMA table_info(logs)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        if 'image_path' not in existing_columns:
            conn.execute('ALTER TABLE logs ADD COLUMN image_path TEXT DEFAULT ""')
        if 'is_featured' not in existing_columns:
            conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')
        conn.commit()

# --- 2. 页面设置 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

# 读取数据
with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)

# --- 3. 侧边栏：人生画布与可视化统计 ---
with st.sidebar:
    st.header("⏳ 人生画布")
    birth = st.date_input("你的生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    lived_days = (datetime.now().date() - birth).days
    total_days = expectancy * 365
    percent = min(lived_days / total_days, 1.0)
    st.progress(percent)
    st.caption(f"已渡过 {lived_days} 天 | 进度: {percent:.2%}")

    if not df_all.empty:
        st.divider()
        st.header("📊 能量看板")
        
        # 饼图
        try:
            cate_counts = df_all['category'].value_counts()
            fig1, ax1 = plt.subplots(figsize=(5,5))
            ax1.pie(cate_counts, labels=cate_counts.index, autopct='%1.1f%%', startangle=90)
            fig1.patch.set_alpha(0)
            st.pyplot(fig1)
        except: st.write("数据不足以生成比例图")

        # 趋势图
        try:
            df_trend = df_all.copy()
            df_trend['only_date'] = pd.to_datetime(df_trend['date'].str.split(' ').str[0])
            trend_data = df_trend.groupby('only_date')['mood'].mean().sort_index()
            fig2, ax2 = plt.subplots(figsize=(5,3))
            ax2.plot(trend_data.index, trend_data.values, marker='o', color='#FF4B4B')
            plt.xticks(rotation=45)
            fig2.patch.set_alpha(0)
            st.pyplot(fig2)
        except: st.write("数据不足以生成趋势图")

# --- 4. 核心功能区 ---
tab1, tab2, tab3 = st.tabs(["✍️ 记录瞬间", "🖼️ 人生展板", "📜 往事回响"])

with tab1:
    with st.form("new_entry", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            content = st.text_area("记录此刻...", height=150)
            uploaded_file = st.file_uploader("上传照片", type=['png', 'jpg', 'jpeg'])
        with c2:
            cate = st.selectbox("分类", ["日常", "重要里程碑", "灵感闪现", "至暗时刻", "旅行"])
            mood = st.select_slider("能量", options=range(1, 11), value=5)
            manual_date = st.date_input("日期", datetime.now())
            is_feat = st.checkbox("设为展板精选")
        
        if st.form_submit_button("封存入库"):
            if content:
                timestamp = manual_date.strftime('%Y-%m-%d') + " " + datetime.now().strftime('%H:%M')
                img_path = ""
                if uploaded_file is not None:
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    img_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(img_path, "wb") as f: f.write(uploaded_file.getbuffer())
                
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)", 
                                 (timestamp, cate, content, mood, img_path, 1 if is_feat else 0))
                st.success("已存档。")
                st.rerun()

with tab2:
    st.header("🖼️ 人生精选展板")
    featured_df = df_all[df_all['is_featured'] == 1]
    if not featured_df.empty:
        cols = st.columns(3)
        for idx, (_, row) in enumerate(featured_df.iterrows()):
            with cols[idx % 3]:
                if row.get('image_path') and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
                st.caption(f"{row['date']} | {row['content'][:30]}...")
    else:
        st.info("勾选记录中的“精选”即可在此展示。")

with tab3:
    search = st.text_input("🔍 检索内容或日期")
    display_df = df_all.copy()
    if search:
        display_df = display_df[(display_df['content'].str.contains(search, na=False)) | (display_df['date'].str.contains(search, na=False))]

    for _, row in display_df.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 4])
            with col1:
                if row.get('image_path') and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
            with col2:
                st.write(f"**{row['date']}** | {row['category']} | 能量: {row['mood']}⭐")
                st.info(row['content'])
                if st.button("删除记录", key=f"del_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                    st.rerun()
            st.divider()
