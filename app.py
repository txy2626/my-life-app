import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. 基础配置与自修复数据库 ---
UPLOAD_FOLDER = 'life_images'
GALLERY_FOLDER = 'life_gallery' # 新增：精选展板文件夹
for folder in [UPLOAD_FOLDER, GALLERY_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, 
                      mood INTEGER, image_path TEXT, is_featured INTEGER DEFAULT 0)''')
        # 补丁：确保旧数据库有 is_featured 列（用于展板）
        cursor = conn.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_featured' not in columns:
            conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')

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
    percent = min(lived_days / (expectancy * 365), 1.0)
    st.progress(percent)
    st.caption(f"进度: {percent:.2%}")

    if not df_all.empty:
        st.divider()
        st.header("📊 能量看板")
        
        # 统计图表 1：饼图 (维度分布)
        st.subheader("维度比例")
        cate_counts = df_all['category'].value_counts()
        fig1, ax1 = plt.subplots()
        ax1.pie(cate_counts, labels=cate_counts.index, autopct='%1.1f%%', startangle=90, textprops={'color':"grey"})
        ax1.axis('equal')
        fig1.patch.set_alpha(0) # 背景透明
        st.pyplot(fig1)

        # 统计图表 2：趋势图 (日均能量)
        st.subheader("情绪趋势")
        df_all['only_date'] = pd.to_datetime(df_all['date'].str.split(' ').str[0])
        trend_data = df_all.groupby('only_date')['mood'].mean().sort_index()
        fig2, ax2 = plt.subplots()
        ax2.plot(trend_data.index, trend_data.values, marker='o', linestyle='-', color='#FF4B4B')
        ax2.set_ylabel("Mood Level")
        plt.xticks(rotation=45)
        fig2.patch.set_alpha(0)
        st.pyplot(fig2)

# --- 4. 核心功能区 ---
tab1, tab2, tab3 = st.tabs(["✍️ 记录瞬间", "🖼️ 人生展板", "📜 往事回响"])

# --- Tab 1: 记录 ---
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
            is_featured = st.checkbox("设为展板精选 (大图展示)")
        
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
                                 (timestamp, cate, content, mood, img_path, 1 if is_featured else 0))
                st.success("已存档。")
                st.rerun()

# --- Tab 2: 人生展板 (精选集) ---
with tab2:
    st.header("🖼️ 人生精选展板")
    featured_df = df_all[df_all['is_featured'] == 1]
    if not featured_df.empty:
        # 采用网格布局显示大图
        cols = st.columns(3)
        for idx, (_, row) in enumerate(featured_df.iterrows()):
            with cols[idx % 3]:
                if row['image_path'] and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True, caption=row['date'])
                else:
                    st.warning(f"ID:{row['id']} 记录被设为精选但无图片")
                st.write(f"> {row['content'][:50]}...")
    else:
        st.info("尚未勾选任何“精选”记录。在记录时勾选“设为展板精选”即可在此展示。")

# --- Tab 3: 往事回响 (含日期检索) ---
with tab3:
    search_query = st.text_input("🔍 检索内容或日期 (如: 2024-05)")
    display_df = df_all.copy()
    if search_query:
        display_df = display_df[
            (display_df['content'].str.contains(search_query, case=False, na=False)) |
            (display_df['date'].str.contains(search_query, case=False, na=False))
        ]

    for _, row in display_df.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 4])
            with col1:
                if row.get('image_path') and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
            with col2:
                st.write(f"**{row['date']}** | `{row['category']}` | 能量: {row['mood']}⭐")
                new_text = st.text_area("编辑", value=row['content'], key=f"ed_{row['id']}", label_visibility="collapsed")
                b1, b2, b3, _ = st.columns([1, 1, 2, 6])
                if b1.button("更新", key=f"u_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("UPDATE logs SET content=? WHERE id=?", (new_text, row['id']))
                    st.toast("已保存")
                if b2.button("删除", key=f"d_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                    st.rerun()
                # 快速切换精选状态
                current_feat = "⭐ 取消精选" if row['is_featured'] else "🌟 设为精选"
                if b3.button(current_feat, key=f"feat_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("UPDATE logs SET is_featured=? WHERE id=?", (0 if row['is_featured'] else 1, row['id']))
                    st.rerun()
            st.divider()
