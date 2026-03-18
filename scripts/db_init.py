import sqlite3
from pathlib import Path 

def db_setup():
    db_path = Path(__file__).parent.parent / "data" / "budget.db" #this gives the path budget.db

    conn = sqlite3.connect(db_path)

    curs = conn.cursor()
    curs.execute("PRAGMA foreign_keys = ON;") #turns on the usage of foreign_keys



#creates the categories table, the primary key used for lookup will be the ID
    curs.execute("""CREATE TABLE IF NOT EXISTS categories(
             id INTEGER PRIMARY KEY AUTOINCREMENT, 
             name TEXT UNIQUE NOT NULL)""")

##creates the transactions table
    curs.execute("""CREATE TABLE IF NOT EXISTS transactions(
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             amount REAL NOT NULL, 
             category_id INTEGER, 
             date_recorded DATE DEFAULT CURRENT_DATE, 
             description TEXT, 
             FOREIGN KEY(category_id) REFERENCES categories(id) )""")
    

    curs.execute("""CREATE TABLE IF NOT EXISTS budget(
                 id INTEGER PRIMARY KEY CHECK (id =1),
                 monthly_budget REAL DEFAULT 0.0,
                 total_budget REAL DEFAULT 0.0)""")
    
    curs.execute("INSERT OR IGNORE INTO budget (id, monthly_budget, total_budget) VALUES (1, 0.0, 0.0)")
    
    default_categories = default_categories = [
    (1, 'Income'), 
    (2, 'Groceries'),
    (3, 'Rent & Utilities'),  
    (4, 'Subscriptions'),
    (5, 'Transportation'), 
    (6, 'Education'),
    (7, 'Hobbies'),
    (8, 'Health & Care'),
    (9, 'Entertainment'),
    (10, 'Food'), 
    (11, 'Other'),
    (12, 'Continous Income')
    ]

    curs.executemany('INSERT OR IGNORE INTO categories(id,name) VALUES (?, ?)',default_categories)

    conn.commit()
    conn.close()



