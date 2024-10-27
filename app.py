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
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
from datetime import datetime
import logging
import sys

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

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    api_key = request.form['api_key']
    session['api_key'] = api_key  # Store API key in session
    os.environ['API_KEY'] = api_key  # Set the environment variable dynamically
    genai.configure(api_key=api_key)  # Configure Gemini API with the new key
    return redirect(url_for('index'))

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()
    
# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    financial_profiles = db.relationship('FinancialProfile', backref='user', lazy=True)

class FinancialProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    annual_income = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    investment_horizon = db.Column(db.String(20))
    region = db.Column(db.String(50))
    total_assets = db.Column(db.Float)
    selected_portfolios = db.Column(db.String(500))  # Store as comma-separated string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
@app.route("/financial_planning", methods=["GET", "POST"])
def financial_planning():
    if request.method == "POST":
        # Debug Step 1: Print raw form data
        print("\n==== Raw Form Data ====")
        print("Form Data:", request.form)
        
        try:
            # Debug Step 2: Extract form data with explicit error checking
            print("\n==== Extracting Form Data ====")
            
            # Get form data with validation
            age = request.form.get("age")
            gender = request.form.get("gender")
            annual_income = request.form.get("annual_income")
            total_assets = request.form.get("total_assets")
            
            print(f"Age: {age}, type: {type(age)}")
            print(f"Gender: {gender}, type: {type(gender)}")
            print(f"Annual Income: {annual_income}, type: {type(annual_income)}")
            print(f"Total Assets: {total_assets}, type: {type(total_assets)}")

            # Validate all required fields are present
            if not all([age, gender, annual_income, total_assets]):
                missing_fields = []
                if not age: missing_fields.append("age")
                if not gender: missing_fields.append("gender")
                if not annual_income: missing_fields.append("annual income")
                if not total_assets: missing_fields.append("total assets")
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"Validation Error: {error_msg}")
                return render_template("advice.html", r=error_msg)

            # Debug Step 3: Configure API
            print("\n==== API Configuration ====")
            api_key = "AIzaSyDtgxpFE0405T7m7l4llYVzW-eCb_Z-XMg"  # Replace with your actual key
            if not api_key:
                print("Error: No API key provided")
                return render_template("advice.html", r="API key is missing")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-pro")
            print("API configured successfully")

            # Debug Step 4: Create prompt
            prompt = f"""
            As a financial advisor, provide specific investment advice for an investor with the following profile:

            Demographics:
            - Age: {age}
            - Gender: {gender}

            Financial Status:
            - Annual Income: ${annual_income}
            - Total Assets: ${total_assets}

            Please provide:
            1. Asset allocation recommendation based on age and financial status
            2. Specific investment suggestions considering the financial profile
            3. Timeline-based investment strategy
            4. Risk considerations and diversification advice
            """

            print("\n==== Generated Prompt ====")
            print(prompt)

            # Debug Step 5: Generate response
            response = model.generate_content(prompt)
            print("Response received from API")
            
            if response and hasattr(response, 'text'):
                advice_text = response.text
                print(f"Generated text length: {len(advice_text)}")
                print("Full advice text:", advice_text)
                
                # Return JSON response for AJAX
                return jsonify({"advice": advice_text})
            else:
                error_msg = "Invalid response format from API"
                print(f"Error: {error_msg}")
                return jsonify({"advice": error_msg})
                
        except Exception as e:
            error_msg = f"Server error: {str(e)}"
            print(f"Server Error: {error_msg}")
            return jsonify({"advice": error_msg})

    return render_template("financial_planning.html")

@app.route("/advice")
def advice():
    advice_text = request.args.get('advice', 'No advice available.')
    return render_template("advice.html", advice=advice_text)


if __name__ == '__main__':
    app.run(debug=True)
