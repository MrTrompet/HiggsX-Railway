import sqlite3
import time
import datetime

DB_NAME = 'higgs_memory.db'

def init_db():
    """Crea la base de datos y las tablas necesarias si no existen.
    Se crean dos tablas:
      - messages: para almacenar el historial de mensajes (inputs y respuestas)
      - tasks: para almacenar tareas programadas, con la hora de ejecución prevista.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabla para mensajes del chat
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            username TEXT,
            content TEXT
        )
    ''')
    # Tabla para tareas programadas
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_time TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

def store_message(username, content):
    """Almacena un mensaje en la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
    conn.commit()
    conn.close()

def get_recent_messages(limit=10):
    """Recupera los últimos 'limit' mensajes, en orden cronológico."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT timestamp, username, content FROM messages ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    messages = [f"[{ts}] {username}: {content}" for ts, username, content in rows]
    return "\n".join(messages[::-1])

def add_task(description, scheduled_time):
    """
    Agrega una nueva tarea programada a la base de datos.
    Se asegura de almacenar el scheduled_time en formato "%Y-%m-%d %H:%M:%S".
    """
    if isinstance(scheduled_time, datetime.datetime):
        scheduled_time_str = scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        scheduled_time_str = str(scheduled_time)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO tasks (scheduled_time, description) VALUES (?, ?)', (scheduled_time_str, description))
    conn.commit()
    conn.close()

def update_task_status(task_id, new_status):
    """Actualiza el estado de una tarea."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', (new_status, task_id))
    conn.commit()
    conn.close()

def get_pending_tasks():
    """Recupera todas las tareas pendientes y las devuelve como lista de diccionarios."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    c = conn.cursor()
    c.execute("SELECT id, scheduled_time, description FROM tasks WHERE status = ?", ('pending',))
    rows = c.fetchall()
    conn.close()
    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "scheduled_time": str(row["scheduled_time"]).strip(),  # Forzamos a string
            "description": row["description"]
        })
    return tasks

# Inicialización de la base de datos al importar el módulo
init_db()
