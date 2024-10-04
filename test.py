import unittest
from app import app, db, User, Account

class FlaskAppTests(unittest.TestCase):
    def setUp(self):
        self.app = app
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
            'password': 'testpassword'
        })
        self.assertIn('Пользователь успешно создан', response.get_json()['message'])

    def test_create_account(self):
        with self.app.app_context():
            user = User(username='testuser', email='test@example.com', password='testpassword')
            db.session.add(user)
            db.session.commit()

            response = self.client.post('/accounts', json={
                'user_id': user.id,
                'balance': 100.0
            })
            self.assertIn('Счет успешно создан', response.get_json()['message'])

    def test_create_transaction(self):
        with self.app.app_context():
            user = User(username='testuser', email='test@example.com', password='testpassword')
            db.session.add(user)
            db.session.commit()

            account1 = Account(balance=100.0, user_id=user.id)
            account2 = Account(balance=50.0, user_id=user.id)
            db.session.add(account1)
            db.session.add(account2)
            db.session.commit()

            response = self.client.post('/transactions', json={
                'from_account_id': account1.id,
                'to_account_id': account2.id,
                'amount': 25.0,
                'currency': 'USD'
            })
            self.assertIn('Транзакция успешно создана', response.get_json()['message'])

if __name__ == '__main__':
    unittest.main()
