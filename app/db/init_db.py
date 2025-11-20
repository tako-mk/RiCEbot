import sqlite3
import os

# dbファイルのパス（result.db）
db_path = os.path.join(os.path.dirname(__file__), "result.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS result_a;")
cursor.execute("DROP TABLE IF EXISTS result_b;")

# result_a テーブル（4team戦：敵3チーム）
cursor.execute("""
CREATE TABLE IF NOT EXISTS result_a (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player TEXT,
    my_point INTEGER NOT NULL,
    enemy1 TEXT,
    point1 INTEGER,
    enemy2 TEXT,
    point2 INTEGER,
    enemy3 TEXT,
    point3 INTEGER,
    rank INTEGER,
    date TEXT
);
""")

# result_b テーブル（2team戦：敵1チーム）
cursor.execute("""
CREATE TABLE IF NOT EXISTS result_b (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player TEXT,
    my_point INTEGER NOT NULL,
    enemy TEXT,
    enemy_point INTEGER,
    rank INTEGER,
    date TEXT
);
""")

conn.commit()
conn.close()

print(f"✅ データベース初期化完了: {db_path}")
