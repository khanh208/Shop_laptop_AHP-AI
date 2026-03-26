import os
import sys

# Đảm bảo import đúng cấu trúc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run import app
from app.extensions import db
from app.services.import_service import stage_laptop_file, commit_staging

file_path = r"e:\NguyenQuocKhanh\DAMH\Shop_laptop\T2CA1\laptop_be\Train AI\AHP_Laptop_Nhom8.xlsx"

if not os.path.exists(file_path):
    print(f"Error: File not found: {file_path}")
    sys.exit(1)

with app.app_context():
    with db.engine.begin() as conn:
        print("Tiến hành nạp dữ liệu từ file Excel (Staging)...")
        staged = stage_laptop_file(
            conn=conn,
            file_path=file_path,
            original_filename="AHP_Laptop_Nhom8.xlsx",
            sheet_name="Laptop_Data",
            replace_staging=True,
        )
        print("Đã stage xong. Xử lý dữ liệu trùng lặp trong stg_laptop_data...")
        from sqlalchemy import text
        conn.execute(text("""
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        COALESCE(NULLIF(TRIM(laptop_name), ''), 'Unknown Laptop'),
                        COALESCE(NULLIF(TRIM(model_code), ''), '')
                    ORDER BY id
                ) AS rn
            FROM stg_laptop_data
        )
        DELETE FROM stg_laptop_data s
        USING ranked r
        WHERE s.id = r.id
          AND r.rn > 1;
        """))
        print("Tiến hành commit vào Database...")
        committed = commit_staging(conn)
        print("Kết quả Commit:", committed)
        print("Hoàn tất Import dữ liệu Laptop thành công!")
