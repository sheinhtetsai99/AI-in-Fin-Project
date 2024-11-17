import os
from flask import Flask, jsonify, request, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import timedelta, datetime, timezone
import psycopg2
import psycopg2.extras
from openai import OpenAI
import json
import os
import openai
from dotenv import load_dotenv
import yfinance as yf
import requests
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Transaction choices for form population
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
        'Newark, NJ',
        'Los Angeles, CA',
        'Miami, FL',
        'Lagos, Nigeria',
        'Moscow, Russia',
        'Dubai, UAE'
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

# Stock monitoring
MAGNIFICENT_7_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META"]
MONITORING_SYMBOLS = set(MAGNIFICENT_7_SYMBOLS)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

load_dotenv()

# OpenAI client initialization
client = openai.OpenAI(
    api_key=os.getenv('OPENAI_KEY')
)

# Database configuration
DB_HOST = "35.226.233.144"
DB_NAME = "sampledb"
DB_USER = "postgres"
DB_PASS = "password"

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

# Stock data functions
def get_stock_data(symbols):
    stock_data = {}
    for symbol in symbols:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if not data.empty:
            last_quote = data.iloc[-1]
            stock_data[symbol] = {
                "price": round(last_quote["Close"], 2),
                "change": round(last_quote["Close"] - last_quote["Open"], 2),
                "percent_change": round((last_quote["Close"] - last_quote["Open"]) / last_quote["Open"] * 100, 2)
            }
    return stock_data

def fetch_financial_news(page=1):
    api_key = "76cac055c5ec487cb5f01affdd1bd27f"
    url = f"https://newsapi.org/v2/top-headlines?category=business&country=us&pageSize=6&page={page}&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        return data.get('articles', []), data.get('totalResults', [])
    else:
        logging.error("Failed to fetch financial news")
        return [], 0

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.before_request
def initialize_session():
    if 'monitored_stocks' not in session:
        session['monitored_stocks'] = MAGNIFICENT_7_SYMBOLS.copy()

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT balance_after as current_balance 
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC 
            LIMIT 1
        """, (session['username'],))
        
        balance_result = cursor.fetchone()
        current_balance = float(balance_result['current_balance']) if balance_result else 0.00
        
        cursor.execute("""
            SELECT COUNT(*) as transaction_count
            FROM transactions 
            WHERE username = %s 
            AND transaction_date >= NOW() - INTERVAL '30 days'
        """, (session['username'],))
        
        count_result = cursor.fetchone()
        recent_transactions = count_result['transaction_count'] if count_result else 0
        
        return render_template('home.html', 
                             username=session['username'],
                             current_balance=current_balance,
                             recent_transactions=recent_transactions)

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('login'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    stock_data = get_stock_data(session['monitored_stocks'])
    local_timezone = timezone(timedelta(hours=8))
    current_datetime = datetime.now(local_timezone).strftime('%d/%m/%Y %H:%M:%S')

    page = int(request.args.get('page', 1))
    news_articles, total_results = fetch_financial_news(page)
    total_pages = (total_results // 6) + (1 if total_results % 6 > 0 else 0)

    return render_template('dashboard.html', 
                         stock_data=stock_data, 
                         current_datetime=current_datetime, 
                         news_articles=news_articles, 
                         current_page=page, 
                         total_pages=total_pages)

# Stock-related routes
@app.route('/search_stocks')
def search_stocks():
    query = request.args.get('query', '').upper()
    if len(query) < 1:
        return jsonify([])
    results = [{"symbol": "AAPL", "name": "Apple Inc."}, {"symbol": "MSFT", "name": "Microsoft Corp"}]
    matched_stocks = [stock for stock in results if query in stock['symbol']]
    return jsonify(matched_stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    symbol = request.args.get('symbol').upper()
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d")
    if not data.empty:
        if symbol not in session['monitored_stocks']:
            session['monitored_stocks'].append(symbol)
            session.modified = True
        return jsonify({"success": True, "symbol": symbol, "data": get_stock_data([symbol])[symbol]})
    else:
        return jsonify({"success": False, "error": "Invalid ticker symbol"}), 400

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    symbol = request.args.get('symbol').upper()
    if symbol in session['monitored_stocks']:
        session['monitored_stocks'].remove(symbol)
        session.modified = True
    return '', 204

@app.route('/get_stock_data', methods=['GET'])
def get_stock_data_single():
    symbol = request.args.get('symbol')
    data = get_stock_data([symbol])
    return jsonify(data.get(symbol, {}))

# Authentication routes
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

# Transaction routes
@app.route('/transactions')
def transactions():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Fetch current balance with better error handling
        cursor.execute("""
            SELECT COALESCE(balance_after, 0) as current_balance 
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC 
            LIMIT 1
        """, (session['username'],))
        
        balance_result = cursor.fetchone()
        current_balance = float(balance_result['current_balance'] if balance_result else 0.00)
        
        # Fetch transactions with better error handling
        cursor.execute("""
            SELECT 
                transaction_id,
                transaction_date,
                description,
                COALESCE(amount, 0) as amount,
                transaction_type,
                COALESCE(balance_after, 0) as balance_after,
                merchant_category_code,
                location,
                ip_address,
                device_id,
                transaction_method,
                COALESCE(status, 'pending') as status,
                COALESCE(risk_score, 0) as risk_score,
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
                             current_balance=current_balance,
                             descriptions=TRANSACTION_CHOICES['descriptions'],
                             locations=TRANSACTION_CHOICES['locations'],
                             merchant_names=TRANSACTION_CHOICES['merchant_names'],
                             transaction_methods=TRANSACTION_CHOICES['transaction_methods'])

    except Exception as e:
        logging.error(f"Error in transactions route: {str(e)}", exc_info=True)
        flash(f'An error occurred while loading transactions. Please try again.', 'error')
        return redirect(url_for('home'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/get_transaction_choices')
def get_transaction_choices():
    return jsonify(TRANSACTION_CHOICES)

@app.route('/insert_transaction', methods=['POST'])
def insert_transaction():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT balance_after as current_balance 
            FROM transactions 
            WHERE username = %s 
            ORDER BY transaction_date DESC, transaction_id DESC 
            LIMIT 1
        """, (session['username'],))
        
        result = cursor.fetchone()
        current_balance = float(result['current_balance']) if result else 0.00
        
        # Get the absolute amount from the form
        amount = abs(float(request.form['amount']))
        
        # For debits, we subtract from the balance
        # For credits, we add to the balance
        if request.form['transaction_type'] == 'debit':
            amount = -amount  # Make the amount negative for debits
            new_balance = current_balance + amount  # This will subtract since amount is negative
        else:
            new_balance = current_balance + amount  # Add for credits
        
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
            amount,  # Store the signed amount
            request.form['transaction_type'],
            new_balance,
            request.form['merchant_name'],
            request.form['location'],
            request.form['transaction_method']
        ))
        
        transaction_id = cursor.fetchone()['transaction_id']
        conn.commit()
        
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

# Financial planning routes
@app.route("/financial_planning", methods=["GET", "POST"])
def financial_planning():
    return redirect("https://group-assignment-b6o6.onrender.com/financial_planning")

# chatbot routes
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    return redirect("https://bc3409-chatbot-twld.onrender.com/")

@app.route("/advice")
def advice():
    advice_text = request.args.get('advice', 'No advice available.')
    return render_template("advice.html", advice=advice_text)

if __name__ == '__main__':
    app.run(debug=True)