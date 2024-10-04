from flask import Flask, jsonify, request
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/openapi.yaml'  # Путь к YAML-файлу спецификации
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

users = []
accounts = []
transactions = []

@app.route('/users', methods=['POST'])
def register_user():
    user_data = request.get_json()
    user_id = len(users) + 1
    user = {
        "user_id": user_id,
        "username": user_data['username'],
        "email": user_data['email']
    }
    users.append(user)
    return jsonify(user), 201

@app.route('/accounts', methods=['GET'])
def get_user_accounts():
    user_id = request.args.get('user_id')
    user_accounts = [acc for acc in accounts if acc['user_id'] == int(user_id)]
    return jsonify(user_accounts), 200

@app.route('/accounts', methods=['POST'])
def create_account():
    account_data = request.get_json()
    account_id = len(accounts) + 1
    account = {
        "account_id": account_id,
        "user_id": account_data['user_id'],
        "account_type": account_data['account_type'],
        "balance": 0,
        "currency": account_data['currency']
    }
    accounts.append(account)
    return jsonify(account), 201

@app.route('/transactions', methods=['POST'])
def create_transaction():
    transaction_data = request.get_json()
    from_account = next((acc for acc in accounts if acc['account_id'] == transaction_data['from_account_id']), None)
    to_account = next((acc for acc in accounts if acc['account_id'] == transaction_data['to_account_id']), None)

    if not from_account or not to_account:
        return jsonify({"message": "One of the accounts not found"}), 404

    if from_account['balance'] < transaction_data['amount']:
        return jsonify({"message": "Insufficient balance"}), 400

    from_account['balance'] -= transaction_data['amount']
    to_account['balance'] += transaction_data['amount']

    transaction = {
        "transaction_id": len(transactions) + 1,
        "from_account_id": transaction_data['from_account_id'],
        "to_account_id": transaction_data['to_account_id'],
        "amount": transaction_data['amount'],
        "currency": transaction_data['currency'],
        "timestamp": transaction_data.get('timestamp', '2024-09-29 15:27:00')
    }
    transactions.append(transaction)
    return jsonify(transaction), 201


@app.route('/transactions/history', methods=['GET'])
def get_transaction_history():
    account_id = request.args.get('account_id')
    account_transactions = [t for t in transactions if t['from_account_id'] == int(account_id) or t['to_account_id'] == int(account_id)]
    return jsonify(account_transactions), 200


if __name__ == '__main__':
    app.run(debug=True, port=8080)
