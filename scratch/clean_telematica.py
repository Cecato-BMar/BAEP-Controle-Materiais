import sqlite3
import os

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List of tables to drop (old telematica tables)
    tables = [
        'telematica_dispositivogps',
        'telematica_registrotelemetria',
        'telematica_alertatelematico',
        'telematica_percursoviatura',
        'telematica_geocercaarea',
        'telematica_infracaoregistrada',
        'telematica_manutencaodispositivo'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE {table}")
            print(f"Dropped {table}")
        except:
            print(f"Table {table} not found or error dropping.")
            
    # Also remove from django_migrations
    cursor.execute("DELETE FROM django_migrations WHERE app='telematica'")
    print("Cleared telematica from django_migrations")
    
    conn.commit()
    conn.close()
else:
    print("Database not found.")
