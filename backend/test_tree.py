import sqlite3
import sys

conn = sqlite3.connect('../data/catalog.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("Testing root drive query...")
cursor.execute("""
    SELECT DISTINCT SUBSTR(path, 1, 3) as root_path
    FROM files
    WHERE LENGTH(path) > 2 AND SUBSTR(path, 2, 2) = ':\\'
    ORDER BY root_path
""")

roots = cursor.fetchall()
print(f"Found {len(roots)} drives:")
for row in roots:
    root = row[0] if isinstance(row, tuple) else row["root_path"]
    print(f"  - {root}")

conn.close()
