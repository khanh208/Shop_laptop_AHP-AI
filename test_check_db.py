import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('laptop_be/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('SELECT AVG(norm_battery), AVG(norm_durability), AVG(norm_upgradeability) FROM laptop_ml_features')
print("Averages:")
print(cur.fetchone())

cur.execute('SELECT battery_hours, material, disk_storage FROM laptops LIMIT 5')
print("\nRaw Data:")
print(cur.fetchall())
