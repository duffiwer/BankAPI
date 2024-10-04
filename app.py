from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime
from sqlalchemy.orm import Session

SWAGGER_URL = '/swagger'
API_URL = '/static/openapi.yaml'  # Путь к YAML-файлу спецификации
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)

app = Flask(__name__)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify(message="Пользователь успешно создан"), 201

@app.route('/accounts', methods=['POST'])
def create_account():
    data = request.get_json()
    new_account = Account(user_id=data['user_id'], balance=data['balance'])
    db.session.add(new_account)
    db.session.commit()
    return jsonify(message="Счет успешно создан"), 201

@app.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.get_json()
    session = db.session

    from_account = session.get(Account, data['from_account_id'])
    to_account = session.get(Account, data['to_account_id'])

    if not from_account or not to_account:
        return jsonify(message="Один или оба аккаунта не найдены"), 404

    if from_account.balance < data['amount']:
        return jsonify(message="Недостаточно средств"), 400

    transaction = Transaction(
        from_account_id=data['from_account_id'],
        to_account_id=data['to_account_id'],
        amount=data['amount'],
        currency=data['currency']
    )

    from_account.balance -= data['amount']
    to_account.balance += data['amount']

    db.session.add(transaction)
    db.session.commit()

    return jsonify(message="Транзакция успешно создана"), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080)
