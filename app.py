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

TRANSACTION_CHOICES = {
    'descriptions': [
        'Grocery Shopping',
        'Amazon.com',
        'Subway Pass',
        'Restaurant Payment',
        'Utility Bill Payment',
        'ATM Withdrawal',
        'Wire Transfer',
        'Luxury Purchase',
        'Transfer to Cryptocurrency Exchange',
        'Online Gaming Payment'
    ],
    'locations': [
        'New York, NY',
        'Brooklyn, NY',
        'Queens, NY',
        'Manhattan, NY',
        'Newark, NJ',  # Nearby city
        'Los Angeles, CA',  # Unusual but possible
        'Miami, FL',  # Unusual but possible
        'Lagos, Nigeria',  # Potentially suspicious
        'Moscow, Russia',  # Potentially suspicious
        'Dubai, UAE'  # Potentially suspicious
    ],
    'merchant_names': [
        'Whole Foods Market',
        'Amazon',
        'MTA',
        'Con Edison',
        'Chase ATM',
        'Best Buy',
        'Unknown Merchant',
        'Crypto Exchange XYZ',
        'Foreign Luxury Store',
        'Online Casino'
    ],
    'transaction_methods': [
        'card_present',
        'contactless_payment',
        'online_purchase',
        'wire_transfer',
        'mobile_payment',
        'atm_withdrawal',
        'cryptocurrency',
        'foreign_pos',
        'phone_order',
        'unusual_terminal'
    ]
}

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

@app.route('/get_transaction_choices')
def get_transaction_choices():
    return jsonify(TRANSACTION_CHOICES)

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

        # Pass the TRANSACTION_CHOICES to the template
        return render_template('transactions.html', 
                             transactions=transactions,
                             current_balance=current_balance,
                             descriptions=TRANSACTION_CHOICES['descriptions'],
                             locations=TRANSACTION_CHOICES['locations'],
                             merchant_names=TRANSACTION_CHOICES['merchant_names'],
                             transaction_methods=TRANSACTION_CHOICES['transaction_methods'])

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/insert_transaction', methods=['POST'])
def insert_transaction():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get the latest balance
        cursor.execute("""
            SELECT balance_after as current_balance 
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC 
            LIMIT 1
        """, (session['username'],))
        
        result = cursor.fetchone()
        current_balance = float(result['current_balance']) if result else 0.00
        
        # Calculate new balance
        amount = float(request.form['amount'])
        if request.form['transaction_type'] == 'debit':
            amount = -amount  # Make amount negative for debits
        new_balance = current_balance + amount
        
        # Insert new transaction
        cursor.execute("""
            INSERT INTO transactions (
                username,
                transaction_date,
                description,
                amount,
                transaction_type,
                balance_after,
                merchant_name,
                location,
                transaction_method,
                device_id,
                ip_address,
                status
            ) VALUES (
                %s, NOW(), %s, %s, %s, %s, %s, %s, %s, 'device_123', '192.168.1.1', 'pending'
            ) RETURNING transaction_id
        """, (
            session['username'],
            request.form['description'],
            amount,
            request.form['transaction_type'],
            new_balance,
            request.form['merchant_name'],
            request.form['location'],
            request.form['transaction_method']
        ))
        
        # Get the new transaction ID
        transaction_id = cursor.fetchone()['transaction_id']
        conn.commit()
        
        # Perform AI analysis on the new transaction
        analyze_transaction_with_ai(transaction_id)
        
        flash('Transaction inserted successfully!', 'success')
        return redirect(url_for('transactions'))
        
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('transactions'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/reanalyze_all', methods=['POST'])
def reanalyze_transactions_endpoint():
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    result = reanalyze_all_transactions()
    return jsonify(result)

@app.route('/analyze_transaction/<int:transaction_id>')
def analyze_transaction_with_ai(transaction_id):
    try:
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

        # Updated prompt with New York context
        transaction_description = f"""
        Please analyze this bank transaction for potential fraud, considering that the account holder lives in New York City. Provide a risk score between 0-100. Consider the following context:
        - Normal patterns include transactions in NY boroughs and nearby states
        - Regular commuting patterns within NYC
        - Common NY merchants and services
        - Occasional domestic travel is normal
        - International transactions should be scrutinized but not automatically flagged
        
        Transaction Details:
        - Amount: ${abs(float(transaction['amount']))}
        - Type: {transaction['transaction_type']}
        - Location: {transaction['location']}
        - Merchant: {transaction['merchant_name']}
        - Method: {transaction['transaction_method']}
        - Device ID: {transaction['device_id']}
        - IP Address: {transaction['ip_address']}
        - Time: {transaction['transaction_date']}
        
        Please respond in JSON format with:
        {{
            "risk_score": <number between 0-100>,
            "reasoning": "<brief explanation considering NY context>",
            "flags": ["<specific concerns if any>"]
        }}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fraud detection AI for a New York City bank. You understand normal NYC transaction patterns and lifestyle. Flag only genuinely suspicious activities, not regular NYC living patterns."},
                {"role": "user", "content": transaction_description}
            ],
            temperature=0.7
        )
        
        result = json.loads(response.choices[0].message.content)
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

def reanalyze_all_transactions():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get all transactions
        cursor.execute("""
            SELECT 
                transaction_id,
                amount,
                transaction_type,
                location,
                merchant_name,
                transaction_method,
                device_id,
                ip_address,
                transaction_date
            FROM transactions 
            ORDER BY transaction_date DESC
        """)
        
        transactions = cursor.fetchall()
        
        for transaction in transactions:
            # Construct context-aware prompt for each transaction
            prompt = f"""
            Analyze this bank transaction for potential fraud. Consider these guidelines:
            
            Base Context:
            - Account holder is based in New York City
            - Normal radius includes NY metro area (NYC boroughs, NJ, CT)
            - Expected merchant types: retail, restaurants, transit, utilities
            - Regular commuting patterns within NYC
            - Common transaction methods: card_present, contactless, online
            
            Specific Risk Factors to Consider:
            1. Location Risk
                - NYC metro area: Low risk
                - Other US cities: Moderate risk if unusual
                - International: High risk unless previously established pattern
            
            2. Amount Risk
                - Compare to transaction type and merchant
                - Unusual amounts for merchant type
                - Round numbers in wire transfers
            
            3. Method Risk
                - Card present outside normal area
                - Wire transfers to unknown accounts
                - Unusual payment methods for merchant
            
            4. Pattern Risk
                - Device/IP changes
                - Velocity of transactions
                - Merchant category alignment
            
            Transaction Details:
            - Amount: ${abs(float(transaction['amount']))}
            - Type: {transaction['transaction_type']}
            - Location: {transaction['location']}
            - Merchant: {transaction['merchant_name']}
            - Method: {transaction['transaction_method']}
            - Device ID: {transaction['device_id']}
            - IP: {transaction['ip_address']}
            - Time: {transaction['transaction_date']}
            
            Provide analysis in this JSON format:
            {{
                "risk_score": <0-100>,
                "reasoning": "<brief explanation>",
                "flags": ["<specific risk factors>"]
            }}
            
            Risk Score Guidelines:
            0-30: Low risk, normal NYC patterns
            31-60: Moderate risk, unusual but explainable
            61-80: High risk, multiple concerns
            81-100: Very high risk, immediate attention needed
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a NYC-based fraud detection AI. You understand normal NYC transaction patterns and typical consumer behavior in the metropolitan area."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Update the transaction with new analysis
            cursor.execute("""
                UPDATE transactions 
                SET risk_score = %s,
                    ai_reasoning = %s,
                    ai_flags = %s,
                    status = CASE 
                        WHEN %s >= 80 THEN 'flagged'
                        WHEN %s >= 60 THEN 'suspicious'
                        ELSE 'completed' 
                    END
                WHERE transaction_id = %s
            """, (
                result['risk_score'],
                result['reasoning'],
                json.dumps(result['flags']),
                result['risk_score'],
                result['risk_score'],
                transaction['transaction_id']
            ))
            
            conn.commit()
            
        return {"message": "Successfully reanalyzed all transactions"}
        
    except Exception as e:
        print(f"Error in reanalysis: {str(e)}")
        return {"error": str(e)}
    
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
