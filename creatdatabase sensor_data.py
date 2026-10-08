import sqlite3
from datetime import datetime
import os

# 连接数据库（自动创建文件）
conn = sqlite3.connect(os.getenv('ENV_MONITOR_DB', os.path.join(os.path.dirname(__file__), 'environment.db')))
cursor = conn.cursor()

# 创建数据表
cursor.execute('''
  CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT
  )
''')
conn.commit()
conn.close()
