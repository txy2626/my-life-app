import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. 基础配置 ---
UPLOAD_FOLDER = 'life_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """极其强力的数据库初始化与修复"""
    with get_connection() as conn:
        # 创建基础表
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, mood INTEGER)''')
        conn.commit()
        
        # 尝试逐一添加缺失列
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        
        try:
            if 'image_path' not in cols:
                conn.execute('ALTER TABLE logs ADD COLUMN image_path TEXT DEFAULT ""')
            if 'is_featured' not in cols:
                conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')
            conn.commit()
        except Exception as e:
            st.error(f"数据库自动升级失败，请使用侧边栏的‘强制重置’。错误: {e}")

# --- 2. 页面初始化 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

# --- 侧边栏辅助功能 ---
with st.sidebar:
    st.header("🛠️ 系统控制")
    if st.button("⚠️ 强制重置数据库"):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        st.success("数据库已删除，请点击下方按钮重启。")
        st.button("重新初始化")
        st.rerun()

    st.divider()
    st.header("⏳ 人生画布")
    birth = st.date_input("你的生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    lived_days = (datetime.now().date() - birth).days
    percent = min(lived_days / (expectancy * 365), 1.0)
    st.progress(percent)
    st.caption(f"进度: {percent:.2%}")

# 获取数据（使用防御性编程避开 KeyError）
try:
    with get_connection() as conn:
        df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
except Exception as e:
    st.warning("正在初始化数据结构，请稍候...")
    df_all = pd.DataFrame()

# --- 3. 可视化图表 ---
if not df_all.empty and 'mood' in df_all.columns:
    with st.sidebar:
        st.divider()
        st.subheader("📊 能量看板")
        # 简单绘图逻辑
        try:
            fig, ax = plt.subplots(figsize=(5,3))
            df_plot = df_all.copy()
            df_plot['date_only'] = pd.to_datetime(df_plot['date'].str.split(' ').str[0])
            daily = df_plot.groupby('date_only')['mood'].mean()
            ax.plot(daily.index, daily.values, marker='o', color='red')
            plt.xticks(rotation=45)
            fig.patch.set_alpha(0)
            st.pyplot(fig)
        except: pass

st.title("🕯️ 虚无之镜：人生存根")

# --- 4. 功能标签页 ---
t1, t2, t3 = st.tabs(["✍️ 记录瞬间", "🖼️ 人生展板", "📜 往事回响"])

with t1:
    with st.form("new_log", clear_on_submit=True):
        col_a, col_b = st.columns([2,1])
        with col_a:
            content = st.text_area("记录此刻...")
            pic = st.file_uploader("传张照片", type=['jpg','png','jpeg'])
        with col_b:
            cat = st.selectbox("分类", ["日常", "重要", "灵感", "至暗", "旅行"])
            val = st.select_slider("能量", range(1,11), 5)
            feat = st.checkbox("设为精选")
        
        if st.form_submit_button("封存"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join(UPLOAD_FOLDER, f"{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, 1 if feat else 0))
                st.success("存档成功！")
                st.rerun()

with t2:
    if not df_all.empty and 'is_featured' in df_all.columns:
        f_df = df_all[df_all['is_featured'] == 1]
        if not f_df.empty:
            cs = st.columns(3)
            for i, r in enumerate(f_df.iterrows()):
                row = r[1]
                with cs[i % 3]:
                    if row.get('image_path') and os.path.exists(row['image_path']):
                        st.image(row['image_path'], use_container_width=True)
                    st.caption(f"{row['date']} | {row['content'][:20]}")
    else: st.info("还没有精选瞬间。")

with t3:
    search = st.text_input("🔍 检索")
    d_df = df_all.copy()
    if search and not d_df.empty:
        d_df = d_df[d_df['content'].str.contains(search, na=False)]
    
    if not d_df.empty:
        for _, row in d_df.iterrows():
            c1, c2 = st.columns([1,4])
            with c1:
                if row.get('image_path') and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
            with c2:
                st.write(f"**{row['date']}** | {row.get('category','')} | {row.get('mood',5)}⭐")
                st.info(row['content'])
                if st.button("删除", key=f"d_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                    st.rerun()
            st.divider()
