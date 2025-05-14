import sqlite3
import datetime


class Database:
    def __init__(self):
        self.con = sqlite3.connect("DataBase.db")
        self.cur = self.con.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "person" (
                        "id"	INTEGER NOT NULL UNIQUE,
                        "name"	TEXT NOT NULL,
                        "passhash"	TEXT NOT NULL,
                        "image" BLOB NOT NULL,
                        "disabled" BOOLEAN,
                        "vk_id" INTEGER,
                        PRIMARY KEY("id" AUTOINCREMENT)
                        );""")
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "info" (
                        "id" INTEGER NOT NULL UNIQUE,
                        "reg_time" DATETIME DEFAULT CURRENT_TIMESTAMP,
                        "last_auth" DATETIME,
                        PRIMARY KEY ("id" AUTOINCREMENT)
                        );""")
        self.con.commit()

    def create_person(self, name, password, image, disabled):
        self.cur.execute("""INSERT INTO person (name, passhash, image, disabled, vk_id) VALUES
                    (?, ?, ?, ?, 0)
                    """, (name, password, image, disabled))
        self.cur.execute("""INSERT INTO info (reg_time, last_auth) VALUES
                    (?, ?)""", (str(datetime.datetime.now()), str(datetime.datetime.now())))
        self.con.commit()

    def __get_by_id(self, id: int):
        get_response = self.cur.execute("""
                                    SELECT * FROM (SELECT id, reg_time, last_auth FROM info) RIGHT JOIN person ON person.id = ?""",
                                        str(id))
        return get_response.fetchone()

    def find_by_name(self, name: str):
        fid = self.cur.execute("""SELECT * FROM person WHERE name = ?""", (name,)).fetchone()
        if fid:
            return fid
            get_response = self.__get_by_id(int(fid))
            return get_response

    def delete_by_name(self, name: str):
        try:
            id = self.cur.execute("""
                SELECT * FROM person WHERE name = ?
            """, (name,)).fetchone()[0]
            self.__delete_person(id)
            return True
        except Exception as e:
            print(e)
            return False

    def __delete_person(self, id: int):
        self.cur.execute("""
            DELETE FROM info WHERE id = ?
        """, (str(id),))
        self.cur.execute("""
            DELETE FROM person WHERE id = ?
        """, (str(id),))
        self.con.commit()

    def close(self):
        self.con.close()
