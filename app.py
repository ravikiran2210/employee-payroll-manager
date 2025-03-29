from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import logging
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def create_connection():
    return sqlite3.connect("payroll_system.db")

def initialize_db():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Employee (
                        emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        department TEXT,
                        position TEXT,
                        basic_salary REAL,
                        contact TEXT,
                        email TEXT
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Admin (
                        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Salary (
                        salary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        emp_id INTEGER,
                        month TEXT,
                        year INTEGER,
                        basic_salary REAL,
                        deductions REAL,
                        overtime REAL,
                        total_salary REAL,
                        FOREIGN KEY(emp_id) REFERENCES Employee(emp_id)
                      )''')
    # Check if 'role' column exists in Admin table 
    conn.commit()
    conn.close()

initialize_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST']) 
def admin_login(): 
    if request.method == 'POST': 
        username = request.form['username'] 
        password = request.form['password'] 
        conn = create_connection() 
        cursor = conn.cursor() 
        cursor.execute("SELECT * FROM Admin WHERE username = ? AND password = ?", (username, password)) 
        admin = cursor.fetchone() 
        conn.close() 
        if admin: 
            session['admin'] = username 
            return redirect(url_for('admin_dashboard'))
        else: 
            return "Invalid Credentials" 
@app.route('/employee', methods=['POST']) 
def employee_login(): 
    emp_id = request.form['emp_id'] 
    conn = create_connection() 
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM Employee WHERE emp_id=?", (emp_id,)) 
    employee = cursor.fetchone() 
    conn.close() 
    if employee: 
        session['employee'] = emp_id 
        return redirect(url_for('employee_dashboard')) 
    else: 
        return "Invalid credentials"
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/employee/dashboard')
def employee_dashboard():
    if 'employee' not in session:
        return redirect(url_for('employee_login'))
    return render_template('employee_dashboard.html')

@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        data = request.form
        print("Form Data Received:", data)  # Debugging statement to check form data
        try:
            name = data['name']
            department = data['department']
            position = data['position']
            basic_salary = float(data['basic_salary'])
            contact = data['contact']
            email = data['email']
            is_admin=data['is_admin']
            print("is_admin",is_admin)
        except KeyError as e:
            print(f"KeyError: Missing form data for key {e}")  # Print error to console
            return f"KeyError: Missing form data for key {e}"
        
        try:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Employee (name, department, position, basic_salary, contact, email) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, department, position, basic_salary, contact, email))
            emp_id = cursor.lastrowid
            print("Employee ID:", emp_id)  # Debugging statement to check if employee ID is generated
            if is_admin=='yes':
                cursor.execute("INSERT INTO Admin (username, password) VALUES (?, 'password')", (name))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Database error: {e}")  # Print database error to console
            return f"Database error: {e}"
        except Exception as e:
            print(f"Exception in _query: {e}")  # Print any other exception to console
            return f"Exception in _query: {e}"

       
    return render_template('register_employee.html')

@app.route('/view_employees', methods=['GET'])
def view_employees():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT emp_id, name, department, position, basic_salary, contact, email FROM Employee")
    employees = cursor.fetchall()
    conn.close()
    
    return render_template('view_employees.html', employees=employees)


@app.route('/calculate_salary', methods=['GET', 'POST'])
def calculate_salary():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        emp_id = int(request.form['emp_id'])
        month = request.form['month']
        year = request.form['year']
        deductions = float(request.form['deductions'])
        overtime_hours = float(request.form['overtime_hours'])
        
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT basic_salary FROM Employee WHERE emp_id = ?", (emp_id,))
        basic_salary = cursor.fetchone()[0]
        
        overtime_rate = 20  # Example rate: $20 per overtime hour
        total_salary = basic_salary - deductions + (overtime_hours * overtime_rate)
        
        cursor.execute("INSERT INTO Salary (emp_id, month, year, basic_salary, deductions, overtime, total_salary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (emp_id, month, year, basic_salary, deductions, overtime_hours, total_salary))
        conn.commit()
        conn.close()
        
        return '<script>alert("Salary calculated successfully!"); window.location.href="/calculate_salary";</script>'
    return render_template('calculate_salary.html')



@app.route('/generate_pay_slip_admin', methods=['GET', 'POST']) 
def generate_pay_slip_admin(): 
    if 'admin' not in session: 
        return redirect(url_for('admin_login')) 
    if request.method == 'POST': 
        emp_id = int(request.form['emp_id']) 
        month = request.form['month'] 
        year = request.form['year'] 
        conn = create_connection() 
        cursor = conn.cursor() 
        cursor.execute("SELECT * FROM Salary WHERE emp_id = ? AND month = ? AND year = ?", (emp_id, month, year)) 
        salary = cursor.fetchone() 
        conn.close() 
        if salary: 
            return render_template('pay_slip.html', salary=salary) 
        else: 
            return "No salary data found for the specified period." 
    return render_template('generate_pay_slip_admin.html') 
@app.route('/generate_pay_slip', methods=['POST'])
def generate_pay_slip():
    if 'employee' not in session:
        return redirect(url_for('employee_login'))
    emp_id = session['employee']
    try:
        month = request.form['month']
        year = request.form['year']
    except KeyError as e:
        return f"KeyError: Missing form data for key {e}"

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Salary WHERE emp_id = ? AND month = ? AND year = ?", (emp_id, month, year))
    salary = cursor.fetchone()
    conn.close()

    if salary:
        return render_template('pay_slip-emp.html', salary=salary)
    else:
        return "No salary data available for the selected period."

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
