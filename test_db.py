import sqlite3
conn = sqlite3.connect('/app/data/projects.db')
print(conn.execute('SELECT provider, name, status, user_id FROM api_credential').fetchall())
print(conn.execute('SELECT provider, model, health_status, is_active FROM model_profile').fetchall())
