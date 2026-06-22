import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="expense_tracker"
)

print("Database Connected Successfully!")