import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. 环境配置 ---
UPLOAD_FOLDER = 'life_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, 
                      mood INTEGER, image_path TEXT)''')
        # 数据库列自动修复补丁
        cursor = conn.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'image_path' not in columns:
            conn.execute('ALTER TABLE logs ADD COLUMN image_path TEXT DEFAULT ""')

# --- 2. 页面初始化 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

# 读取全局数据用于统计
with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)

# --- 3. 侧边栏：人生看板与能量统计 ---
with st.sidebar:
    st.header("⏳ 人生看板")
    birth = st.date_input("你的生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    
    # 基础进度
    total_days = expectancy * 365
    lived_days = (datetime.now().date() - birth).days
    percent = min(lived_days / total_days, 1.0)
    st.progress(percent)
    st.caption(f"人生已渡过 {lived_days} 天，进度 {percent:.2%}")

    st.divider()
    
    # 每日能量统计功能
    st.header("📊 能量统计")
    if not df_all.empty:
        # 转换日期格式，按天计算平均能量
        df_stat = df_all.copy()
        df_stat['only_date'] = df_stat['date'].str.split(' ').str[0]
        daily_mood = df_stat.groupby('only_date')['mood'].mean().reset_index()
        
        # 显示最近三天的平均能量
        st.write("📅 最近日均能量：")
        for i, row in daily_mood.head(3).iterrows():
            st.metric(label=row['only_date'], value=f"{row['mood']:.1f} ⭐")
    else:
        st.write("暂无统计数据")

st.title("🕯️ 虚无之镜：人生存根")

# --- 4. 记录模块 ---
with st.expander("📝 记录新的瞬间", expanded=False):
    with st.form("new_entry", clear_on_submit=True):
        col_text, col_meta = st.columns([2, 1])
        with col_text:
            content = st.text_area("此刻在想什么？", height=100)
            uploaded_file = st.file_uploader("上传照片", type=['png', 'jpg', 'jpeg'])
        with col_meta:
            cate = st.selectbox("分类", ["日常", "重要里程碑", "灵感闪现", "至暗时刻", "旅行"])
            mood = st.select_slider("能量", options=range(1, 11), value=5)
            manual_date = st.date_input("日期", datetime.now())
        
        if st.form_submit_button("封存入库"):
            if content:
                timestamp = manual_date.strftime('%Y-%m-%d') + " " + datetime.now().strftime('%H:%M')
                img_path = ""
                if uploaded_file is not None:
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    img_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path) VALUES (?,?,?,?,?)", 
                                 (timestamp, cate, content, mood, img_path))
                st.success("已存档。")
                st.rerun()

# --- 5. 检索模块（支持内容与日期检索） ---
st.divider()
search_query = st.text_input("🔍 检索往事（输入文字内容或日期，如：2024-05）")

# 过滤逻辑
display_df = df_all.copy()
if search_query:
    # 同时在内容(content)和日期(date)列中检索
    display_df = display_df[
        (display_df['content'].str.contains(search_query, case=False, na=False)) |
        (display_df['date'].str.contains(search_query, case=False, na=False))
    ]

# --- 6. 往事回响显示 ---
if not display_df.empty:
    for _, row in display_df.iterrows():
        with st.container():
            c1, c2 = st.columns([1, 4])
            with c1:
                if row.get('image_path') and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
                else:
                    st.caption("📷 纯文字记忆")
            with c2:
                st.write(f"**{row['date']}** | `{row['category']}` | 能量: {row['mood']}⭐")
                new_content = st.text_area("编辑内容", value=row['content'], key=f"edit_{row['id']}", label_visibility="collapsed")
                
                b1, b2, _ = st.columns([1, 1, 8])
                if b1.button("更新", key=f"upd_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("UPDATE logs SET content=? WHERE id=?", (new_content, row['id']))
                    st.toast("已修改")
                if b2.button("删除", key=f"del_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                    st.rerun()
            st.divider()
else:
    st.info("没有找到匹配的往事。")
