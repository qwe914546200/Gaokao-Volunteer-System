import sqlite3
import os

# 向上两级目录找到 gaokao_v2.db
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gaokao_v2.db')

def get_db_connection():
    """获取数据库连接，并设置以字典形式返回查询结果"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
