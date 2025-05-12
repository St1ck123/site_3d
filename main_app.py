from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from db import init_app, get_db
from werkzeug.utils import secure_filename

def main_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY='super_secret_key_12345',
        UPLOAD_FOLDER='static/uploads',
        DATABASE='database.db'
    )
    return app

@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%d.%m.%Y %H:%M'):
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
    return value.strftime(format)

init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute("SELECT id, username FROM Users WHERE id = ?", (user_id,)).fetchone()
    return User(user['id'], user['username']) if user else None

@app.route('/')
def index():
    search = request.args.get('search', '')
    sort_order = request.args.get('sort', 'desc')
    order_by = "DESC" if sort_order == "desc" else "ASC"

    db = get_db()
    works = db.execute(f'''
        SELECT Works.*, Users.username, 
        (SELECT COUNT(*) FROM Likes WHERE work_id = Works.id) AS likes_count,
        CASE 
            WHEN EXISTS (SELECT 1 FROM Likes WHERE user_id = ? AND work_id = Works.id) 
            THEN 1 ELSE 0 
        END AS user_liked
        FROM Works 
        JOIN Users ON Works.user_id = Users.id
        WHERE Works.title LIKE ? OR Works.description LIKE ?
        ORDER BY likes_count {order_by}
    ''', (current_user.id if current_user.is_authenticated else None, f"%{search}%", f"%{search}%")).fetchall()

    return render_template('index.html', works=works)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        db = get_db()
        try:
            db.execute("INSERT INTO Users (username, email, password_hash) VALUES (?, ?, ?)",
                       (username, email, hashed_password))
            db.commit()
        except:
            flash('Имя пользователя или email уже существуют!', 'error')
            return redirect(url_for('register'))
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT id, username, password_hash FROM Users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            login_user(User(user['id'], user['username']))
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль!', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['image']
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            db = get_db()
            db.execute("INSERT INTO Works (user_id, title, description, image_path) VALUES (?, ?, ?, ?)",
                       (current_user.id, request.form['title'], request.form['description'], f'static/uploads/{filename}'))
            db.commit()
            flash('Работа загружена!', 'success')
            return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/work/<int:work_id>')
def work_detail(work_id):
    db = get_db()
    work = db.execute('''
        SELECT Works.*, Users.username,
        (SELECT COUNT(*) FROM Likes WHERE work_id = Works.id) AS likes_count,
        CASE 
            WHEN EXISTS (SELECT 1 FROM Likes WHERE user_id = ? AND work_id = Works.id) 
            THEN 1 ELSE 0 
        END AS user_liked
        FROM Works
        JOIN Users ON Works.user_id = Users.id
        WHERE Works.id = ?
    ''', (current_user.id if current_user.is_authenticated else None, work_id)).fetchone()

    comments = db.execute('''
        SELECT Comments.*, Users.username
        FROM Comments
        JOIN Users ON Comments.user_id = Users.id
        WHERE Comments.work_id = ?
        ORDER BY comment_date DESC
    ''', (work_id,)).fetchall()

    if work is None:
        flash('Работа не найдена!', 'error')
        return redirect(url_for('index'))

    return render_template('work_detail.html', work=work, comments=comments)


@app.route('/add_comment/<int:work_id>', methods=['POST'])
@login_required
def add_comment(work_id):
    comment_text = request.form['comment']
    db = get_db()
    db.execute("INSERT INTO Comments (user_id, work_id, text) VALUES (?, ?, ?)",
               (current_user.id, work_id, comment_text))
    db.commit()
    flash('Комментарий добавлен!', 'success')
    return redirect(url_for('work_detail', work_id=work_id))

@app.route('/profile/<username>')
def profile(username):
    db = get_db()
    user = db.execute("SELECT id, username, registration_date FROM Users WHERE username = ?", (username,)).fetchone()
    works = db.execute("SELECT * FROM Works WHERE user_id = ?", (user['id'],)).fetchall()
    return render_template('profile.html', user=user, works=works)


@app.route('/delete_work/<int:work_id>', methods=['POST'])
@login_required
def delete_work(work_id):
    db = get_db()
    work = db.execute("SELECT * FROM Works WHERE id = ?", (work_id,)).fetchone()

    if work is None:
        flash("Работа не найдена!", "error")
        return redirect(url_for('index'))

    if work['user_id'] != current_user.id:
        flash("Вы не можете удалить эту работу!", "error")
        return redirect(url_for('profile', username=current_user.username))

    # Удаляем изображение с сервера
    image_path = work['image_path']
    if os.path.exists(image_path):
        os.remove(image_path)

    # Удаляем запись из базы данных
    db.execute("DELETE FROM Works WHERE id = ?", (work_id,))
    db.commit()

    flash("Работа удалена!", "success")
    return redirect(url_for('profile', username=current_user.username))


@app.route('/like/<int:work_id>', methods=['POST'])
@login_required
def like_work(work_id):
    db = get_db()
    existing_like = db.execute(
        "SELECT * FROM Likes WHERE user_id = ? AND work_id = ?",
        (current_user.id, work_id)
    ).fetchone()

    if existing_like:
        db.execute("DELETE FROM Likes WHERE user_id = ? AND work_id = ?", (current_user.id, work_id))
        liked = False
    else:
        db.execute("INSERT INTO Likes (user_id, work_id) VALUES (?, ?)", (current_user.id, work_id))
        liked = True

    db.commit()

    likes_count = db.execute("SELECT COUNT(*) FROM Likes WHERE work_id = ?", (work_id,)).fetchone()[0]

    return jsonify({"liked": liked, "likes_count": likes_count})




if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
