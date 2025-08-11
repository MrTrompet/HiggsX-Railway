import sqlite3
import time
import datetime
import threading
import logging
import openai
from telegram_handler import send_telegram_message
from memoria import get_pending_tasks, update_task_status

# Configuración de logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def execute_task(task):
    """
    Ejecuta una tarea pendiente.
    La tarea contiene la descripción completa que actuará como prompt para GPT‑4.
    Se envía la respuesta a Telegram y se actualiza el estado de la tarea a 'completed'.
    """
    task_id = task['id']
    prompt = task['description']
    logging.info(f"Ejecutando tarea ID {task_id} con prompt: {prompt}")

    system_prompt = (
        "Eres Higgs X, el agente de inteligencia encargado de vigilar el ecosistema blockchain. "
        "Responde de forma concisa, seria y con un toque de misterio, y protege al equipo de pérdidas."
    )
    context = prompt

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        answer = response.choices[0].message.content.strip()
        send_telegram_message(f"[Tarea Programada]\n{answer}")
        logging.info(f"Tarea ID {task_id} ejecutada correctamente.")
        update_task_status(task_id, 'completed')
    except Exception as e:
        logging.error(f"Error al ejecutar la tarea ID {task_id}: {e}")

def dynamic_scheduler_loop():
    """
    Bucle que revisa cada 10 segundos la tabla de tareas pendientes.
    Si alguna tarea tiene un scheduled_time menor o igual que la hora actual, se ejecuta.
    """
    while True:
        tasks = get_pending_tasks()
        now = datetime.datetime.now()  # Hora local
        logging.info(f"Hora actual: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Tareas pendientes: {tasks}")
        for task in tasks:
            scheduled_time_str = task['scheduled_time']
            try:
                scheduled_time = datetime.datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logging.error(f"Error parseando la fecha de tarea {task}: {e}")
                continue
            logging.info(f"Tarea ID {task['id']} programada para {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if now >= scheduled_time:
                logging.info(f"Hora actual supera la tarea ID {task['id']}; se procede a ejecutar.")
                execute_task(task)
        time.sleep(10)

def start_dynamic_scheduler():
    threading.Thread(target=dynamic_scheduler_loop, daemon=True).start()

if __name__ == '__main__':
    start_dynamic_scheduler()
    while True:
        time.sleep(1)
