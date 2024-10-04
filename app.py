from flask import Flask, jsonify, request
from flask_swagger_ui import get_swaggerui_blueprint
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/openapi.yaml'  # Путь к YAML-файлу спецификации
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    accounts = db.relationship('Account', backref='user', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(db.String(50), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)


with app.app_context():
    db.create_all()


@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Пользователь успешно создан"}), 201

@app.route('/accounts', methods=['POST'])
def create_account():
    data = request.get_json()
    new_account = Account(account_type=data['account_type'], balance=data['balance'], currency=data['currency'], user_id=data['user_id'])
    db.session.add(new_account)
    db.session.commit()
    return jsonify({"message": "Счет успешно создан"}), 201

@app.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.get_json()
    from_account = Account.query.get(data['from_account_id'])
    to_account = Account.query.get(data['to_account_id'])

    if not from_account or not to_account:
        return jsonify({"message": "Один из счетов не найден"}), 404

    if from_account.balance < data['amount']:
        return jsonify({"message": "Недостаточно средств"}), 400

    from_account.balance -= data['amount']
    to_account.balance += data['amount']
    new_transaction = Transaction(
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=data['amount'],
        currency=data['currency']
    )
    db.session.add(new_transaction)
    db.session.commit()
    return jsonify({"message": "Транзакция успешно создана"}), 201

if __name__ == '__main__':
    app.run(debug=True, port=8080)
