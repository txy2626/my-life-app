import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import matplotlib.pyplot as plt
from github import Github

# --- 1. 基础配置与隐私锁 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if st.session_state["password_correct"]:
        return True

    st.title("🕯️ 虚无之镜")
    # 从 Secrets 读取预设密码
    target_password = st.secrets.get("APP_PASSWORD", "123456") 
    pwd = st.text_input("唯有持灯者方能进入 (输入密码)", type="password")
    if st.button("进入"):
        if pwd == target_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("🔑 密码错误")
    return False

if not check_password():
    st.stop()

# --- 2. 文件夹与数据库初始化 ---
FOLDERS = ['life_images', 'life_gallery', 'life_plans']
for f in FOLDERS:
    if not os.path.exists(f): os.makedirs(f)

DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, 
                      content TEXT, mood INTEGER, image_path TEXT, is_featured INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS gallery 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, title TEXT, image_path TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS plans 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, title TEXT, details TEXT, image_path TEXT)''')
        
        # 字段补全补丁
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'is_featured' not in cols:
            conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')
        if 'image_path' not in cols:
            conn.execute('ALTER TABLE logs ADD COLUMN image_path TEXT DEFAULT ""')

init_db()

# --- 3. GitHub 永久同步逻辑 ---
def sync_to_github(file_path, commit_msg):
    try:
        # 必须在 Secrets 配置 GITHUB_TOKEN 和 REPO_NAME
        token = st.secrets.get("GITHUB_TOKEN")
        repo_name = st.secrets.get("REPO_NAME")
        
        if not token or not repo_name:
            st.warning("未配置 GitHub Secrets，数据仅保存在本地（重启将丢失）")
            return

        g = Github(token)
        repo = g.get_repo(repo_name)
        with open(file_path, "rb") as f:
            content = f.read()
        
        remote_path = file_path.replace("\\", "/")
        try:
            contents = repo.get_contents(remote_path)
            repo.update_file(remote_path, commit_msg, content, contents.sha)
        except:
            repo.create_file(remote_path, commit_msg, content)
        st.toast(f"☁️ {file_path} 已永久存档至云端")
    except Exception as e:
        st.error(f"同步失败: {e}")

# --- 4. 数据读取 ---
with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    df_gallery = pd.read_sql_query("SELECT * FROM gallery ORDER BY date DESC", conn)
    df_plans = pd.read_sql_query("SELECT * FROM plans ORDER BY id DESC", conn)

# --- 5. 侧边栏：画布与统计 ---
with st.sidebar:
    st.header("⏳ 人生画布")
    birth = st.date_input("你的生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    lived_days = (datetime.now().date() - birth).days
    st.progress(min(lived_days / (expectancy * 365), 1.0))
    st.caption(f"已渡过 {lived_days} 天 | 进度: {lived_days/(expectancy*365):.2%}")

    if not df_all.empty:
        st.divider()
        st.header("📊 能量看板")
        chart_df = df_all.copy()
        chart_df['date_dt'] = pd.to_datetime(chart_df['date'])
        chart_data = chart_df.groupby(chart_df['date_dt'].dt.date)['mood'].mean()
        st.line_chart(chart_data)

        cate_counts = df_all['category'].value_counts()
        fig, ax = plt.subplots(figsize=(5,5))
        ax.pie(cate_counts, labels=cate_counts.index, autopct='%1.1f%%', startangle=90)
        fig.patch.set_alpha(0)
        st.pyplot(fig)

st.title("🕯️ 虚无之镜")

# --- 6. 主功能区 ---
tab1, tab2, tab3, tab4 = st.tabs(["✍️ 记录存根", "🖼️ 人生展板", "🚀 人生计划", "📜 往事回响"])

# --- Tab 1: 记录存根 ---
with tab1:
    with st.form("new_log", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            content = st.text_area("记录此刻...", height=150)
            pic = st.file_uploader("配图", type=['jpg','png','jpeg'])
        with c2:
            cat = st.selectbox("分类", ["日常", "里程碑", "灵感", "至暗", "旅行"])
            val = st.select_slider("能量", range(1,11), 5)
            is_feat = st.checkbox("同步至展板")
        if st.form_submit_button("封存入库"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join('life_images', f"LOG_{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                    sync_to_github(path, "Upload Image") # 同步图片
                
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, 1 if is_feat else 0))
                sync_to_github(DB_PATH, "Update DB") # 同步数据库
                st.rerun()

# --- Tab 2: 人生展板 ---
with tab2
