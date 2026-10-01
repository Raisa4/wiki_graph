import sqlite3


def get_connection(db_name='wiki_graph.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # We handle table creation here now, ensuring they exist before any script runs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            title TEXT PRIMARY KEY,
            visited INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            source_title TEXT,
            target_title TEXT,
            UNIQUE(source_title, target_title)
        )
    ''')

    conn.commit()
    return conn