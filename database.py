import sqlite3
import threading


class Database:
    def __init__(self, db_name="tasks.db"):
        self.db_lock = threading.Lock()
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                task TEXT,
                                reminder TEXT
                              )''')
            self.conn.commit()

    def add_task(self, user_id, task, reminder=None):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO tasks (user_id, task, reminder) VALUES (?, ?, ?)", (user_id, task, reminder))
            self.conn.commit()

    def get_tasks(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE user_id=?", (user_id,))
            return cursor.fetchall()

    def delete_task(self, task_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            self.conn.commit()

    def update_task(self, task_id, new_task):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET task=? WHERE id=?", (new_task, task_id))
            self.conn.commit()

    def set_reminder(self, task_id, reminder):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET reminder=? WHERE id=?", (reminder, task_id))
            self.conn.commit()

    def get_all_tasks_with_reminders(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE reminder IS NOT NULL")
            return cursor.fetchall()

    def close(self):
        with self.db_lock:
            self.conn.close()
