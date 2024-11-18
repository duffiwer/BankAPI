from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy.orm import Session
from prometheus_client import Counter, start_http_server
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
import logging

resource = Resource.create(attributes={
    "service.name": "bankAPI"
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831  
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  
        logging.StreamHandler()        
    ]
)

logger = logging.getLogger(__name__)
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

FlaskInstrumentor().instrument_app(app)
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
    with tracer.start_as_current_span("create_user") as span:
        http_total_requests.labels(method=request.method, endpoint=request.path).inc()
        logger.info("Creating user started")

        data = request.get_json()
        existing_user = User.query.filter_by(email=data['email']).first()

        span.set_attribute("request.email", data['email'])  
        span.set_attribute("request.username", data['username'])

        if existing_user:
            span.set_attribute("error", "User already exists")
            logger.warning("Attempt to create user with existing email: %s", data['email'])
            return jsonify(message="User already exists"), 400

        new_user = User(username=data['username'], email=data['email'], password=data['password'])
        db.session.add(new_user)
        db.session.commit()
        user_created_total.inc()

        logger.info("User successfully created: %s", new_user.username)
        return jsonify(message="User was created"), 201

@app.route('/accounts', methods=['POST'])
def create_account():
    http_total_requests.labels(method=request.method, endpoint=request.path).inc()
    logger.info("Creating account started")

    data = request.get_json()
    new_account = Account(user_id=data['user_id'], balance=data['balance'])
    db.session.add(new_account)
    db.session.commit()
    logger.info("Account successfully created: ID=%s, User ID=%s", new_account.id, data['user_id'])
    
    return jsonify(message="Account was created"), 201

@app.route('/accounts', methods=['GET'])
def get_accounts():
    accounts = Account.query.all()
    accounts_list = [{'id': account.id, 'user_id': account.user_id, 'balance': account.balance} for account in accounts]
    logger.info("Getting accounts list completed, found %d accounts", len(accounts))
    
    return jsonify(accounts_list), 200

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    users_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
    logger.info("Getting users list completed, found %d users", len(users))
    
    return jsonify(users_list), 200

@app.route('/transactions', methods=['POST'])
def create_transaction():
    with tracer.start_as_current_span("create_transaction") as span:
        http_total_requests.labels(method=request.method, endpoint=request.path).inc()
        logger.info("Creating transaction started")

        data = request.get_json()

        span.set_attribute("transaction.from_account_id", data['from_account_id'])
        span.set_attribute("transaction.to_account_id", data['to_account_id'])
        span.set_attribute("transaction.amount", data['amount'])

        try:
            from_account = db.session.get(Account, data['from_account_id'])
            to_account = db.session.get(Account, data['to_account_id'])

            if not from_account or not to_account:
                span.set_attribute("error", "One or both accounts not found")
                logger.warning("One or both accounts not found: from_account_id=%s, to_account_id=%s", data['from_account_id'], data['to_account_id'])
                return jsonify(message="One or two accounts not found"), 404

            if from_account.balance < data['amount']:
                span.set_attribute("error", "Not enough funds")
                logger.warning("Not enough funds for transaction: balance=%s, requested amount=%s", from_account.balance, data['amount'])
                return jsonify(message="Not enough money"), 400

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
            logger.info("Transaction successfully created: from account=%s, to account=%s, amount=%s", data['from_account_id'], data['to_account_id'], data['amount'])

            return jsonify(message="Transaction was created"), 201

        except Exception as e:
            db.session.rollback()
            span.set_attribute("error", str(e))
            logger.error("Error while creating transaction: %s", e)
            return jsonify(message="Transaction error"), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8080)