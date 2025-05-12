import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tempfile
import pytest
from main_app import app as flask_app, init_app
from db import init_db, get_db
from flask import g

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test',
    })

    init_app(flask_app)

    with flask_app.app_context():
        init_db()

    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def auth(client):
    class AuthActions:
        def login(self, username='testuser', password='testpassword'):
            client.post('/register', data={
                'username': username,
                'email': 'test@example.com',
                'password': password
            })
            return client.post('/login', data={
                'username': username,
                'password': password
            }, follow_redirects=True)

        def logout(self):
            return client.get('/logout', follow_redirects=True)

    return AuthActions()
