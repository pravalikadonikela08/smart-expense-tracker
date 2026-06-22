from flask import Flask, render_template, request, redirect, session
#from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import pandas as pd
from flask import send_file
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "expense_tracker_secret"

# Database Connection
conn = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT"))
)

cursor = conn.cursor()


# Home Page
@app.route('/')
def home():
    return render_template('index.html')


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']


        sql = """
        INSERT INTO users(name,email,password)
        VALUES(%s,%s,%s)
        """

        values = (name, email, password)

        cursor.execute(sql, values)
        conn.commit()

        return redirect('/login')

    return render_template('register.html')


# Login
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        sql = """
        SELECT * FROM users
        WHERE email=%s
        """

        values = (email,)

        cursor.execute(sql, values)

        user = cursor.fetchone()

        if user:

            session['user_id'] = user[0]
            session['user_name'] = user[1]

            return redirect('/dashboard')

        return "Invalid Email or Password!"

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Total Records
    cursor.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id=%s",
        (user_id,)
    )
    total_records = cursor.fetchone()[0]

    # Total Expense
    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=%s",
        (user_id,)
    )
    total_expense = cursor.fetchone()[0]

    if total_expense is None:
        total_expense = 0

    # Pie Chart Data
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE user_id=%s
        GROUP BY category
    """, (user_id,))

    chart_data = cursor.fetchall()

    # Monthly Report
    cursor.execute("""
        SELECT DATE_FORMAT(expense_date, '%M %Y') AS month,
               SUM(amount)
        FROM expenses
        WHERE user_id=%s
        GROUP BY DATE_FORMAT(expense_date, '%M %Y')
        ORDER BY MIN(expense_date)
    """, (user_id,))

    monthly_data = cursor.fetchall()

    # Budget
    cursor.execute(
        "SELECT budget_amount FROM budget WHERE user_id=%s",
        (user_id,)
    )

    budget = cursor.fetchone()

    budget_amount = 0

    if budget:
        budget_amount = float(budget[0])

    budget_message = ""

    if total_expense > budget_amount and budget_amount > 0:
        budget_message = "⚠ Budget Exceeded!"

    # Chart Lists
    categories = []
    amounts = []

    for row in chart_data:
        categories.append(row[0])
        amounts.append(float(row[1]))

    return render_template(
        'dashboard.html',
        total_records=total_records,
        total_expense=total_expense,
        categories=categories,
        amounts=amounts,
        budget_amount=budget_amount,
        budget_message=budget_message,
        monthly_data=monthly_data
    )
    
    
# Add Expense
# Add Expense
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        user_id = session['user_id']

        category = request.form['category']
        amount = request.form['amount']
        description = request.form['description']

        sql = """
        INSERT INTO expenses(
            user_id,
            category,
            amount,
            description,
            expense_date
        )
        VALUES(%s,%s,%s,%s,CURDATE())
        """

        values = (
            user_id,
            category,
            amount,
            description
        )

        cursor.execute(sql, values)
        conn.commit()

        return redirect('/view_expenses')

    return render_template('add_expense.html')


# View Expenses
@app.route('/view_expenses')
def view_expenses():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    search = request.args.get('search', '')

    if search:

        cursor.execute("""
            SELECT id, category, amount, description
            FROM expenses
            WHERE user_id=%s
            AND category LIKE %s
        """, (user_id, f"%{search}%"))

    else:

        cursor.execute("""
            SELECT id, category, amount, description
            FROM expenses
            WHERE user_id=%s
        """, (user_id,))

    expenses = cursor.fetchall()

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=%s",
        (user_id,)
    )

    total = cursor.fetchone()[0]

    if total is None:
        total = 0

    return render_template(
        'view_expenses.html',
        expenses=expenses,
        total=total
    )
    
# Delete Expense
@app.route('/delete_expense/<int:id>')
def delete_expense(id):

    cursor.execute(
        "DELETE FROM expenses WHERE id=%s",
        (id,)
    )

    conn.commit()

    return redirect('/view_expenses')


# Edit Expense
@app.route('/edit_expense/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):

    if request.method == 'POST':

        category = request.form['category']
        amount = request.form['amount']
        description = request.form['description']

        sql = """
        UPDATE expenses
        SET category=%s,
            amount=%s,
            description=%s
        WHERE id=%s
        """

        values = (
            category,
            amount,
            description,
            id
        )

        cursor.execute(sql, values)
        conn.commit()

        return redirect('/view_expenses')

    cursor.execute(
        "SELECT * FROM expenses WHERE id=%s",
        (id,)
    )

    expense = cursor.fetchone()

    return render_template(
        'edit_expense.html',
        expense=expense
    )
    
#logout
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

#budget
@app.route('/set_budget', methods=['GET', 'POST'])
def set_budget():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        budget_amount = request.form['budget_amount']
        user_id = session['user_id']

        cursor.execute(
            "DELETE FROM budget WHERE user_id=%s",
            (user_id,)
        )

        cursor.execute(
            "INSERT INTO budget(user_id, budget_amount) VALUES(%s,%s)",
            (user_id, budget_amount)
        )

        conn.commit()

        return redirect('/dashboard')

    return render_template('set_budget.html')

#excel
@app.route('/export_excel')
def export_excel():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute("""
        SELECT category, amount, description
        FROM expenses
        WHERE user_id=%s
    """, (user_id,))

    data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=['Category', 'Amount', 'Description']
    )

    file_name = "expenses.xlsx"

    df.to_excel(file_name, index=False)

    return send_file(
        file_name,
        as_attachment=True
    )
#pdf export
@app.route('/export_pdf')
def export_pdf():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute("""
        SELECT category, amount, description
        FROM expenses
        WHERE user_id=%s
    """, (user_id,))

    expenses = cursor.fetchall()

    pdf_file = "expense_report.pdf"

    c = canvas.Canvas(pdf_file)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(180, 800, "Expense Report")

    y = 760

    c.setFont("Helvetica", 12)

    for expense in expenses:

        line = f"{expense[0]} | ₹{expense[1]} | {expense[2]}"

        c.drawString(50, y, line)

        y -= 25

        if y < 50:
            c.showPage()
            y = 800

    c.save()

    return send_file(
        pdf_file,
        as_attachment=True
    )
    
#profile
@app.route('/profile')
def profile():

    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        "SELECT name, email FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id=%s",
        (user_id,)
    )

    total_records = cursor.fetchone()[0]

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id=%s",
        (user_id,)
    )

    total_expense = cursor.fetchone()[0]

    if total_expense is None:
        total_expense = 0

    return render_template(
        'profile.html',
        user=user,
        total_records=total_records,
        total_expense=total_expense
    )


if __name__ == "__main__":
    app.run(debug=True)