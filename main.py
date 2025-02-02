from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
import smtplib
from email.mime.text import MIMEText
import random
import psycopg2
from psycopg2 import sql
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '__i__am__devsujeet__')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/dbname')

# Initialize the database
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# OTP management
otp_storage = {}

# Generate OTP
def generate_otp():
    return random.randint(100000, 999999)

# Send OTP via email
def send_email_otp(receiver_email):
    sender_email = "sujeetdey66@gmail.com"
    sender_password = os.getenv('EMAIL_PASSWORD')
    otp = generate_otp()
    msg = MIMEText(f"Your OTP is {otp}. Please use it within 5 minutes.")
    msg['Subject'] = 'Your OTP Code'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        otp_storage[receiver_email] = otp
        return otp
    except Exception as e:
        print(f"Failed to send OTP: {e}")
        return None

# User routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').lower()
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for('signup'))

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s OR username = %s', (email, username))
        if cursor.fetchone():
            flash("Username or email already exists!", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('signup'))

        sent_otp = send_email_otp(email)
        if sent_otp:
            flash("OTP sent! Please verify.", "success")
            return render_template('signup.html', otp_sent=True, email=email, username=username, password=password)
        else:
            flash("Failed to send OTP.", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email', '').strip().lower()
    otp = request.form.get('otp', '').strip()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()

    if not email or not otp or not username or not password:
        flash("All fields are required.", "error")
        return redirect(url_for('signup'))

    if email in otp_storage and otp_storage[email] == int(otp):
        hashed_password = generate_password_hash(password)
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                       (username, email, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        del otp_storage[email]
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('login'))
    else:
        flash("Invalid OTP. Please try again!", "error")
        return redirect(url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is already logged in via cookies
    username = request.cookies.get('username')
    if username:
        return redirect(url_for('home'))  # Redirect to home if the user is already logged in

    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            # Set cookies for persistent login
            resp = make_response(redirect(url_for('home')))
            expires = datetime.now() + timedelta(days=30)  # Cookie expires in 30 days
            resp.set_cookie('username', user[1], expires=expires)
            resp.set_cookie('user_id', str(user[0]), expires=expires)
            flash("Login successful!", "success")
            return resp
        else:
            flash("Invalid email or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie('username')
    resp.delete_cookie('user_id')
    flash("Logged out successfully.", "success")
    return resp

@app.route('/')
def home():
    user_id = request.cookies.get('user_id')
    username = request.cookies.get('username')
    if not user_id or not username:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, content, created_at FROM notes WHERE user_id = %s', (user_id,))
    notes = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('home.html', notes=notes, username=username)

@app.route('/add-note', methods=['GET', 'POST'])
def add_note():
    user_id = request.cookies.get('user_id')
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)', 
                       (user_id, title, content))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Note added!", "success")
        return redirect(url_for('home'))

    return render_template('add-note.html')

@app.route('/delete-note/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    user_id = request.cookies.get('user_id')
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for('login'))

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE id = %s AND user_id = %s', (note_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Note deleted successfully.", "success")
    return redirect(url_for('home'))

@app.route('/change-username', methods=['GET', 'POST'])
def change_username():
    user_id = request.cookies.get('user_id')
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_username = request.form['username'].lower()

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (new_username,))
        if cursor.fetchone():
            flash("Username already exists!", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('home'))

        cursor.execute('UPDATE users SET username = %s WHERE id = %s', (new_username, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        # Update the cookie with the new username
        resp = redirect(url_for('home'))
        resp.set_cookie('username', new_username, max_age=60*60*24*30)  # 30-day expiry
        flash("Username updated successfully!", "success")
        return resp

    return render_template('home.html')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    user_id = request.cookies.get('user_id')
    if not user_id:
        flash("Please log in first!", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("New passwords do not match!", "error")
            return redirect(url_for('home'))

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user[0], current_password):
            flash("Current password is incorrect!", "error")
            cursor.close()
            conn.close()
            return redirect(url_for('home'))

        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for('home'))

    return render_template('home.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)