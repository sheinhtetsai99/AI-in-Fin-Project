from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import timedelta
import psycopg2
import psycopg2.extras
from openai import OpenAI
import json
import os
import openai
from dotenv import load_dotenv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

load_dotenv()


client = openai.OpenAI(
    api_key= os.getenv('OPENAI_KEY')
)

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

@app.route('/transactions')
def transactions():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # First, get the latest balance
        cursor.execute("""
            SELECT balance_after as current_balance 
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC 
            LIMIT 1
        """, (session['username'],))
        
        balance_result = cursor.fetchone()
        current_balance = float(balance_result['current_balance']) if balance_result else 0.00
        
        # Then get all transactions
        cursor.execute("""
            SELECT 
                transaction_id,
                transaction_date,
                description,
                amount,
                transaction_type,
                balance_after,
                merchant_category_code,
                location,
                ip_address,
                device_id,
                transaction_method,
                status,
                risk_score,
                ai_reasoning,
                ai_flags,
                fraud_flag,
                merchant_name
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC
        """, (session['username'],))
        
        transactions = cursor.fetchall()

        return render_template('transactions.html', 
                             transactions=transactions,
                             current_balance=current_balance)

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/analyze_transaction/<int:transaction_id>')
def analyze_transaction_with_ai(transaction_id):
    """Use ChatGPT to analyze transaction and determine risk score"""
    try:
        # First, get the transaction details from the database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT 
                amount,
                transaction_type,
                location,
                merchant_name,
                transaction_method,
                device_id,
                ip_address,
                transaction_date
            FROM transactions 
            WHERE transaction_id = %s
        """, (transaction_id,))
        
        transaction = cursor.fetchone()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Construct a natural language description of the transaction
        transaction_description = f"""
        Please analyze this bank transaction for potential fraud and provide a risk score between 0-100:
        
        Transaction Details:
        - Amount: ${abs(float(transaction['amount']))}
        - Type: {transaction['transaction_type']}
        - Location: {transaction['location']}
        - Merchant: {transaction['merchant_name']}
        - Method: {transaction['transaction_method']}
        - Device ID: {transaction['device_id']}
        - IP Address: {transaction['ip_address']}
        - Time: {transaction['transaction_date']}
        
        Please respond in JSON format with the following structure:
        {{
            "risk_score": <number between 0-100>,
            "reasoning": "<brief explanation>",
            "flags": ["<any specific concerns>"]
        }}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fraud detection AI specializing in financial transactions. Analyze transactions and provide risk scores based on patterns and anomalies."},
                {"role": "user", "content": transaction_description}
            ],
            temperature=0.7
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Update the transaction with the AI analysis
        update_transaction_risk(transaction_id, result)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_transaction_risk(transaction_id, ai_analysis):
    """Update transaction with AI risk analysis"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE transactions 
            SET risk_score = %s,
                ai_reasoning = %s,
                ai_flags = %s,
                status = CASE 
                    WHEN %s > 70 THEN 'flagged'
                    ELSE status 
                END
            WHERE transaction_id = %s
        """, (
            ai_analysis['risk_score'],
            ai_analysis['reasoning'],
            json.dumps(ai_analysis['flags']),
            ai_analysis['risk_score'],
            transaction_id
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)