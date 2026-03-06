import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. 数据库基础设置 ---
# 这会在你的电脑本地创建一个名为 my_life.db 的数据库文件
db_path = 'my_life.db'

def get_connection():
    return sqlite3.connect(db_path, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        # 创建表：包含 ID(主键), 日期, 类别, 内容, 情绪值
        conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT, category TEXT, content TEXT, mood INTEGER)''')

# --- 2. 页面初始化 ---
st.set_page_config(page_title="虚无之镜", layout="wide", page_icon="🕯️")
init_db()

st.title("🕯️ 虚无之镜：人生存根")
st.markdown("这是你存放记忆的私密空间。所有数据均保存在本地。")

# --- 3. 模块一：新增瞬间 (表单模式) ---
with st.expander("📝 记录新的瞬间", expanded=True):
    with st.form("new_entry", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        content = col1.text_input("此刻在想什么？", placeholder="写下你的故事...")
        cate = col2.selectbox("分类", ["日常", "重要里程碑", "灵感", "至暗时刻"])
        mood = col3.slider("能量(1-10)", 1, 10, 5)
        
        if st.form_submit_button("封存"):
            if content:
                now = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                with get_connection() as conn:
                    conn.execute("INSERT INTO logs (date, category, content, mood) VALUES (?,?,?,?)", 
                                 (now, cate, content, mood))
                st.success("已存档。")
                st.rerun()
            else:
                st.error("请输入内容后再提交。")

# --- 4. 模块二：往事回响 (可编辑/新增/删除的表格) ---
st.subheader("📜 往事回响")
st.caption("💡 技巧：双击内容可直接修改 | 点击表格底部 [+] 可补录往事 | 选中行按 Del 可删除")

# 从数据库读取数据
with get_connection() as conn:
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY date DESC", conn)

# 使用 data_editor 实现 Excel 般的交互
edited_df = st.data_editor(
    df,
    column_config={
        "id": None, # 隐藏内部ID
        "date": st.column_config.TextColumn("时间线"),
        "category": st.column_config.SelectboxColumn("分类", options=["日常", "重要里程碑", "灵感", "至暗时刻"]),
        "content": st.column_config.TextColumn("纪实内容", width="large"),
        "mood": st.column_config.NumberColumn("能量星级", format="%d ⭐")
    },
    num_rows="dynamic", # 允许动态增减行
    use_container_width=True,
    key="editor"
)

# --- 5. 同步保存按钮 ---
col_save, col_empty = st.columns([1, 4])
if col_save.button("💾 同步所有变更", type="primary"):
    with get_connection() as conn:
        # 清空旧数据，存入编辑后的新数据
        conn.execute("DELETE FROM logs")
        edited_df.to_sql('logs', conn, if_exists='append', index=False)
    st.toast("往事已成功更新！")
    st.rerun()

# --- 6. 情绪可视化 ---
if not df.empty:
    st.divider()
    st.subheader("📈 人生能量波动")
    # 将日期设为索引并绘制折线图
    chart_data = df.copy()
    chart_data['date'] = pd.to_datetime(chart_data['date'])
    st.line_chart(chart_data.set_index('date')['mood'])
