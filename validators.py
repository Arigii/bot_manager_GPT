import telebot
from config import TOKEN
from database import Database
import datetime

bot = telebot.TeleBot(TOKEN)
db = Database()


def validate_date(date):
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time(time_set):
    try:
        datetime.datetime.strptime(time_set, '%H:%M')
        return True
    except ValueError:
        return False


# Вывожу категории из бд ради того, чтобы потом добавить функцию добавления категорий
def category_list():
    list_cat = db.select_all_categories()
    response = ""
    if list_cat:
        response = "Доступные категории:\n"
        for cell in list_cat:
            id_category, name = cell
            response += f"{id_category}. {name}\n"
    return response
