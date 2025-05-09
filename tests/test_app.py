from io import BytesIO
from db import get_db

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'<title>' in response.data or 'Работы'.encode('utf-8') in response.data

def test_register_login_logout(client, auth):
    response = auth.login()
    assert 'Работы'.encode('utf-8') in response.data or b'logout' in response.data

    response = auth.logout()
    assert 'Войти'.encode('utf-8') in response.data or b'login' in response.data

def test_register_duplicate_username(client, auth):
    auth.login()
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert 'Регистрация'.encode('utf-8') in response.data

def test_upload_requires_login(client):
    response = client.get('/upload')
    assert response.status_code in (301, 302)
    assert '/login' in response.headers['Location']

def test_upload_work(client, auth, app):
    auth.login()
    data = {
        'title': 'Test Work',
        'description': 'Test Description',
        'image': (BytesIO(b"fake image"), 'test.jpg')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert 'Галерея работ'.encode('utf-8') in response.data

def test_work_detail(client, auth, app):
    auth.login()
    client.post('/upload', data={
        'title': 'Detail Work',
        'description': 'Some description',
        'image': (BytesIO(b'image'), 'detail.jpg')
    }, content_type='multipart/form-data', follow_redirects=True)

    with app.app_context():
        db = get_db()
        row = db.execute("SELECT id FROM works WHERE title = 'Detail Work'").fetchone()
        assert row is not None, "Не найдена работа с title='Detail Work'"
        work_id = row['id']
    response = client.get(f'/work/{work_id}')
    assert 'Detail Work'.encode('utf-8') in response.data

def test_add_comment(client, auth, app):
    auth.login()
    client.post('/upload', data={
        'title': 'Commented Work',
        'description': 'Desc',
        'image': (BytesIO(b'image'), 'c.jpg')
    }, content_type='multipart/form-data', follow_redirects=True)

    with app.app_context():
        db = get_db()
        work_id = db.execute('SELECT id FROM Works').fetchone()['id']

    response = client.post(f'/add_comment/{work_id}', data={'comment': 'Nice!'}, follow_redirects=True)
    assert 'Комментарии'.encode('utf-8') in response.data
    assert 'Nice!'.encode('utf-8') in response.data

def test_profile_view(client, auth):
    auth.login()
    response = client.get('/profile/testuser')
    assert response.status_code == 200
    assert 'testuser'.encode('utf-8') in response.data

def test_delete_own_work(client, auth, app):
    auth.login()
    client.post('/upload', data={
        'title': 'Delete Me',
        'description': 'desc',
        'image': (BytesIO(b'image'), 'del.jpg')
    }, content_type='multipart/form-data', follow_redirects=True)

    with app.app_context():
        db = get_db()
        work_id = db.execute('SELECT id FROM Works').fetchone()['id']
    response = client.post(f'/delete_work/{work_id}', follow_redirects=True)
    assert 'Профиль'.encode('utf-8') in response.data

def test_like_work_toggle(client, auth, app):
    auth.login()
    client.post('/upload', data={
        'title': 'Likeable',
        'description': 'desc',
        'image': (BytesIO(b'image'), 'like.jpg')
    }, content_type='multipart/form-data', follow_redirects=True)

    with app.app_context():
        db = get_db()
        work_id = db.execute('SELECT id FROM Works').fetchone()['id']

    response = client.post(f'/like/{work_id}')
    assert response.status_code == 200
    assert response.json['liked'] is True

    response = client.post(f'/like/{work_id}')
    assert response.status_code == 200
    assert response.json['liked'] is False

def test_index_search_sort(client):
    response = client.get('/?search=test&sort=asc')
    assert response.status_code == 200
