import os
import sys
import io
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found in .env")
    sys.exit(1)

# Xóa +psycopg trong chuỗi URL nếu có để dùng trực tiếp psycopg3
db_url_connect = db_url.replace("postgresql+psycopg://", "postgresql://")

sql_file_path = r"e:\NguyenQuocKhanh\DAMH\Shop_laptop\T2CA1\DB.sql"

print(f"Connecting to {db_url_connect}...")
import psycopg

try:
    with io.open(sql_file_path, "r", encoding="utf-8") as f:
        sql_commands = f.read()

    with psycopg.connect(db_url_connect) as conn:
        with conn.cursor() as cur:
            print("Dropping and recreating public schema...")
            cur.execute("DROP SCHEMA public CASCADE;")
            cur.execute("CREATE SCHEMA public;")
            
            print("Executing DB.sql...")
            cur.execute(sql_commands)
        conn.commit()
    print("Database initialized successfully from DB.sql!")
except Exception as e:
    print("Lỗi khởi tạo DB:", e)
