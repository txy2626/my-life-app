import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. 初始化设置 ---
# 创建存储图片的文件夹
UPLOAD_FOLDER = 'life_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 数据库文件
DB_PATH = 'my_life.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# 初始化数据库
def init_db():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, category TEXT, content TEXT, 
                      mood INTEGER, image_path TEXT)''')

# --- 2. 页面配置 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

# 自定义 CSS 样式
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stTextArea textarea { font-size: 1.1rem; }
    .log-card { padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 10px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🕯️ 虚无之镜：人生存根")

# --- 3. 侧边栏：人生进度条与统计 ---
with st.sidebar:
    st.header("⏳ 人生画布")
    birth = st.date_input("你的生日", datetime(2000, 1, 1))
    expectancy = st.slider("预期寿命", 60, 120, 85)
    
    total_days = expectancy * 365
    lived_days = (datetime.now().date() - birth).days
    percent = min(lived_days / total_days, 1.0)
    
    st.progress(percent)
    st.write(f"人生进度: {percent:.2%}")
    st.write(f"已渡过: {lived_days} 天")
    st.write(f"余额: {max(0, total_days - lived_days)} 天")

# --- 4. 核心功能：记录瞬间 ---
with st.expander("🖼️ 记录带照片的瞬间", expanded=True):
    with st.form("new_entry", clear_on_submit=True):
        col_text, col_meta = st.columns([2, 1])
        
        with col_text:
            content = st.text_area("此刻在想什么？", height=150, placeholder="输入文字...")
            uploaded_file = st.file_uploader("上传一张照片 (可选)", type=['png', 'jpg', 'jpeg'])
            
        with col_meta:
            cate = st.selectbox("分类", ["日常", "重要里程碑", "灵感闪现", "至暗时刻", "旅行"])
            mood = st.select_slider("能量状态", options=range(1, 11), value=5)
            manual_date = st.date_input("日期 (默认今天)", datetime.now())
        
        if st.form_submit_button("封存入库"):
            if content:
                # 处理日期和图片
                timestamp = manual_date.strftime('%Y-%m-%d') + " " + datetime.now().strftime('%H:%M')
                img_path = ""
                
                if uploaded_file is not None:
                    # 使用时间戳作为文件名防止冲突
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    img_path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                # 写入数据库
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood, image_path) VALUES (?,?,?,?,?)", 
                                 (timestamp, cate, content, mood, img_path))
                st.success("这一刻已存档。")
                st.rerun()
            else:
                st.error("内容不能为空哦。")

# --- 5. 往事回响：展示与编辑 ---
st.divider()
st.subheader("📜 往事回响")

# 搜索与筛选
search_query = st.text_input("🔍 检索往事...")

# 读取数据
with get_connection() as conn:
    query = "SELECT * FROM logs ORDER BY date DESC"
    df = pd.read_sql_query(query, conn)

# 过滤逻辑
if search_query:
    df = df[df['content'].str.contains(search_query, case=False, na=False)]

if not df.empty:
    for _, row in df.iterrows():
        with st.container():
            # 使用列布局显示卡片
            c1, c2 = st.columns([1, 3])
            
            with c1:
                if row['image_path'] and os.path.exists(row['image_path']):
                    st.image(row['image_path'], use_container_width=True)
                else:
                    st.caption("📷 纯文字记忆")
            
            with c2:
                # 标题头
                st.write(f"**{row['date']}** | `{row['category']}` | 能量: {row['mood']}⭐")
                
                # 内容编辑区（点击可直接在页面修改）
                new_content = st.text_area("内容", value=row['content'], key=f"edit_{row['id']}", label_visibility="collapsed")
                
                # 操作按钮
                col_btn1, col_btn2, _ = st.columns([1, 1, 4])
                if col_btn1.button("更新", key=f"update_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("UPDATE logs SET content=? WHERE id=?", (new_content, row['id']))
                    st.toast("已修改。")
                
                if col_btn2.button("删除", key=f"del_{row['id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM logs WHERE id=?", (row['id'],))
                        if row['image_path'] and os.path.exists(row['image_path']):
                            os.remove(row['image_path'])
                    st.rerun()
            st.divider()
            
    # 数据可视化
    st.subheader("📊 情绪趋势")
    chart_df = df.copy()
    chart_df['date'] = pd.to_datetime(chart_df['date'])
    st.line_chart(chart_df.set_index('date')['mood'])
    
else:
    st.info("还没有任何记录。开始记录你的第一份存根吧！")
