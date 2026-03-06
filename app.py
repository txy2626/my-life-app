import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# --- 1. 文件夹与数据库配置 ---
folders = ['life_images', 'life_gallery', 'life_plans']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        # 往事记录表 (新增 unlock_date 字段)
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, 
                      mood INTEGER, image_path TEXT, is_featured INTEGER DEFAULT 0,
                      unlock_date TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS gallery 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, title TEXT, image_path TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS plans 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, title TEXT, details TEXT, image_path TEXT)''')
        
        # 数据库列自动补齐补丁
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'unlock_date' not in cols:
            conn.execute('ALTER TABLE logs ADD COLUMN unlock_date TEXT')

# --- 2. 初始化 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    df_gallery = pd.read_sql_query("SELECT * FROM gallery ORDER BY date DESC", conn)
    df_plans = pd.read_sql_query("SELECT * FROM plans ORDER BY id DESC", conn)

# --- 3. 艺术化 UI 与背景色 (随心情波动) ---
if not df_all.empty:
    # 排除掉还没解锁的胶囊，计算真实的心情
    real_mood_df = df_all[df_all['unlock_date'].isna() | (df_all['unlock_date'] <= datetime.now().strftime('%Y-%m-%d'))]
    avg_mood = real_mood_df['mood'].head(5).mean() if not real_mood_df.empty else 5
    
    bg_color = "#FFF9E3" if avg_mood >= 7 else "#F1F8E9" if avg_mood >= 4 else "#E3F2FD"
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg_color}; transition: background-color 2s; }}
        .capsule-locked {{
            filter: blur(8px);
            pointer-events: none;
            user-select: none;
            opacity: 0.6;
        }}
        .capsule-badge {{
            background: #333; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 4. 侧边栏统计 ---
with st.sidebar:
    st.header("⏳ 时光刻度")
    birth = st.date_input("生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    lived_days = (datetime.now().date() - birth).days
    st.progress(min(lived_days / (expectancy * 365), 1.0))
    
    if not df_all.empty:
        st.divider()
        st.subheader("📈 能量起伏")
        chart_data = df_all.groupby(df_all['date'].str[:10])['mood'].mean()
        st.line_chart(chart_data)

st.title("🕯️ 虚无之镜")

# --- 5. 标签页 ---
tab1, tab2, tab3, tab4 = st.tabs(["✍️ 存根", "🖼️ 展板", "🚀 计划", "⌛ 时空胶囊"])

# --- Tab 1: 存根 (新增胶囊设置) ---
with tab1:
    with st.form("new_log", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            content = st.text_area("此刻的回响...", height=150)
            pic = st.file_uploader("上传影像", type=['jpg','png','jpeg'])
        with c2:
            cat = st.selectbox("分类", ["日常", "里程碑", "灵感", "至暗", "秘密"])
            val = st.select_slider("能量状态", range(1,11), 5)
            # 胶囊逻辑
            is_capsule = st.checkbox("封存为时空胶囊")
            unlock_d = st.date_input("设定解锁日期", datetime.now() + timedelta(days=365)) if is_capsule else None
        
        if st.form_submit_button("封入时光"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join('life_images', f"LOG_{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                
                unlock_str = unlock_d.strftime('%Y-%m-%d') if is_capsule else None
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, unlock_date) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, unlock_str))
                st.success("已交由时光保管。" if is_capsule else "存根已留存。")
                st.rerun()

# --- Tab 4: 时空胶囊展示区 ---
with tab4:
    st.header("⏳ 时空胶囊")
    capsules = df_all[df_all['unlock_date'].notna()]
    
    if not capsules.empty:
        for _, row in capsules.iterrows():
            is_locked = row['unlock_date'] > datetime.now().strftime('%Y-%m-%d')
            
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    if is_locked:
                        st.markdown("<h1 style='text-align:center;'>🔒</h1>", unsafe_allow_html=True)
                    elif row['image_path'] and os.path.exists(row['image_path']):
                        st.image(row['image_path'], use_container_width=True)
                
                with col2:
                    if is_locked:
                        st.write(f"📅 **封存于: {row['date']}**")
                        st.write(f"🔓 **解锁于: {row['unlock_date']}**")
                        st.markdown(f'<div class="capsule-locked">{row["content"]}</div>', unsafe_allow_html=True)
                        st.caption("这是一封来自过去的信，目前还不到开启的时候。")
                    else:
                        st.markdown(f"**{row['date']}** <span class='capsule-badge'>已解锁</span>", unsafe_allow_html=True)
                        st.info(row['content'])
                        if st.button("删除胶囊", key=f"cap_del_{row['id']}"):
                            with get_connection() as conn:
                                conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                            st.rerun()
            st.divider()
    else:
        st.info("你还没有埋下任何时空胶囊。")

# 其他 Tab (Tab 2 & Tab 3) 保持原样逻辑...
# [此处省略了展板和计划的代码，建议保留上一版内容即可]
