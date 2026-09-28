"""The same schema in SQLite: constraints only help if the database enforces them."""

import sqlite3
from pathlib import Path

schema = Path("schema.sql").read_text()
row = (172, "0702070001726", "Tahini 16 oz", "pantry", 6.49, "twelve", "count", 999)


def attempt(con, label):
    try:
        con.execute("INSERT INTO Suppliers VALUES (207, 'Heartland Pantry', NULL, NULL)")
        con.execute("INSERT INTO Products VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
        stored = con.execute("SELECT QuantityInStock, typeof(QuantityInStock) FROM Products").fetchone()
        print(f"{label:<42} accepted: QuantityInStock = {stored[0]!r} ({stored[1]}), supplier 999")
    except sqlite3.Error as e:
        print(f"{label:<42} rejected: {e}")


con = sqlite3.connect(":memory:")
con.executescript(schema)
attempt(con, "SQLite default")

con = sqlite3.connect(":memory:")
con.execute("PRAGMA foreign_keys = ON")
con.executescript(schema)
attempt(con, "SQLite with PRAGMA foreign_keys = ON")

con = sqlite3.connect(":memory:")
con.execute("PRAGMA foreign_keys = ON")
con.executescript(schema.replace(");", ") STRICT;").replace("VARCHAR(255)", "TEXT")
                  .replace("VARCHAR(50)", "TEXT").replace("VARCHAR(20)", "TEXT")
                  .replace("VARCHAR(13)", "TEXT").replace("VARCHAR(5)", "TEXT")
                  .replace("DECIMAL(10, 2)", "REAL").replace("DECIMAL(10, 3)", "REAL")
                  .replace("DATE", "TEXT"))
attempt(con, "SQLite STRICT tables + foreign keys")
