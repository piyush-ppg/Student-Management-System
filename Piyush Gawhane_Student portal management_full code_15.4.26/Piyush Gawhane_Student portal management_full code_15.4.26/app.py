from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from functools import wraps
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database connection function
def get_db():
    conn = sqlite3.connect('student_management.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database initialization function
def init_db():
    """Initialize the database with all required tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            student_id INTEGER
        )
    ''')
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Study materials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            file_path TEXT NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            uploaded_by INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id),
            UNIQUE(student_id, date)
        )
    ''')
    
    # Marks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            test_name TEXT NOT NULL,
            marks_obtained INTEGER NOT NULL,
            total_marks INTEGER NOT NULL,
            test_date DATE NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    # Exam timetable table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            subject TEXT NOT NULL,
            exam_date DATE NOT NULL,
            exam_time TEXT NOT NULL,
            venue TEXT NOT NULL
        )
    ''')
    
    # Quiz questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL
        )
    ''')
    
    # Quiz Results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_winner BOOLEAN DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    # Winners table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL,
            quiz_result_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            percentage REAL NOT NULL,
            declared_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            prize_rank TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (quiz_result_id) REFERENCES quiz_results (id)
        )
    ''')
    
    # Insert default admin if not exists
    admin_exists = cursor.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin_exists:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      ('admin', 'admin123', 'admin'))
    
    # Insert sample student for testing
    student_exists = cursor.execute("SELECT * FROM students WHERE roll_number = 'CS2024001'").fetchone()
    if not student_exists:
        cursor.execute('''
            INSERT INTO students (name, email, roll_number, course, semester)
            VALUES (?, ?, ?, ?, ?)
        ''', ('John Doe', 'john@example.com', 'CS2024001', 'Computer Science', 3))
        
        student_id = cursor.lastrowid
        cursor.execute("INSERT INTO users (username, password, role, student_id) VALUES (?, ?, ?, ?)",
                      ('john', 'student123', 'student', student_id))
    
    # Insert sample exam timetable
    timetable_exists = cursor.execute("SELECT * FROM exam_timetable").fetchone()
    if not timetable_exists:
        cursor.executemany('''
            INSERT INTO exam_timetable (course, semester, subject, exam_date, exam_time, venue)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            ('Computer Science', 3, 'Data Structures', '2026-05-15', '10:00 AM - 01:00 PM', 'Hall A'),
            ('Computer Science', 3, 'Database Systems', '2026-05-18', '10:00 AM - 01:00 PM', 'Hall B'),
            ('Computer Science', 3, 'Operating Systems', '2026-05-22', '10:00 AM - 01:00 PM', 'Hall A'),
        ])
    
    # Insert sample quiz questions
    quiz_exists = cursor.execute("SELECT * FROM quiz_questions").fetchone()
    if not quiz_exists:
        cursor.executemany('''
            INSERT INTO quiz_questions (course, semester, question, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('Computer Science', 3, 'What is a primary key?', 
             'A key that uniquely identifies each record', 'A key used for encryption', 'A foreign key reference', 'An index key', 'A'),
            ('Computer Science', 3, 'Which of the following is a Python framework?',
             'Django', 'React', 'Angular', 'Vue.js', 'A'),
            ('Computer Science', 3, 'What does SQL stand for?',
             'Structured Query Language', 'Simple Query Language', 'Standard Query Language', 'Sequential Query Language', 'A'),
        ])
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        roll_number = request.form['roll_number']
        course = request.form['course']
        semester = request.form['semester']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Insert student
            cursor.execute('''
                INSERT INTO students (name, email, roll_number, course, semester)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, roll_number, course, semester))
            
            student_id = cursor.lastrowid
            
            # Create user account
            cursor.execute('''
                INSERT INTO users (username, password, role, student_id)
                VALUES (?, ?, ?, ?)
            ''', (roll_number, password, 'student', student_id))
            
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('Student with this email or roll number already exists!', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                           (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['student_id'] = user['student_id']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db()
    
    total_students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    total_materials = conn.execute('SELECT COUNT(*) as count FROM study_materials').fetchone()['count']
    total_quizzes = conn.execute('SELECT COUNT(*) as count FROM quiz_questions').fetchone()['count']
    
    recent_students = conn.execute('''
        SELECT * FROM students ORDER BY created_at DESC LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_students=total_students,
                         total_materials=total_materials,
                         total_quizzes=total_quizzes,
                         recent_students=recent_students)

@app.route('/admin/add_student', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        roll_number = request.form['roll_number']
        course = request.form['course']
        semester = request.form['semester']
        password = request.form['password']
        
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (name, email, roll_number, course, semester)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, roll_number, course, semester))
            
            student_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO users (username, password, role, student_id)
                VALUES (?, ?, ?, ?)
            ''', (roll_number, password, 'student', student_id))
            
            conn.commit()
            flash('Student added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Student with this email or roll number already exists!', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_student.html')

@app.route('/admin/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    conn = get_db()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        course = request.form['course']
        semester = request.form['semester']
        
        conn.execute('''
            UPDATE students SET name = ?, email = ?, course = ?, semester = ?
            WHERE id = ?
        ''', (name, email, course, semester, student_id))
        conn.commit()
        conn.close()
        
        flash('Student updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    
    return render_template('edit_student.html', student=student)

@app.route('/admin/upload_material', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_material():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        course = request.form['course']
        semester = request.form['semester']
        
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            conn = get_db()
            conn.execute('''
                INSERT INTO study_materials (title, description, file_path, course, semester, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, description, file_path, course, semester, session['user_id']))
            conn.commit()
            conn.close()
            
            flash('Study material uploaded successfully!', 'success')
        else:
            flash('Please select a file to upload!', 'danger')
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('manage_materials.html')

@app.route('/admin/mark_attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def mark_attendance():
    conn = get_db()
    
    if request.method == 'POST':
        attendance_date = request.form['attendance_date']
        students = conn.execute('SELECT id, name FROM students').fetchall()
        
        for student in students:
            status = request.form.get(f'attendance_{student["id"]}', 'absent')
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO attendance (student_id, date, status)
                    VALUES (?, ?, ?)
                ''', (student['id'], attendance_date, status))
            except:
                pass
        
        conn.commit()
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    students = conn.execute('SELECT id, name, roll_number FROM students').fetchall()
    conn.close()
    
    return render_template('manage_attendance.html', students=students, today=date.today())

@app.route('/admin/enter_marks', methods=['GET', 'POST'])
@login_required
@admin_required
def enter_marks():
    conn = get_db()
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        test_name = request.form['test_name']
        marks_obtained = request.form['marks_obtained']
        total_marks = request.form['total_marks']
        test_date = request.form['test_date']
        
        conn.execute('''
            INSERT INTO marks (student_id, subject, test_name, marks_obtained, total_marks, test_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, subject, test_name, marks_obtained, total_marks, test_date))
        conn.commit()
        conn.close()
        
        flash('Marks entered successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    students = conn.execute('SELECT id, name, roll_number FROM students').fetchall()
    conn.close()
    
    return render_template('manage_marks.html', students=students)

# Admin Quiz Management Routes
@app.route('/admin/manage_quizzes')
@login_required
@admin_required
def manage_quizzes():
    conn = get_db()
    quizzes = conn.execute('''
        SELECT * FROM quiz_questions ORDER BY course, semester, id
    ''').fetchall()
    conn.close()
    return render_template('manage_quizzes.html', quizzes=quizzes)

@app.route('/admin/add_quiz', methods=['GET', 'POST'])
@login_required
@admin_required
def add_quiz():
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        question = request.form['question']
        option_a = request.form['option_a']
        option_b = request.form['option_b']
        option_c = request.form['option_c']
        option_d = request.form['option_d']
        correct_answer = request.form['correct_answer']
        
        conn = get_db()
        conn.execute('''
            INSERT INTO quiz_questions (course, semester, question, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course, semester, question, option_a, option_b, option_c, option_d, correct_answer))
        conn.commit()
        conn.close()
        
        flash('Quiz question added successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    return render_template('add_quiz.html')

@app.route('/admin/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_quiz(quiz_id):
    conn = get_db()
    
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        question = request.form['question']
        option_a = request.form['option_a']
        option_b = request.form['option_b']
        option_c = request.form['option_c']
        option_d = request.form['option_d']
        correct_answer = request.form['correct_answer']
        
        conn.execute('''
            UPDATE quiz_questions 
            SET course = ?, semester = ?, question = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_answer = ?
            WHERE id = ?
        ''', (course, semester, question, option_a, option_b, option_c, option_d, correct_answer, quiz_id))
        conn.commit()
        conn.close()
        
        flash('Quiz question updated successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    quiz = conn.execute('SELECT * FROM quiz_questions WHERE id = ?', (quiz_id,)).fetchone()
    conn.close()
    
    return render_template('edit_quiz.html', quiz=quiz)

@app.route('/admin/delete_quiz/<int:quiz_id>')
@login_required
@admin_required
def delete_quiz(quiz_id):
    conn = get_db()
    conn.execute('DELETE FROM quiz_questions WHERE id = ?', (quiz_id,))
    conn.commit()
    conn.close()
    
    flash('Quiz question deleted successfully!', 'success')
    return redirect(url_for('manage_quizzes'))

# Admin Exam Timetable Management Routes
@app.route('/admin/manage_timetables')
@login_required
@admin_required
def manage_timetables():
    conn = get_db()
    timetables = conn.execute('''
        SELECT * FROM exam_timetable ORDER BY course, semester, exam_date
    ''').fetchall()
    conn.close()
    return render_template('manage_timetables.html', timetables=timetables)

@app.route('/admin/add_timetable', methods=['GET', 'POST'])
@login_required
@admin_required
def add_timetable():
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        exam_date = request.form['exam_date']
        exam_time = request.form['exam_time']
        venue = request.form['venue']
        
        conn = get_db()
        conn.execute('''
            INSERT INTO exam_timetable (course, semester, subject, exam_date, exam_time, venue)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (course, semester, subject, exam_date, exam_time, venue))
        conn.commit()
        conn.close()
        
        flash('Exam timetable entry added successfully!', 'success')
        return redirect(url_for('manage_timetables'))
    
    return render_template('add_timetable.html')

@app.route('/admin/edit_timetable/<int:timetable_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_timetable(timetable_id):
    conn = get_db()
    
    if request.method == 'POST':
        course = request.form['course']
        semester = request.form['semester']
        subject = request.form['subject']
        exam_date = request.form['exam_date']
        exam_time = request.form['exam_time']
        venue = request.form['venue']
        
        conn.execute('''
            UPDATE exam_timetable 
            SET course = ?, semester = ?, subject = ?, exam_date = ?, exam_time = ?, venue = ?
            WHERE id = ?
        ''', (course, semester, subject, exam_date, exam_time, venue, timetable_id))
        conn.commit()
        conn.close()
        
        flash('Exam timetable updated successfully!', 'success')
        return redirect(url_for('manage_timetables'))
    
    timetable = conn.execute('SELECT * FROM exam_timetable WHERE id = ?', (timetable_id,)).fetchone()
    conn.close()
    
    return render_template('edit_timetable.html', timetable=timetable)

@app.route('/admin/delete_timetable/<int:timetable_id>')
@login_required
@admin_required
def delete_timetable(timetable_id):
    conn = get_db()
    conn.execute('DELETE FROM exam_timetable WHERE id = ?', (timetable_id,))
    conn.commit()
    conn.close()
    
    flash('Exam timetable entry deleted successfully!', 'success')
    return redirect(url_for('manage_timetables'))

@app.route('/admin/quiz_results')
@login_required
@admin_required
def admin_quiz_results():
    conn = get_db()
    
    # Get filter parameters
    course_filter = request.args.get('course', '')
    semester_filter = request.args.get('semester', '')
    
    # Get all quiz results - NO filters by default
    query = '''
        SELECT qr.*, 
               CASE WHEN w.id IS NOT NULL THEN 1 ELSE 0 END as is_declared_winner
        FROM quiz_results qr
        LEFT JOIN winners w ON qr.id = w.quiz_result_id
        WHERE 1=1
    '''
    params = []
    
    if course_filter and course_filter != '':
        query += " AND qr.course = ?"
        params.append(course_filter)
    if semester_filter and semester_filter != '':
        query += " AND qr.semester = ?"
        params.append(semester_filter)
    
    query += " ORDER BY qr.completed_at DESC, qr.percentage DESC"
    
    results = conn.execute(query, params).fetchall()
    
    # Get unique courses and semesters for filters
    courses = conn.execute('SELECT DISTINCT course FROM quiz_results').fetchall()
    semesters = conn.execute('SELECT DISTINCT semester FROM quiz_results ORDER BY semester').fetchall()
    
    # Debug: Print to console
    print(f"Found {len(results)} quiz results")
    for r in results:
        print(f"Result: {r['student_name']} - Score: {r['score']}/{r['total_questions']} - Winner: {r['is_declared_winner']}")
    
    conn.close()
    
    return render_template('admin_quiz_results.html', 
                         results=results, 
                         courses=courses, 
                         semesters=semesters,
                         course_filter=course_filter,
                         semester_filter=semester_filter)

@app.route('/admin/declare_winner/<int:result_id>', methods=['POST'])
@login_required
@admin_required
def declare_winner(result_id):
    prize_rank = request.form.get('prize_rank', 'Winner')
    
    conn = get_db()
    
    # Get quiz result details
    result = conn.execute('SELECT * FROM quiz_results WHERE id = ?', (result_id,)).fetchone()
    
    if result:
        # Check if already declared as winner
        existing_winner = conn.execute('SELECT * FROM winners WHERE quiz_result_id = ?', (result_id,)).fetchone()
        
        if not existing_winner:
            # Insert into winners table
            conn.execute('''
                INSERT INTO winners (student_id, student_name, roll_number, course, semester, 
                                   quiz_result_id, score, percentage, prize_rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (result['student_id'], result['student_name'], result['roll_number'], 
                  result['course'], result['semester'], result_id, result['score'], 
                  result['percentage'], prize_rank))
            
            # Update quiz_results to mark as winner
            conn.execute('UPDATE quiz_results SET is_winner = 1 WHERE id = ?', (result_id,))
            
            conn.commit()
            flash(f'{result["student_name"]} declared as {prize_rank}!', 'success')
        else:
            flash('This student has already been declared as a winner!', 'warning')
    
    conn.close()
    return redirect(url_for('admin_quiz_results'))

@app.route('/admin/winners')
@login_required
@admin_required
def view_winners():
    conn = get_db()
    winners = conn.execute('''
        SELECT * FROM winners 
        ORDER BY declared_on DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_winners.html', winners=winners)

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db()
    
    # Get student details
    student = conn.execute('''
        SELECT * FROM students WHERE id = ?
    ''', (session['student_id'],)).fetchone()
    
    # Get attendance summary
    attendance = conn.execute('''
        SELECT status, COUNT(*) as count FROM attendance 
        WHERE student_id = ? GROUP BY status
    ''', (session['student_id'],)).fetchall()
    
    # Get marks
    marks = conn.execute('''
        SELECT * FROM marks WHERE student_id = ? ORDER BY test_date DESC LIMIT 5
    ''', (session['student_id'],)).fetchall()
    
    # Get recent winners
    recent_winners = conn.execute('''
        SELECT * FROM winners 
        ORDER BY declared_on DESC 
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('student_dashboard.html', 
                         student=student, 
                         attendance=attendance,
                         marks=marks,
                         recent_winners=recent_winners)

@app.route('/student/materials')
@login_required
def view_materials():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db()
    student = conn.execute('SELECT course, semester FROM students WHERE id = ?', 
                          (session['student_id'],)).fetchone()
    
    materials = conn.execute('''
        SELECT * FROM study_materials 
        WHERE course = ? AND semester = ?
        ORDER BY upload_date DESC
    ''', (student['course'], student['semester'])).fetchall()
    conn.close()
    
    return render_template('view_materials.html', materials=materials)

@app.route('/student/download/<int:material_id>')
@login_required
def download_material(material_id):
    conn = get_db()
    material = conn.execute('SELECT * FROM study_materials WHERE id = ?', 
                           (material_id,)).fetchone()
    conn.close()
    
    if material:
        return send_file(material['file_path'], as_attachment=True)
    else:
        flash('File not found!', 'danger')
        return redirect(url_for('view_materials'))

@app.route('/student/timetable')
@login_required
def view_timetable():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db()
    student = conn.execute('SELECT course, semester FROM students WHERE id = ?', 
                          (session['student_id'],)).fetchone()
    
    # Get timetable for student's course and semester
    timetable = conn.execute('''
        SELECT * FROM exam_timetable 
        WHERE course = ? AND semester = ?
        ORDER BY exam_date
    ''', (student['course'], student['semester'])).fetchall()
    
    # Also get all available timetables for debugging/info
    all_timetables = conn.execute('SELECT DISTINCT course, semester FROM exam_timetable').fetchall()
    
    conn.close()
    
    return render_template('exam_timetable.html', 
                         timetable=timetable, 
                         student=student,
                         all_timetables=all_timetables)

@app.route('/student/quiz', methods=['GET', 'POST'])
@login_required
def take_quiz():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))
    
    conn = get_db()
    student = conn.execute('SELECT id, name, roll_number, course, semester FROM students WHERE id = ?', 
                          (session['student_id'],)).fetchone()
    
    if request.method == 'POST':
        score = 0
        total = 0
        
        for key, value in request.form.items():
            if key.startswith('q_'):
                total += 1
                question_id = int(key.split('_')[1])
                correct_answer = conn.execute('SELECT correct_answer FROM quiz_questions WHERE id = ?', 
                                             (question_id,)).fetchone()
                if correct_answer and value == correct_answer['correct_answer']:
                    score += 1
        
        percentage = (score / total) * 100 if total > 0 else 0
        
        # Save quiz result
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO quiz_results (student_id, student_name, roll_number, course, semester, score, total_questions, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student['id'], student['name'], student['roll_number'], student['course'], 
              student['semester'], score, total, percentage))
        
        # Get the result ID
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        flash(f'Quiz completed! Your score: {score}/{total} ({percentage:.1f}%)', 'success')
        return redirect(url_for('quiz_result', result_id=result_id))
    
    # Get questions for student's course and semester
    questions = conn.execute('''
        SELECT * FROM quiz_questions 
        WHERE course = ? AND semester = ?
        ORDER BY RANDOM() LIMIT 10
    ''', (student['course'], student['semester'])).fetchall()
    conn.close()
    
    if not questions:
        flash('No quiz questions available for your course and semester yet.', 'info')
        return redirect(url_for('student_dashboard'))
    
    return render_template('quiz.html', questions=questions)

@app.route('/student/quiz_result/<int:result_id>')
@login_required
def quiz_result(result_id):
    conn = get_db()
    result = conn.execute('''
        SELECT * FROM quiz_results WHERE id = ? AND student_id = ?
    ''', (result_id, session['student_id'])).fetchone()
    conn.close()
    
    if not result:
        flash('Quiz result not found!', 'danger')
        return redirect(url_for('student_dashboard'))
    
    return render_template('quiz_result.html', result=result)

@app.route('/student/quiz_history')
@login_required
def quiz_history():
    conn = get_db()
    history = conn.execute('''
        SELECT * FROM quiz_results 
        WHERE student_id = ? 
        ORDER BY completed_at DESC
    ''', (session['student_id'],)).fetchall()
    conn.close()
    
    return render_template('quiz_history.html', history=history)

@app.route('/student/leaderboard')
@login_required
def leaderboard():
    conn = get_db()
    
    # Get top performers
    top_performers = conn.execute('''
        SELECT student_name, roll_number, course, semester, 
               MAX(percentage) as best_percentage,
               COUNT(*) as quizzes_taken,
               AVG(percentage) as avg_percentage
        FROM quiz_results
        GROUP BY student_id
        ORDER BY best_percentage DESC
        LIMIT 10
    ''').fetchall()
    
    # Get declared winners
    winners = conn.execute('''
        SELECT * FROM winners 
        ORDER BY declared_on DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('leaderboard.html', 
                         top_performers=top_performers, 
                         winners=winners)

if __name__ == '__main__':
    # Initialize database before starting the app
    init_db()
    app.run(debug=True)