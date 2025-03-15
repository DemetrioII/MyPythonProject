import sqlite3

con = sqlite3.connect("DataBase.db")
cur = con.cursor()


def create_db():
    cur.execute("""CREATE TABLE "person" (
                    "id"	INTEGER NOT NULL UNIQUE,
                    "name"	,
                    "passhash"	,
                    PRIMARY KEY("id" AUTOINCREMENT)
                    );""")
    cur.execute("""CREATE TABLE "info" (
                "id",
                "reg_time",
                "last_auth"
                );""")


def get_hash(s):
    return "a"


def create_person(name, password):
    cur.execute("""
                INSERT INTO person VALUES
                (?, ?, ?)
                """, (1, name, get_hash(password)))
    con.commit()


# create_db()
create_person(name="Test", password="TestPass")
