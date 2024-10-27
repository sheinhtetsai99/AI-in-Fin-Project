
import openai
import os
from dotenv import load_dotenv
import json

# Load the .env file
load_dotenv()

client = openai.OpenAI(
    api_key= os.getenv('OPENAI_KEY')
)

def analyze_transaction_with_ai(transaction):
    """Use ChatGPT to analyze transaction and determine risk score"""
    
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

    try:
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
        return result
        
    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
        return {"risk_score": 0, "reasoning": "AI analysis failed", "flags": []}

# Create a sample transaction for testing
sample_transaction = {
    'amount': 999.99,
    'transaction_type': 'online_purchase',
    'location': 'Moscow, Russia',
    'merchant_name': 'Unknown Electronics Store',
    'transaction_method': 'credit_card',
    'device_id': 'dev_12345',
    'ip_address': '185.173.35.42',
    'transaction_date': '2024-10-27 13:52:37.809482'
}

# Test the function
print("\nTesting transaction analysis...")
result = analyze_transaction_with_ai(sample_transaction)
print("\nAnalysis Result:")
print(f"Risk Score: {result['risk_score']}")
print(f"Reasoning: {result['reasoning']}")
print("Flags:", ', '.join(result['flags']) if result['flags'] else "None")