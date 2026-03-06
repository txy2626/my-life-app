import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt
from github import Github

# --- 1. 基础配置与科幻样式 / Config & Sci-Fi Style ---
st.set_page_config(page_title="虚无之镜 | Mirror of Void", layout="wide", page_icon="🕯️")

# 自定义科幻样式 CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #00f2fe, #4facfe); }
    .countdown-box { 
        font-family: 'Courier New', Courier, monospace; 
        color: #00f2fe; 
        text-align: center; 
        padding: 15px; 
        border: 1px solid #00f2fe; 
        border-radius: 8px;
        background: rgba(0, 242, 254, 0.05);
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 隐私锁屏 / Privacy Lock ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True

    st.title("🕯️ 虚无之镜 | Mirror of Void")
    target_password = st.secrets.get("APP_PASSWORD", "123456") 
    pwd = st.text_input("唯有持灯者方能进入 | Access Code Required", type="password")
    if st.button("系统接入 | System Access"):
        if pwd == target_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("🔑 拒绝访问 | Access Denied")
    return False

if not check_password():
    st.stop()

# --- 3. 数据库初始化 / DB Init ---
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
        # 补丁：确保字段完整
        cursor = conn.execute("PRAGMA table_info(logs)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'is_featured' not in cols: conn.execute('ALTER TABLE logs ADD COLUMN is_featured INTEGER DEFAULT 0')
        if 'image_path' not in cols: conn.execute('ALTER TABLE logs ADD COLUMN image_path TEXT DEFAULT ""')

init_db()

# --- 4. GitHub 同步逻辑 / GitHub Sync ---
def sync_to_github(file_path, commit_msg):
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo_name = st.secrets.get("REPO_NAME")
        if not token or not repo_name:
            st.warning("⚠️ 未配置云端同步 | Cloud Sync Not Configured")
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
        st.toast(f"☁️ {file_path} 同步成功 | Synced")
    except Exception as e:
        st.error(f"同步异常 | Sync Error: {e}")

# --- 5. 数据读取 / Data Load ---
with get_connection() as conn:
    df_all = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)
    df_gallery = pd.read_sql_query("SELECT * FROM gallery ORDER BY date DESC", conn)
    df_plans = pd.read_sql_query("SELECT * FROM plans ORDER BY id DESC", conn)

# --- 6. 侧边栏：倒计时与科幻看板 / Sidebar ---
with st.sidebar:
    st.header("⏳ 人生画布 | Life Canvas")
    birth_date = st.date_input("诞生之日 | Birth Date", datetime(2000, 1, 1))
    target_age = st.slider("终末之限 | Expected Age", 60, 120, 85)
    
    # 倒计时逻辑 / Countdown Logic
    death_date = datetime(birth_date.year + target_age, birth_date.month, birth_date.day)
    time_left = death_date - datetime.now()
    
    if time_left.total_seconds() > 0:
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        st.markdown(f"""
        <div class="countdown-box">
            <p style="margin:0;font-size:0.7rem;color:#888;">人生倒计时 | Final Countdown</p>
            <p style="margin:0;font-size:1.1rem;font-weight:bold;">{days}d {hours:02}:{minutes:02}:{seconds:02}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.progress(min((datetime.now().date() - birth_date).days / (target_age * 365), 1.0))

    if not df_all.empty:
        st.divider()
        st.header("📊 能量看板 | Bio-Pulse")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(5, 3.5))
        
        chart_df = df_all.copy()
        chart_df['date_dt'] = pd.to_datetime(chart_df['date'])
        chart_data = chart_df.groupby(chart_df['date_dt'].dt.date)['mood'].mean().sort_index()
        
        ax.plot(chart_data.index, chart_data.values, color='#00f2fe', linewidth=2, marker='o', markersize=4)
        ax.fill_between(chart_data.index, chart_data.values, color='#00f2fe', alpha=0.15)
        ax.grid(color='#4facfe', linestyle='--', linewidth=0.3, alpha=0.4)
        ax.set_title("情绪脉冲 | Emotion Pulse", fontsize=9, color='#00f2fe')
        plt.xticks(rotation=45, fontsize=6)
        plt.yticks(fontsize=6)
        st.pyplot(fig)

# --- 7. 主功能区 / Main Functions ---
st.title("🕯️ 虚无之镜 | Mirror of Void")

tab1, tab2, tab3, tab4 = st.tabs([
    "✍️ 记录存根 | Entry", "🖼️ 人生展板 | Vision", 
    "🚀 人生计划 | Plans", "📜 往事回响 | Echoes"
])

# --- Tab 1: 记录存根 | Entry ---
with tab1:
    with st.form("new_log", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            content = st.text_area("记录此刻... | Capture current thought...", height=150)
            pic = st.file_uploader("配图 | Attachment", type=['jpg','png','jpeg'])
        with c2:
            cat = st.selectbox("分类 | Category", ["日常/Daily", "里程碑/Milestone", "灵感/Inspo", "至暗/Darkness", "旅行/Travel"])
            val = st.select_slider("能量 | Energy Level", range(1,11), 5)
            is_feat = st.checkbox("设为精选 | Feature on Board")
        if st.form_submit_button("封存入库 | Seal Entry"):
            if content:
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                path = ""
                if pic:
                    path = os.path.join('life_images', f"LOG_{datetime.now().timestamp()}.jpg")
                    with open(path, "wb") as f: f.write(pic.getbuffer())
                    sync_to_github(path, "Upload Log Image")
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path, is_featured) VALUES (?,?,?,?,?,?)",
                                 (now, cat, content, val, path, 1 if is_feat else 0))
                sync_to_github(DB_PATH, "Update DB")
                st.rerun()

# --- Tab 2: 人生展板 | Vision Board ---
with tab2:
    st.header("🖼️ 精选瞬间 | Curated Moments")
    with st.expander("➕ 直接上传照片 | Direct Upload"):
        with st.form("gal_up", clear_on_submit=True):
            g_pic = st.file_uploader("选择照片 | Select Image", type=['jpg','png','jpeg'])
            g_title = st.text_input("描述 | Title")
            if st.form_submit_button("同步展板 | Sync to Board"):
                if g_pic:
                    g_path = os.path.join('life_gallery', f"GAL_{datetime.now().timestamp()}.jpg")
                    with open(g_path, "wb") as f: f.write(g_pic.getbuffer())
                    sync_to_github(g_path, "Upload Gallery")
                    with get_connection() as conn:
                        conn.execute("INSERT INTO gallery (date, title, image_path) VALUES (?,?,?)",
                                     (datetime.now().strftime('%Y-%m-%d'), g_title, g_path))
                    sync_to_github(DB_PATH, "Update DB")
                    st.rerun()
    st.divider()
    feat_logs = df_all[df_all['is_featured'] == 1].rename(columns={'content': 'title'})
    combined = pd.concat([df_gallery, feat_logs[['date', 'title', 'image_path']]], ignore_index=True).sort_values(by='date', ascending=False)
    if not combined.empty:
        cols = st.columns(3)
        for i, row in enumerate(combined.iterrows()):
            r = row[1]
            with cols[i % 3]:
                if r['image_path'] and os.path.exists(r['image_path']):
                    st.image(r['image_path'], use_container_width=True)
                    st.caption(f"{r['date']} | {r['title']}")

# --- Tab 3: 人生计划 | Life Plans ---
with tab3:
    st.header("🚀 未来蓝图 | Future Blueprints")
    with st.expander("📝 绘制新计划 | Draft New"):
        with st.form("plan_form", clear_on_submit=True):
            p_title = st.text_input("计划标题 | Project Name")
            p_details = st.text_area("详细步骤 | Protocol")
            p_pic = st.file_uploader("愿景配图 | Visionary Asset", type=['jpg','png','jpeg'])
            if st.form_submit_button("开启计划 | Initiate"):
                if p_title:
                    p_path = ""
                    if p_pic:
                        p_path = os.path.join('life_plans', f"PLAN_{datetime.now().timestamp()}.jpg")
                        with open(p_path, "wb") as f: f.write(p_pic.getbuffer())
                        sync_to_github(p_path, "Upload Plan")
                    with get_connection() as conn:
                        conn.execute("INSERT INTO plans (date, title, details, image_path) VALUES (?,?,?,?)",
                                     (datetime.now().strftime('%Y-%m-%d'), p_title, p_details, p_path))
                    sync_to_github(DB_PATH, "Update DB")
                    st.rerun()
    st.divider()
    for _, row in df_plans.iterrows():
        c1, c2 = st.columns([1, 2])
        with c1:
            if row['image_path'] and os.path.exists(row['image_path']): st.image(row['image_path'], use_container_width=True)
        with c2:
            st.subheader(row['title'])
            st.info(row['details'])
            if st.button("废弃计划 | Abort", key=f"p_{row['id']}"):
                with get_connection() as conn: conn.execute("DELETE FROM plans WHERE id=?", (row['id'],))
                sync_to_github(DB_PATH, "Delete Plan")
                st.rerun()
        st.divider()

# --- Tab 4: 往事回响 | Past Echoes ---
with tab4:
    col1, col2 = st.columns([3, 1])
    with col1: search = st.text_input("🔍 搜索记忆 | Search Memory")
    with col2:
        st.write("")
        if st.button("🎲 随机漫游 | Random Echo"):
            if not df_all.empty:
                r = df_all.sample(1).iloc[0]
                st.info(f"💡 记忆闪回 | Flashback ({r['date']}):\n\n{r['content']}")
    
    view_df = df_all.copy()
    if search:
        view_df = view_df[(view_df['content'].str.contains(search, na=False)) | (view_df['date'].str.contains(search, na=False))]

    for _, row in view_df.iterrows():
        c1, c2 = st.columns([1, 4])
        with c1:
            if row.get('image_path') and os.path.exists(row['image_path']): st.image(row['image_path'], use_container_width=True)
        with c2:
            st.write(f"**{row['date']}** | {row['category']} | {row['mood']}⭐")
            st.write(row['content'])
            if st.button("抹除记录 | Erase", key=f"d_{row['id']}"):
                with get_connection() as conn: conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                sync_to_github(DB_PATH, "Delete Log")
                st.rerun()
        st.divider()
