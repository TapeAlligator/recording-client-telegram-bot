import sqlite3 as sq


def init_db():
    connection = sq.connect('clients.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            specialization TEXT,
            phone TEXT,
            email TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            time_m TEXT,
            master_id INTEGER,
            FOREIGN KEY(master_id) REFERENCES masters(id)
        )
    ''')

    connection.commit()
    cursor.close()
    connection.close()


def add_client(tg_id, name, phone=None, email=None, time_m=None, master_id=None):
    connection = sq.connect('clients.db')
    cursor = connection.cursor()
    cursor.execute('''INSERT INTO clients (tg_id, name, phone, email, time_m, master_id) VALUES (?, ?, ?, ?, ?, ?)''',
                   (tg_id, name, phone, email, time_m, master_id))
    connection.commit()
    cursor.close()
    connection.close()


def add_master(name, specialization=None, phone=None, email=None):
    connection = sq.connect('clients.db')
    cursor = connection.cursor()
    cursor.execute(
        '''INSERT INTO masters (name, specialization, phone, email) VALUES (?, ?, ?, ?)''',
        (name, specialization, phone, email)
    )
    connection.commit()
    cursor.close()
    connection.close()


def get_masters():
    connection = sq.connect('clients.db')
    cursor = connection.cursor()
    cursor.execute('SELECT id, name, specialization, phone, email FROM masters')
    masters = cursor.fetchall()
    cursor.close()
    connection.close()
    return masters

