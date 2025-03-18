![гиф](static/img/demo.gif)
<b>3d Портфолио

Этот проект представляет собой веб-приложение для загрузки, просмотра и лайков художественных работ.

Возможности:\
Поиск и сортировка работ по популярности\
Загрузка изображений с описанием\
Лайки\
Добавление комментариев\
Регистрация и авторизация пользователей\
Установка и запуск

1. Клонирование репозитория

       git clone https://github.com/St1ck123/site_3d.git
       cd repository


2. Установка зависимостей

        pip install -r requirements.txt

4. Инициализация базы данных

        flask db init
        flask db migrate -m "Initial migration"
        flask db upgrade

5. Запуск приложения

        flask run

Приложение будет доступно по адресу: http://127.0.0.1:5000

📂 Структура проекта

        │-- static/
        │         uploads/      
        │         img/         
        │-- templates      
        │-- app.py         
        │-- db.py              
        │-- models.py       
        │-- requirements.txt   
        │-- README.md           

🔧 Технологии

        Flask (основной фреймворк)
        
        SQLite (база данных)
        
        Bootstrap (стили)
