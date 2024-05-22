import telebot
import threading
import time
import datetime
from config import TOKEN
from database import Database

bot = telebot.TeleBot(TOKEN)
db = Database()



@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот-менеджер задач. Чтобы добавить задачу, используй команду /add.")


@bot.message_handler(commands=['add'])
def add_task(message):
    bot.reply_to(message, "Введите описание вашей задачи:")
    bot.register_next_step_handler(message, process_task_step)


def process_task_step(message):
    chat_id = message.chat.id
    task = message.text
    db.add_task(chat_id, task)
    bot.reply_to(message, "Хотите добавить дату и время к задаче? (Да/Нет)")
    bot.register_next_step_handler(message, select_datetime_step)


def select_datetime_step(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Выберите дату в формате ГГГГ-ММ-ДД")
        bot.register_next_step_handler(message, select_date_validator)
    elif option == "нет":
        bot.send_message(chat_id, "Задача добавлена без даты и времени.")
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_datetime_step)


def select_date_validator(message):
    chat_id = message.chat.id
    date = message.text
    if not validate_date(date):
        bot.reply_to(message, "Введена дата неправильного формата. Пожалуйста, введите в формате ГГГГ-ММ-ДД.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if date < current_date:
        bot.send_message(chat_id, "Ошибка: Дата задачи должна быть позже текущего времени.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    db.add_date(chat_id, date)
    bot.reply_to(message, "Дата успешно выбрана. Выбрать время (Да/Нет)?")
    bot.register_next_step_handler(message, select_time)


def select_time(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Введите время начала задачи в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_time_validator)
    elif option == "нет":
        bot.send_message(chat_id, "Дата добавлена успешно без времени!")
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_time)


def process_time_validator(message):
    chat_id = message.chat.id
    start_time = message.text
    if not validate_time(start_time):
        bot.send_message(chat_id, "Некорректное время начала задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_time_validator)
        return
    current_time = datetime.datetime.now().strftime("%H:%M")
    if start_time <= current_time:
        bot.send_message(chat_id, "Ошибка: Время начала задачи должно быть позже текущего времени.")
        bot.register_next_step_handler(message, process_time_validator)
        return
    bot.reply_to(message, "Введите время окончания задачи в формате ЧЧ:ММ")
    bot.register_next_step_handler(message, process_end_time_validator, start_time)


def process_end_time_validator(message, start_time):
    chat_id = message.chat.id
    end_time = message.text
    if not validate_time(end_time):
        bot.send_message(chat_id, "Некорректное время окончания задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time)
        return
    if end_time <= start_time:
        bot.send_message(chat_id, "Ошибка: Время окончания задачи должно быть позже времени начала.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time)
        return
    db.add_time(chat_id, start_time, end_time)
    bot.send_message(chat_id, "Время к задаче добавлено успешно!")


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


@bot.message_handler(commands=['list'])
def list_tasks(message):
    chat_id = message.chat.id
    tasks = db.get_tasks(chat_id)
    if tasks:
        response = "Ваши задачи:\n"
        for task in tasks:
            task_id, user_id, task_description, task_date, start_time, end_time, reminder = task
            response += f"{task_id}. {task_description}\n"
            if task_date:
                response += f"  Дата: {task_date}\n"
            if start_time:
                response += f"  Время начала: {start_time}\n"
            if end_time:
                response += f"  Время окончания: {end_time}\n"
            if reminder:
                response += f"  Напоминание: {reminder}\n"
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
    list_tasks(message)
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите отредактировать:")
    bot.register_next_step_handler(msg, process_edit_step)


def process_edit_step(message):
    try:
        task_id = int(message.text)
        task = db.get_task_by_id(task_id)
        if task:
            bot.reply_to(message, "Что вы хотите изменить?\n1. Описание\n2. Дату\n3. Время начала\n4. Время окончания")
            bot.register_next_step_handler(message, lambda msg: process_edit_choice(msg, task_id))
        else:
            bot.reply_to(message, "Задача с указанным номером не найдена.")
            bot.register_next_step_handler(message, process_edit_step)
    except ValueError:
        bot.reply_to(message, "Неверный формат номера задачи. Пожалуйста, введите числовое значение.")
        bot.register_next_step_handler(message, process_edit_step)


def process_edit_choice(message, task_id):
    choice = message.text.strip()
    if choice == '1':
        msg = bot.reply_to(message, "Введите новое описание задачи:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_description_step(msg, task_id))
    elif choice == '2':
        msg = bot.reply_to(message, "Введите новую дату задачи в формате ГГГГ-ММ-ДД:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_date_step(msg, task_id))
    elif choice == '3':
        msg = bot.reply_to(message, "Введите новое время начала задачи в формате ЧЧ:ММ:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_start_time_step(msg, task_id))
    elif choice == '4':
        msg = bot.reply_to(message, "Введите новое время окончания задачи в формате ЧЧ:ММ:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_end_time_step(msg, task_id))
    else:
        bot.reply_to(message, "Пожалуйста, выберите один из пунктов: 1, 2, 3 или 4.")
        bot.register_next_step_handler(message, lambda msg: process_edit_choice(msg, task_id))


def process_edit_description_step(message, task_id):
    new_description = message.text
    db.update_task(task_id, new_description)
    bot.send_message(message.chat.id, "Описание задачи успешно обновлено.")


def process_edit_date_step(message, task_id):
    chat_id = message.chat.id
    new_date = message.text
    if not validate_date(new_date):
        bot.reply_to(message, "Некорректный формат даты. Пожалуйста, введите в формате ГГГГ-ММ-ДД.")
        bot.register_next_step_handler(message, lambda msg: process_edit_date_step(msg, task_id))
        return
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d")
    if new_date < current_datetime:
        bot.reply_to(message, "Дата задачи должна быть позже текущего времени.")
        bot.register_next_step_handler(message, lambda msg: process_edit_date_step(msg, task_id))
        return
    db.add_date(task_id, new_date)
    bot.send_message(chat_id, "Дата задачи успешно обновлена.")


def process_edit_start_time_step(message, task_id):
    chat_id = message.chat.id
    new_start_time = message.text
    if not validate_time(new_start_time):
        bot.reply_to(message, "Некорректный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_edit_start_time_step(msg, task_id))
        return
    db.update_task_start_time(task_id, new_start_time)
    bot.send_message(chat_id, "Время начала задачи успешно обновлено.")


def process_edit_end_time_step(message, task_id):
    chat_id = message.chat.id
    new_end_time = message.text
    if not validate_time(new_end_time):
        bot.reply_to(message, "Некорректный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_edit_end_time_step(msg, task_id))
        return
    db.update_task_end_time(task_id, new_end_time)
    bot.send_message(chat_id, "Время окончания задачи успешно обновлено.")


@bot.message_handler(commands=['reminder'])
def set_reminder(message):
    list_tasks(message)
    msg = bot.reply_to(message, "Введите номер задачи, для которой хотите установить напоминание:")
    bot.register_next_step_handler(msg, process_reminder_step)


def process_reminder_step(message):
    msg = bot.reply_to(message, "Введите дату и время напоминания (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    bot.register_next_step_handler(msg, lambda msg: process_reminder_date_step(msg, message.text))


def process_reminder_date_step(message, task_id):
    chat_id = message.chat.id
    reminder = message.text

    try:
        reminder_datetime = datetime.datetime.strptime(reminder, "%Y-%m-%d %H:%M")
    except ValueError:
        bot.send_message(chat_id, "Некорректный формат даты и времени. Пожалуйста, введите в формате ГГГ-ММ-ДД ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
        return

    current_datetime = datetime.datetime.now()
    if reminder_datetime <= current_datetime:
        bot.send_message(chat_id, "Ошибка: Время напоминания должно быть позже текущего времени.")
        bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
        return

    task = db.get_task_by_id(task_id)
    if not task:
        bot.send_message(chat_id, "Ошибка: Задача с указанным номером не найдена.")
        return

    # Проверяем наличие даты и времени окончания задачи
    task_date = task[3]  # assuming task[3] is the date
    task_end_time = task[5]  # assuming task[5] is the end time

    if task_date and task_end_time:
        task_end_datetime_str = f"{task_date} {task_end_time}"
        try:
            task_end_datetime = datetime.datetime.strptime(task_end_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            bot.send_message(chat_id, "Ошибка в формате даты или времени окончания задачи.")
            return

        if reminder_datetime >= task_end_datetime:
            bot.send_message(chat_id, "Ошибка: Время напоминания должно быть раньше времени окончания задачи.")
            bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
            return

    db.set_reminder(task_id, reminder)
    bot.send_message(chat_id, "Напоминание установлено успешно!")


def check_reminders():
    while True:
        tasks = db.get_all_tasks_with_reminders()
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        for task in tasks:
            task_id, user_id, task_description, task_date, start_time, end_time, reminder_time = task
            if current_time == reminder_time:
                bot.send_message(user_id, f"Напоминание: {task_description}")
        time.sleep(60)  # Проверяем каждую минуту


reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.start()

if __name__ == "__main__":
    bot.polling()
