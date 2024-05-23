import sqlite3
import threading


class Database:
    def __init__(self, db_name="users_tasks.db"):
        self.db_lock = threading.Lock()
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.db_lock:
            cursor = self.conn.cursor()
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
            self.conn.commit()

    def select_all_categories(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM categories")
            self.conn.commit()
            return cursor.fetchall()

    def update_category(self, sequence_number, new_category, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET category_id=? WHERE sequence_number=? AND user_id=?",
                           (new_category, sequence_number, user_id))
            self.conn.commit()

    def get_last_task(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
            return cursor.fetchone()

    def add_category(self, task_id, category_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET category_id=? WHERE id=?", (category_id, task_id))
            self.conn.commit()

    def add_user(self, chat_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()

    def add_task(self, user_id, task, reminder=None, category_name=None):
        with self.db_lock:
            cursor = self.conn.cursor()
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
            self.conn.commit()

    def update_list(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            # Получаем все задачи пользователя, отсортированные по времени добавления
            cursor.execute("SELECT id FROM tasks WHERE user_id=? ORDER BY id", (user_id,))
            tasks = cursor.fetchall()
            # Обновляем sequence_number для каждой задачи в порядке добавления
            for index, task_id in enumerate(tasks, start=1):
                cursor.execute("UPDATE tasks SET sequence_number=? WHERE id=?", (index, task_id[0]))
            self.conn.commit()

    def add_date(self, task_id, date, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET date=? WHERE id=? and user_id=?", (date, task_id, user_id))
            self.conn.commit()

    def update_date(self, sequence_number, date, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET date=? WHERE sequence_number=? and user_id=?",
                           (date, sequence_number, user_id))
            self.conn.commit()

    def add_time(self, task_id, start_time, end_time, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET start_time=?, end_time=? WHERE id=? and user_id=?",
                           (start_time, end_time, task_id, user_id))
            self.conn.commit()

    def update_task(self, sequence_number, new_task, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET task=? WHERE sequence_number=? and user_id=?",
                           (new_task, sequence_number, user_id))
            self.conn.commit()

    def update_task_start_time(self, sequence_number, start_time, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET start_time=? WHERE sequence_number=? and user_id=?",
                           (start_time, sequence_number, user_id))
            self.conn.commit()

    def update_task_end_time(self, sequence_number, end_time, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET end_time=? WHERE sequence_number=? and user_id=?",
                           (end_time, sequence_number, user_id))
            self.conn.commit()

    def get_task_by_id(self, sequence_number, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE sequence_number=? and user_id=?", (sequence_number, user_id))
            return cursor.fetchone()

    def get_tasks(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY category_id, id", (user_id,))
            return cursor.fetchall()

    def delete_task(self, sequence_number, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE sequence_number=? and user_id=?", (sequence_number, user_id))
            self.conn.commit()

    def delete_remind(self, reminder, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET reminder=? WHERE user_id=?", (reminder, user_id))
            self.conn.commit()

    def set_reminder(self, sequence_number, reminder, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET reminder=? WHERE sequence_number=? and user_id=?",
                           (reminder, sequence_number, user_id))
            self.conn.commit()

    def get_all_tasks_with_reminders(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE reminder IS NOT NULL")
            return cursor.fetchall()

    def get_all_datatime(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, task, date, start_time, end_time, reminder FROM tasks WHERE date IS NOT NULL "
                "AND start_time IS NOT NULL AND end_time IS NOT NULL")
            return cursor.fetchall()
