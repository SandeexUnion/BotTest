from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import User, Base

# Создаем Flask-приложение
app = Flask(__name__)

# Настройка базы данных (синхронный движок)
engine = create_engine('sqlite:///db.sqlite3')
Session = sessionmaker(bind=engine)
session = Session()

# Настройка Flask-Admin
app.config['SECRET_KEY'] = 'ваш_секретный_ключ'
admin = Admin(app, name='Админка', template_mode='bootstrap3')

# Модель для отображения пользователей
class UserAdmin(ModelView):
    column_list = ('id', 'tg_id', 'login', 'name', 'start_date', 'is_trial', 'end_date')
    column_labels = {
        'id': 'ID',
        'tg_id': 'Telegram ID',
        'login': 'Логин',
        'name': 'Имя',
        'start_date': 'Дата начала',
        'is_trial': 'Тип (тест/платная)',
        'end_date': 'Дата окончания',
    }
    column_searchable_list = ('login', 'name')
    column_filters = ('is_trial',)

# Добавляем модель User в админку
admin.add_view(UserAdmin(User, session))

if __name__ == '__main__':
    app.run(debug=True)