import telebot
import threading
import time
from config import TOKEN
from database import Database

bot = telebot.TeleBot(TOKEN)
db = Database()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот-менеджер задач. Чтобы добавить задачу, используй команду /add.")


@bot.message_handler(commands=['add'])
def add_task(message):
    msg = bot.reply_to(message, "Введите вашу задачу:")
    bot.register_next_step_handler(msg, process_task_step)


def process_task_step(message):
    chat_id = message.chat.id
    task = message.text
    db.add_task(chat_id, task)
    bot.send_message(chat_id, "Задача добавлена успешно!")


@bot.message_handler(commands=['list'])
def list_tasks(message):
    chat_id = message.chat.id
    tasks = db.get_tasks(chat_id)
    if tasks:
        response = "Ваши задачи:\n"
        for task in tasks:
            response += f"{task[0]}. {task[2]}\n"
        bot.send_message(chat_id, response)
    else:
        bot.send_message(chat_id, "У вас нет задач.")


@bot.message_handler(commands=['delete'])
def delete_task(message):
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите удалить:")
    bot.register_next_step_handler(msg, process_delete_step)


def process_delete_step(message):
    chat_id = message.chat.id
    task_id = int(message.text)
    db.delete_task(task_id)
    bot.send_message(chat_id, "Задача удалена успешно!")


@bot.message_handler(commands=['edit'])
def edit_task(message):
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите отредактировать:")
    bot.register_next_step_handler(msg, process_edit_step)


def process_edit_step(message):
    msg = bot.reply_to(message, "Введите новое описание задачи:")
    bot.register_next_step_handler(msg, lambda msg: process_edit_description_step(msg, message.text))


def process_edit_description_step(message, task_id):
    chat_id = message.chat.id
    new_task = message.text
    db.update_task(task_id, new_task)
    bot.send_message(chat_id, "Задача отредактирована успешно!")


@bot.message_handler(commands=['reminder'])
def set_reminder(message):
    msg = bot.reply_to(message, "Введите номер задачи, для которой хотите установить напоминание:")
    bot.register_next_step_handler(msg, process_reminder_step)


def process_reminder_step(message):
    msg = bot.reply_to(message, "Введите дату и время напоминания (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    bot.register_next_step_handler(msg, lambda msg: process_reminder_date_step(msg, message.text))


def process_reminder_date_step(message, task_id):
    chat_id = message.chat.id
    reminder = message.text
    db.set_reminder(task_id, reminder)
    bot.send_message(chat_id, "Напоминание установлено успешно!")


def check_reminders():
    while True:
        tasks = db.get_all_tasks_with_reminders()
        current_time = time.strftime("%Y-%m-%d %H:%M")
        print(current_time)
        for task in tasks:
            task_id, user_id, task_description, reminder_time = task
            if current_time == reminder_time:
                bot.send_message(user_id, f"Напоминание: {task_description}")
        time.sleep(60)  # Проверяем каждую минуту


reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.start()

if __name__ == "__main__":
    bot.polling()
