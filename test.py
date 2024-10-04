import unittest
from app import app, db, User, Account

class FlaskAppTests(unittest.TestCase):
    
    def setUp(self):
        
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'  
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()  

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()  
    def test_create_user(self):
        response = self.client.post('/users', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('Пользователь успешно создан', response.data)

    def test_create_account(self):
        user = User(username='testuser', email='test@example.com', password='password123')
        db.session.add(user)
        db.session.commit()  

        response = self.client.post('/accounts', json={
            'account_type': 'savings',
            'balance': 1000,
            'currency': 'USD',
            'user_id': user.id
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('Счет успешно создан', response.data)

    def test_create_transaction(self):
        user = User(username='testuser', email='test@example.com', password='password123')
        db.session.add(user)
        db.session.commit()

        account1 = Account(account_type='savings', balance=1000, currency='USD', user_id=user.id)
        account2 = Account(account_type='checking', balance=500, currency='USD', user_id=user.id)
        db.session.add(account1)
        db.session.add(account2)
        db.session.commit()
        response = self.client.post('/transactions', json={
            'from_account_id': account1.id,
            'to_account_id': account2.id,
            'amount': 100,
            'currency': 'USD'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('Транзакция успешно создана', response.data)

if __name__ == '__main__':
    unittest.main()
