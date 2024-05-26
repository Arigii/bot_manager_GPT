import logging
import sqlite3
from config import DB_FILE, LOGS

db_name = DB_FILE

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")


def create_tables():
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                        id INTEGER PRIMARY KEY,
                                        chat_id TEXT UNIQUE
                                      )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                                        id INTEGER PRIMARY KEY,
                                        name TEXT UNIQUE
                                      )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                                        id INTEGER PRIMARY KEY,
                                        user_id INTEGER,
                                        sequence_number INTEGER,
                                        task TEXT,
                                        date DATE,
                                        start_time TEXT,
                                        end_time TEXT,
                                        reminder TEXT,
                                        category_id INTEGER,
                                        FOREIGN KEY (user_id) REFERENCES users (id),
                                        FOREIGN KEY (category_id) REFERENCES categories (id)
                                      )''')
            cursor.execute(
                "INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'Срочное важное'), (2, 'Несрочное важное'), "
                "(3, 'Срочное неважное'), (4, 'Мусор')")
            conn.commit()
    except ValueError as e:
        # Обработка ошибок
        logging.error(f"Ошибка создания и добавления значений в бд: {e}")


def select_all_categories():
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories")
            conn.commit()
            return cursor.fetchall()
    except ValueError as e:
        logging.error(f"select_all_categories: {e}")


def update_category(sequence_number, new_category, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET category_id=? WHERE sequence_number=? AND user_id=?",
                           (new_category, sequence_number, user_id))
            conn.commit()
    except ValueError as e:
        logging.error(f"update_category: {e}")


def get_last_task(user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
            return cursor.fetchone()
    except ValueError as e:
        logging.error(f"get_last_task: {e}")


def add_category(task_id, category_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET category_id=? WHERE id=?", (category_id, task_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"add_category: {e}")


def add_user(chat_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except ValueError as e:
        logging.error(f"add_user: {e}")


def add_task(user_id, task, reminder=None, category_name=None):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(sequence_number) FROM tasks WHERE user_id=?", (user_id,))
            max_sequence_number = cursor.fetchone()[0]
            if max_sequence_number is None:
                sequence_number = 1
            else:
                sequence_number = max_sequence_number + 1

            category_id = None
            if category_name:
                cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
                category_id = cursor.fetchone()
                if category_id:
                    category_id = category_id[0]

            cursor.execute(
                "INSERT INTO tasks (user_id, sequence_number, task, reminder, category_id) VALUES (?, ?, ?, ?, ?)",
                (user_id, sequence_number, task, reminder, category_id))
            conn.commit()
    except ValueError as e:
        logging.error(f"add_task: {e}")


def update_list(user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            # Получаем все задачи пользователя, отсортированные по времени добавления
            cursor.execute("SELECT id FROM tasks WHERE user_id=? ORDER BY id", (user_id,))
            tasks = cursor.fetchall()
            # Обновляем sequence_number для каждой задачи в порядке добавления
            for index, task_id in enumerate(tasks, start=1):
                cursor.execute("UPDATE tasks SET sequence_number=? WHERE id=?", (index, task_id[0]))
            conn.commit()
    except ValueError as e:
        logging.error(f"update_list: {e}")


def add_date(task_id, date, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET date=? WHERE id=? and user_id=?", (date, task_id, user_id))
            conn.commit()
    except ValueError as e:
        logging.error(f"add_date: {e}")


def update_date(sequence_number, date, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET date=? WHERE sequence_number=? and user_id=?",
                       (date, sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"update_date: {e}")


def add_time(task_id, start_time, end_time, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET start_time=?, end_time=? WHERE id=? and user_id=?",
                       (start_time, end_time, task_id, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"add_time: {e}")


def update_task(sequence_number, new_task, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET task=? WHERE sequence_number=? and user_id=?",
                       (new_task, sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"update_task: {e}")


def update_task_start_time(sequence_number, start_time, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET start_time=? WHERE sequence_number=? and user_id=?",
                       (start_time, sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"update_task_start_time: {e}")


def update_task_end_time(sequence_number, end_time, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET end_time=? WHERE sequence_number=? and user_id=?",
                       (end_time, sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"update_task_end_time: {e}")


def get_task_by_id(sequence_number, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE sequence_number=? and user_id=?", (sequence_number, user_id))
        return cursor.fetchone()
    except ValueError as e:
        logging.error(f"get_task_by_id: {e}")


def get_tasks(user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY category_id, id", (user_id,))
        return cursor.fetchall()
    except ValueError as e:
        logging.error(f"get_tasks: {e}")


def delete_task(sequence_number, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE sequence_number=? and user_id=?", (sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"delete_task: {e}")


def delete_remind(reminder, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET reminder=? WHERE user_id=?", (reminder, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"delete_remind: {e}")


def set_reminder(sequence_number, reminder, user_id):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET reminder=? WHERE sequence_number=? and user_id=?",
                       (reminder, sequence_number, user_id))
        conn.commit()
    except ValueError as e:
        logging.error(f"set_reminder: {e}")


def get_all_tasks_with_reminders():
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE reminder IS NOT NULL")
        return cursor.fetchall()
    except ValueError as e:
        logging.error(f"get_all_tasks_with_reminders: {e}")


def get_all_datatime():
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, task, date, start_time, end_time, reminder FROM tasks WHERE date IS NOT NULL "
            "AND start_time IS NOT NULL AND end_time IS NOT NULL")
        return cursor.fetchall()
    except ValueError as e:
        logging.error(f"get_all_datatime: {e}")
