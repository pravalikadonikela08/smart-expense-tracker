import os
import mysql.connector

if os.getenv("MYSQLHOST"):
    conn = mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT"))
    )
else:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="expense_tracker"
    )

cursor = conn.cursor()