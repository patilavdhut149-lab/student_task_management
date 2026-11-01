from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from db_config import get_db_connection

app = Flask(__name__)
app.secret_key = "student_task_manager_secret_key"


# ==========================
# DATABASE SETUP / MIGRATION
# ==========================
def ensure_database_updates():
    """Create the student login table and add task status if they do not exist."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_accounts (
            account_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_student_account
                FOREIGN KEY (student_id) REFERENCES students(student_id)
                ON DELETE CASCADE
        )
    """)

    # Check whether status already exists in student_tasks.
    cursor.execute("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'student_tasks'
          AND COLUMN_NAME = 'status'
    """)
    status_exists = cursor.fetchone()[0]

    if not status_exists:
        cursor.execute("""
            ALTER TABLE student_tasks
            ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        """)

    connection.commit()
    cursor.close()
    connection.close()


# Run the small migration when the application starts.
try:
    ensure_database_updates()
except Exception as exc:
    # The application can still start; a clear error will be shown when a
    # database-backed page is opened if the database is unavailable.
    print("Database setup warning:", exc)


# ==========================
# ACCESS CONTROL
# ==========================
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('user') != 'admin':
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('student_id'):
            return redirect(url_for('student_login'))
        return view(*args, **kwargs)
    return wrapped


# ==========================
# HOME
# ==========================
@app.route('/')
def home():
    if session.get('user') == 'admin':
        return redirect(url_for('dashboard'))
    if session.get('student_id'):
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


# ==========================
# ADMIN / USER LOGIN
# ==========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            session.clear()
            session['user'] = username
            return redirect(url_for('dashboard'))

        flash('Invalid Username or Password', 'danger')

    return render_template('login.html')


# ==========================
# STUDENT LOGIN
# ==========================
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT sa.student_id, sa.username, sa.password_hash,
                   s.first_name, s.last_name
            FROM student_accounts sa
            JOIN students s ON s.student_id = sa.student_id
            WHERE sa.username = %s
        """, (username,))
        account = cursor.fetchone()
        cursor.close()
        connection.close()

        if account and check_password_hash(account['password_hash'], password):
            session.clear()
            session['student_id'] = account['student_id']
            session['student_username'] = account['username']
            session['student_name'] = f"{account['first_name']} {account['last_name']}"
            return redirect(url_for('student_dashboard'))

        flash('Invalid Student Username or Password', 'danger')

    return render_template('student_login.html')


# ==========================
# ADMIN DASHBOARD
# ==========================
@app.route('/dashboard')
@admin_required
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks")
    task_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance")
    attendance_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM student_tasks")
    assignment_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM student_tasks WHERE status='Pending'")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM student_tasks WHERE status='Complete'")
    completed_count = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return render_template(
        'index.html',
        student_count=student_count,
        task_count=task_count,
        attendance_count=attendance_count,
        assignment_count=assignment_count,
        pending_count=pending_count,
        completed_count=completed_count
    )


# ==========================
# ADD STUDENT + STUDENT LOGIN ACCOUNT
# ==========================
@app.route('/add_student', methods=['GET', 'POST'])
@admin_required
def add_students():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        mobile_number = request.form['mobile_number']
        email = request.form['email']
        course_name = request.form['course_name']
        admission_date = request.form['admission_date']
        username = request.form['username'].strip()
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO students
                (first_name, last_name, gender, mobile_number, email,
                 course_name, admission_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                first_name, last_name, gender, mobile_number, email,
                course_name, admission_date
            ))

            student_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO student_accounts (student_id, username, password_hash)
                VALUES (%s,%s,%s)
            """, (student_id, username, generate_password_hash(password)))

            connection.commit()
            flash('Student and login account created successfully.', 'success')
            return redirect(url_for('students'))

        except Exception as exc:
            connection.rollback()
            flash(f'Unable to add student: {exc}', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('add_student.html')


# ==========================
# STUDENTS LIST
# ==========================
@app.route('/students')
@admin_required
def students():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.*,
               sa.username AS login_username
        FROM students s
        LEFT JOIN student_accounts sa ON sa.student_id = s.student_id
        ORDER BY s.student_id DESC
    """)
    students = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('students.html', students=students)


# ==========================
# CREATE / RESET STUDENT ACCOUNT
# ==========================
@app.route('/student_account/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def student_account(student_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        connection.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        try:
            cursor.execute("""
                INSERT INTO student_accounts (student_id, username, password_hash)
                VALUES (%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    username=VALUES(username),
                    password_hash=VALUES(password_hash)
            """, (student_id, username, generate_password_hash(password)))
            connection.commit()
            flash('Student login account saved successfully.', 'success')
            return redirect(url_for('students'))
        except Exception as exc:
            connection.rollback()
            flash(f'Unable to save account: {exc}', 'danger')

    cursor.execute("SELECT * FROM student_accounts WHERE student_id=%s", (student_id,))
    account = cursor.fetchone()

    cursor.close()
    connection.close()
    return render_template('student_account.html', student=student, account=account)


# ==========================
# EDIT STUDENT
# ==========================
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        cursor.execute("""
            UPDATE students
            SET first_name=%s, last_name=%s, gender=%s,
                mobile_number=%s, email=%s, course_name=%s
            WHERE student_id=%s
        """, (
            request.form['first_name'],
            request.form['last_name'],
            request.form['gender'],
            request.form['mobile_number'],
            request.form['email'],
            request.form['course_name'],
            student_id
        ))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for('students'))

    cursor.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    connection.close()

    return render_template('edit_student.html', student=student)


# ==========================
# DELETE STUDENT
# ==========================
@app.route('/delete_student/<int:student_id>')
@admin_required
def delete_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('students'))


# ==========================
# TASKS LIST
# ==========================
@app.route('/tasks')
@admin_required
def tasks():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks ORDER BY task_id DESC")
    tasks = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('tasks.html', tasks=tasks)


# ==========================
# ADD TASK
# ==========================
@app.route('/add_task', methods=['GET', 'POST'])
@admin_required
def add_task():
    if request.method == 'POST':
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO tasks (task_name, description, due_date)
            VALUES (%s,%s,%s)
        """, (
            request.form['task_name'],
            request.form['description'],
            request.form['due_date']
        ))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for('tasks'))

    return render_template('add_task.html')


# ==========================
# ASSIGN TASK TO STUDENT
# ==========================
@app.route('/assign_task', methods=['GET', 'POST'])
@admin_required
def assign_task():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        task_id = request.form['task_id']

        cursor.execute("""
            SELECT id FROM student_tasks
            WHERE student_id=%s AND task_id=%s
        """, (student_id, task_id))
        already_assigned = cursor.fetchone()

        if already_assigned:
            flash('This task is already assigned to the selected student.', 'warning')
        else:
            cursor.execute("""
                INSERT INTO student_tasks (student_id, task_id, status)
                VALUES (%s,%s,'Pending')
            """, (student_id, task_id))
            connection.commit()
            flash('Task assigned successfully. Status: Pending.', 'success')

        cursor.close()
        connection.close()
        return redirect(url_for('student_tasks'))

    cursor.execute("SELECT * FROM students ORDER BY first_name, last_name")
    students = cursor.fetchall()
    cursor.execute("SELECT * FROM tasks ORDER BY task_id DESC")
    tasks = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('assign_task.html', students=students, tasks=tasks)


# ==========================
# ADMIN: ALL ASSIGNED TASKS + STATUS
# ==========================
@app.route('/student_tasks')
@admin_required
def student_tasks():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            st.id,
            st.student_id,
            st.task_id,
            s.first_name,
            s.last_name,
            t.task_name,
            t.description,
            t.due_date,
            st.status
        FROM student_tasks st
        JOIN students s ON st.student_id=s.student_id
        JOIN tasks t ON st.task_id=t.task_id
        ORDER BY st.id DESC
    """)
    assigned_tasks = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('student_tasks.html', student_tasks=assigned_tasks)


# ==========================
# STUDENT DASHBOARD / ASSIGNED TASKS
# ==========================
@app.route('/student_dashboard')
@student_required
def student_dashboard():
    student_id = session['student_id']
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            st.id,
            t.task_id,
            t.task_name,
            t.description,
            t.due_date,
            st.status
        FROM student_tasks st
        JOIN tasks t ON st.task_id=t.task_id
        WHERE st.student_id=%s
        ORDER BY
            CASE WHEN st.status='Pending' THEN 0 ELSE 1 END,
            t.due_date ASC
    """, (student_id,))
    assigned_tasks = cursor.fetchall()

    total = len(assigned_tasks)
    completed = sum(1 for row in assigned_tasks if row['status'] == 'Complete')
    pending = total - completed

    cursor.close()
    connection.close()

    return render_template(
        'student_dashboard.html',
        assigned_tasks=assigned_tasks,
        total=total,
        completed=completed,
        pending=pending
    )


# ==========================
# STUDENT: MARK TASK COMPLETE
# ==========================
@app.route('/student_task/complete/<int:assignment_id>', methods=['POST'])
@student_required
def complete_student_task(assignment_id):
    student_id = session['student_id']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE student_tasks
        SET status='Complete'
        WHERE id=%s AND student_id=%s
    """, (assignment_id, student_id))
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('student_dashboard'))


# ==========================
# ATTENDANCE
# ==========================
@app.route('/attendance', methods=['GET', 'POST'])
@admin_required
def attendance():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO attendance (student_id, attendance_date, status)
            VALUES (%s,%s,%s)
        """, (
            request.form['student_id'],
            request.form['attendance_date'],
            request.form['status']
        ))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for('attendance_report'))

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('attendance.html', students=students)


# ==========================
# ATTENDANCE REPORT
# ==========================
@app.route('/attendance_report')
@admin_required
def attendance_report():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            a.attendance_id,
            s.first_name,
            s.last_name,
            a.attendance_date,
            a.status
        FROM attendance a
        JOIN students s ON a.student_id=s.student_id
        ORDER BY a.attendance_date DESC
    """)
    attendance_records = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('attendance_report.html', attendance_records=attendance_records)




# ==========================
# LOGOUT
# ==========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==========================
# RUN APP
# ==========================
if __name__ == '__main__':
    app.run(debug=True)

