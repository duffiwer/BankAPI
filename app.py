from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy.orm import Session
from prometheus_client import Counter, start_http_server

SWAGGER_URL = '/swagger'
API_URL = '/static/openapi.yaml'  
swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)

app = Flask(__name__)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

metrics = PrometheusMetrics(app)

user_created_total = Counter('user_created_total', 'Total number of users created')

metrics.info('app_info', 'Info about app', version='1.0')

http_total_requests = Counter(
    'http_requests_total', 
    'Total number of HTTP requests', 
    ['method', 'endpoint']  
)


start_http_server(8000)

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
    http_total_requests.labels(method=request.method, endpoint=request.path).inc()

    data = request.get_json()

    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify(message="User is already exists"), 400
    
    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    user_created_total.inc()
    return jsonify(message="User was created"), 201

@app.route('/accounts', methods=['POST'])
def create_account():
    http_total_requests.labels(method=request.method, endpoint=request.path).inc()

    data = request.get_json()
    new_account = Account(user_id=data['user_id'], balance=data['balance'])
    db.session.add(new_account)
    db.session.commit()
    return jsonify(message="Account was created"), 201
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    users_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
    return jsonify(users_list), 200

@app.route('/transactions', methods=['POST'])
def create_transaction():
    http_total_requests.labels(method=request.method, endpoint=request.path).inc()

    data = request.get_json()
    session = db.session

    from_account = session.get(Account, data['from_account_id'])
    to_account = session.get(Account, data['to_account_id'])

    if not from_account or not to_account:
        return jsonify(message="One ot two aacounts not found"), 404

    if from_account.balance < data['amount']:
        return jsonify(message="Not enought money"), 400

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
    transactions_total.inc() 

    return jsonify(message="Transaction was created"), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080)
