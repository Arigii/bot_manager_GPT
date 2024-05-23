import logging
import telebot
from telebot import types
from database import Database
import datetime

# подтягиваем функции из database файла
from creds import get_bot_token  # модуль для получения bot_token
from config import LOGS

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")

bot = telebot.TeleBot(get_bot_token())  # создаём объект бота
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


def print_list(chat_id):
    tasks = db.get_tasks(chat_id)
    categories = {
        1: "Срочное важное",
        2: "Несрочное важное",
        3: "Срочное неважное",
        4: "Мусор",
        None: "Без категории"
    }

    categorized_tasks = {category: [] for category in categories.values()}

    if tasks:
        for task in tasks:
            (task_id, user_id, sequence_number, task_description, task_date, start_time, end_time, reminder,
             category_id) = task
            task_info = f"{sequence_number}. {task_description}\n"
            if task_date:
                task_info += f"  Дата: {task_date}\n"
            if start_time:
                task_info += f"  Время начала: {start_time}\n"
            if end_time:
                task_info += f"  Время окончания: {end_time}\n"
            if reminder:
                task_info += f"  Напоминание: {reminder}\n"

            category = categories[category_id]
            categorized_tasks[category].append(task_info)

        response = "Ваши задачи:"
        for category, tasks_list in categorized_tasks.items():
            if tasks_list:
                response += f"\nКатегория: {category}\n"
                response += "".join(tasks_list)

        return response
    else:
        return "У вас нет задач."
