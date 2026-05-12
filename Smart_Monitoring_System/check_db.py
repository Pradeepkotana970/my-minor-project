import sqlite3
try:
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("Tables in monitoring.db:")
    for t in tables:
        print(f" - {t[0]}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals(): conn.close()
