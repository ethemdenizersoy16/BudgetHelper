

def id_to_name(conn):
    curs = conn.cursor()

    curs.execute("SELECT name, id FROM categories")

    return {name: id for name, id in curs.fetchall()}

