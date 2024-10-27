from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import timedelta
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

# Database configuration remains the same...
DB_HOST = "localhost"
DB_NAME = "sampledb"
DB_USER = "postgres"
DB_PASS = "password"

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Missing username or password', 'error')
            return render_template('login.html')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute("SELECT * FROM useraccount WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return render_template('login.html')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute("SELECT * FROM useraccount WHERE username=%s", (username,))
        if cursor.fetchone():
            flash('Username already exists', 'error')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO useraccount (username, password) VALUES (%s, %s)",
            (username, password_hash)
        )
        conn.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return render_template('register.html')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)