import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. 环境配置 ---
UPLOAD_FOLDER = 'life_images'
GALLERY_FOLDER = 'life_gallery' # 专门存放展板精选图
for folder in [UPLOAD_FOLDER, GALLERY_FOLDER]:
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
        # 展板表 (独立存储直接上传到展板的内容)
        conn.execute('''CREATE TABLE IF NOT EXISTS gallery 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, title TEXT, image_path TEXT)''')
        
        # 自动补齐 logs 表的 is_featured 列
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'is_featured' not in cols:
            conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')
        conn.commit()

# --- 2. 页面初始化 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    df_gallery = pd.read_sql_query("SELECT * FROM gallery ORDER BY date DESC", conn)

# --- 3. 侧边栏：人生统计 ---
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
        st.header("📊 能量统计")
        try:
            df_stat = df_all.copy()
            df_stat['only_date'] = pd.to_datetime(df_stat['date'].str.split(' ').str[0])
            daily_mood = df_stat.groupby('only_date')['mood'].mean().sort_index()
            
            # 圆状图 (维度占比)
            fig1, ax1 = plt.subplots(figsize=(5,5))
            cate_counts = df_all['category'].value_counts()
            ax1.pie(cate_counts, labels=cate_counts.index, autopct='%1.1f%%', startangle=90)
            fig1.patch.set_alpha(0)
            st.pyplot(fig1)

            # 趋势图
            fig2, ax2 = plt.subplots(figsize=(5,3))
            ax2.plot(daily_mood.index, daily_mood.values, marker='o', color='#FF4B4B')
            plt.xticks(rotation=45)
            fig2.patch.set_alpha(0)
            st.pyplot(fig2)
        except: pass

st.title("🕯️ 虚无之镜：人生存根")

# --- 4. 功能标签页 ---
tab1, tab2, tab3 = st.tabs(["✍️ 记录瞬间", "🖼️ 人生展板", "📜 往事回响"])

# --- Tab 1: 记录 ---
with tab1:
    with st.form("new_log", clear_on_submit=True):
        col_a, col_b = st.columns([2,1])
        with col_a:
            content = st.text_area("此刻在想什么？", height=150)
            pic = st.file_uploader("记录配图", type=['jpg','png','jpeg'])
        with col_b:
            cat = st.selectbox("分类", ["日常", "里程碑", "灵感", "至暗", "旅行"])
            val = st.select_slider("能量", range(1,11), 5)
            is_feat = st.checkbox("同步至展板展示")
        
        if st.form_submit_button("封存入库"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join(UPLOAD_FOLDER, f"LOG_{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, 1 if is_feat else 0))
                st.success("已存档。")
                st.rerun()

# --- Tab 2: 人生展板 (支持直接上传) ---
with tab2:
    st.header("🖼️ 精选瞬间展板")
    
    # 新增：展板专用上传区
    with st.expander("➕ 直接上传精选照片至展板"):
        with st.form("gallery_upload", clear_on_submit=True):
            g_pic = st.file_uploader("选择精选照片", type=['jpg','png','jpeg'])
            g_title = st.text_input("给照片起个标题或写句感悟")
            if st.form_submit_button("上传至展板"):
                if g_pic:
                    g_path = os.path.join(GALLERY_FOLDER, f"GAL_{datetime.now().timestamp()}.jpg")
                    with open(g_path, "wb") as f: f.write(g_pic.getbuffer())
                    now_date = datetime.now().strftime('%Y-%m-%d')
                    with get_connection() as conn:
                        conn.execute("INSERT INTO gallery (date, title, image_path) VALUES (?,?,?)",
                                     (now_date, g_title, g_path))
                    st.success("照片已收录至展板！")
                    st.rerun()
                else:
                    st.error("请先选择照片。")

    st.divider()
    
    # 数据源 1: 直接上传到展板的照片
    # 数据源 2: 记录中勾选了“同步至展板”的照片
    logs_featured = df_all[df_all['is_featured'] == 1].rename(columns={'content': 'title'})
    combined_gallery = pd.concat([df_gallery, logs_featured[['date', 'title', 'image_path']]], ignore_index=True)
    combined_gallery = combined_gallery.sort_values(by='date', ascending=False)

    if not combined_gallery.empty:
        cols = st.columns(3)
        for i, row in enumerate(combined_gallery.iterrows()):
            r = row[1]
            with cols[i % 3]:
                if r['image_path'] and os.path.exists(r['image_path']):
                    st.image(r['image_path'], use_container_width=True)
                    st.write(f"**{r['date']}**")
                    st.caption(r['title'] if r['title'] else "无标题")
                st.write("")
    else:
        st.info("展板空空如也，快去上传或勾选精选记录吧！")

# --- Tab 3: 往事回响 (含日期检索) ---
with tab3:
    search = st.text_input("🔍 检索内容或日期 (例如: 2024-05)")
    d_df = df_all.copy()
    if search:
        d_df = d_df[(d_df['content'].str.contains(search, na=False)) | (d_df['date'].str.contains(search, na=False))]

    if not d_df.empty:
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
