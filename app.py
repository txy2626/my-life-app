import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. 环境配置与文件夹创建 ---
folders = ['life_images', 'life_gallery', 'life_plans']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        # 记录表
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, 
                      mood INTEGER, image_path TEXT, is_featured INTEGER DEFAULT 0)''')
        # 展板表
        conn.execute('''CREATE TABLE IF NOT EXISTS gallery 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, title TEXT, image_path TEXT)''')
        # 计划表
        conn.execute('''CREATE TABLE IF NOT EXISTS plans 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, title TEXT, details TEXT, image_path TEXT)''')
        
        # 自动补齐缺失列
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'is_featured' not in cols:
            conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')

# --- 2. 页面配置与数据读取 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    df_gallery = pd.read_sql_query("SELECT * FROM gallery ORDER BY date DESC", conn)
    df_plans = pd.read_sql_query("SELECT * FROM plans ORDER BY id DESC", conn)

# --- 3. 侧边栏：人生画布与原生统计 ---
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
        
        # 心情走势：原生折线图 (第一版形式)
        st.subheader("心情走势")
        chart_df = df_all.copy()
        chart_df['date'] = pd.to_datetime(chart_df['date'])
        chart_data = chart_df.groupby(chart_df['date'].dt.date)['mood'].mean()
        st.line_chart(chart_data)

        # 维度分布：饼图
        st.subheader("维度占比")
        cate_counts = df_all['category'].value_counts()
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(cate_counts, labels=cate_counts.index, autopct='%1.1f%%', startangle=90)
        fig.patch.set_alpha(0)
        st.pyplot(fig)

st.title("🕯️ 虚无之镜：人生存根")

# --- 4. 核心功能标签页 ---
tab1, tab2, tab3, tab4 = st.tabs(["✍️ 记录瞬间", "🖼️ 人生展板", "🚀 人生计划", "📜 往事回响"])

# --- Tab 1: 记录瞬间 ---
with tab1:
    with st.form("new_log", clear_on_submit=True):
        col_a, col_b = st.columns([2,1])
        with col_a:
            content = st.text_area("此刻在想什么？", height=150)
            pic = st.file_uploader("记录配图", type=['jpg','png','jpeg'], key="log_up")
        with col_b:
            cat = st.selectbox("分类", ["日常", "里程碑", "灵感", "至暗", "旅行"])
            val = st.select_slider("能量", range(1,11), 5)
            is_feat = st.checkbox("设为展板精选")
        
        if st.form_submit_button("封存入库"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join('life_images', f"LOG_{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, 1 if is_feat else 0))
                st.rerun()

# --- Tab 2: 人生展板 (支持同步+上传) ---
with tab2:
    st.header("🖼️ 精选瞬间")
    with st.expander("➕ 直接上传照片至展板"):
        with st.form("gal_up", clear_on_submit=True):
            g_pic = st.file_uploader("选择照片", type=['jpg','png','jpeg'])
            g_title = st.text_input("描述")
            if st.form_submit_button("上传"):
                if g_pic:
                    g_path = os.path.join('life_gallery', f"GAL_{datetime.now().timestamp()}.jpg")
                    with open(g_path, "wb") as f: f.write(g_pic.getbuffer())
                    with get_connection() as conn:
                        conn.execute("INSERT INTO gallery (date, title, image_path) VALUES (?,?,?)",
                                     (datetime.now().strftime('%Y-%m-%d'), g_title, g_path))
                    st.rerun()
    st.divider()
    logs_feat = df_all[df_all['is_featured'] == 1].rename(columns={'content': 'title'})
    combined = pd.concat([df_gallery, logs_feat[['date', 'title', 'image_path']]], ignore_index=True)
    combined = combined.sort_values(by='date', ascending=False)
    if not combined.empty:
        cols = st.columns(3)
        for i, row in enumerate(combined.iterrows()):
            r = row[1]
            with cols[i % 3]:
                if r['image_path'] and os.path.exists(r['image_path']):
                    st.image(r['image_path'], use_container_width=True)
                    st.caption(f"{r['date']} | {r['title']}")
    else: st.info("暂无精选内容。")

# --- Tab 3: 人生计划 ---
with tab3:
    st.header("🚀 未来蓝图")
    with st.expander("📝 绘制新的计划"):
        with st.form("plan_form", clear_on_submit=True):
            p_title = st.text_input("计划标题")
            p_details = st.text_area("详细步骤")
            p_pic = st.file_uploader("愿景配图", type=['jpg','png','jpeg'])
            if st.form_submit_button("开启计划"):
                if p_title:
                    p_path = ""
                    if p_pic:
                        p_path = os.path.join('life_plans', f"PLAN_{datetime.now().timestamp()}.jpg")
                        with open(p_path, "wb") as f: f.write(p_pic.getbuffer())
                    with get_connection() as conn:
                        conn.execute("INSERT INTO plans (date, title, details, image_path) VALUES (?,?,?,?)",
                                     (datetime.now().strftime('%Y-%m-%d'), p_title, p_details, p_path))
                    st.rerun()
    st.divider()
    if not df_plans.empty:
        for _, row in df_plans.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    if row['image_path'] and os.path.exists(row['image_path']):
                        st.image(row['image_path'], use_container_width=True)
                with c2:
                    st.subheader(row['title'])
                    st.write(f"📅 启动日期: {row['date']}")
                    st.info(row['details'])
                    if st.button("删除计划", key=f"p_del_{row['id']}"):
                        with get_connection() as conn:
                            conn.execute("DELETE FROM plans WHERE id=?", (row['id'],))
                        st.rerun()
            st.divider()

# --- Tab 4: 往事回响 (日期检索) ---
with tab4:
    search = st.text_input("🔍 检索内容或日期 (例如: 2026-03)")
    d_df = df_all.copy()
    if search:
        d_df = d_df[(d_df['content'].str.contains(search, na=False)) | (d_df['date'].str.contains(search, na=False))]
    for _, row in d_df.iterrows():
        c1, c2 = st.columns([1, 4])
        with c1:
            if row.get('image_path') and os.path.exists(row['image_path']):
                st.image(row['image_path'], use_container_width=True)
        with c2:
            st.write(f"**{row['date']}** | {row['category']} | {row['mood']}⭐")
            st.info(row['content'])
            if st.button("删除记录", key=f"del_{row['id']}"):
                with get_connection() as conn:
                    conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                st.rerun()
        st.divider()
