import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import app
from app.extensions import db
from sqlalchemy import text

with app.app_context():
    with db.engine.begin() as conn:
        conn.execute(text("UPDATE brands SET code = LOWER(REGEXP_REPLACE(name, '\\s+', '-', 'g')) WHERE code IS NULL;"))
    print("Done")
