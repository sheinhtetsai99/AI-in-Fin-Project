from flask import Flask, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import timedelta
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# CRITICAL: Always set a secure secret key for sessions
app.config['SECRET_KEY'] = 'your-secure-secret-key-here'  # Change this to a secure random value
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

DB_HOST = "localhost"
DB_NAME = "sampledb"
DB_USER = "postgres"
DB_PASS = "password"

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        return jsonify({'message': 'You are already logged in', 'username': username})
    else:
        resp = jsonify({'message': 'Unauthorized'})
        resp.status_code = 401
        return resp

@app.route('/login', methods=['POST'])
def login():
    try:
        _json = request.json
        _username = _json.get('username')
        _password = _json.get('password')

        # Validate the received values
        if not _username or not _password:
            return jsonify({'message': 'Missing username or password'}), 400

        # Check user exists
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        sql = "SELECT * FROM useraccount WHERE username=%s"
        cursor.execute(sql, (_username,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'message': 'User not found'}), 404

        stored_password_hash = row['password']
        
        # Check if the provided password matches the stored hash
        if check_password_hash(stored_password_hash, _password):
            session['username'] = row['username']
            return jsonify({'message': 'You are logged in successfully'})
        else:
            return jsonify({'message': 'Invalid password'}), 401

    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
    return jsonify({'message': 'You successfully logged out'})

# Add a registration route to properly hash passwords when storing them
@app.route('/register', methods=['POST'])
def register():
    try:
        _json = request.json
        _username = _json.get('username')
        _password = _json.get('password')

        if not _username or not _password:
            return jsonify({'message': 'Missing username or password'}), 400

        # Generate password hash
        password_hash = generate_password_hash(_password)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Check if username already exists
        cursor.execute("SELECT * FROM useraccount WHERE username=%s", (_username,))
        if cursor.fetchone():
            return jsonify({'message': 'Username already exists'}), 409

        # Insert new user with hashed password
        print(f'hashed password: {password_hash}')
        sql = "INSERT INTO useraccount (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (_username, password_hash))
        conn.commit()

        return jsonify({'message': 'User registered successfully'}), 201

    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production