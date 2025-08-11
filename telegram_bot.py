import asyncio
import time
from telegram_handler import get_updates, handle_telegram_message

async def process_updates(semaphore):
    offset = None  # Inicializa el offset para evitar mensajes duplicados
    while True:
        try:
            updates = get_updates(offset)
            print(f"[Telegram Bot] Recibidos {len(updates)} actualizaciones")  # Log del número de actualizaciones recibidas
            if updates:
                for update in updates:
                    update_id = update.get("update_id")
                    print(f"[Telegram Bot] Procesando actualización con ID: {update_id}")  # Log del ID de la actualización
                    async with semaphore:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, handle_telegram_message, update)
                    offset = update_id + 1  # Actualiza el offset para futuros mensajes
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[Telegram Bot] Error en el bucle del bot: {e}")
            await asyncio.sleep(10)

def telegram_bot_loop(message=None):

    """
    Bucle principal para escuchar mensajes de Telegram de forma asíncrona.
    Se utiliza un semáforo para limitar las actualizaciones procesadas simultáneamente.
    """
    semaphore = asyncio.Semaphore(5)
    
    # Si se pasa un mensaje, procesarlo
    if message:
        print(f"Enviando mensaje a Telegram: {message}")
        # Aquí iría tu lógica para enviar el mensaje al grupo de Telegram (dependiendo de tu implementación)
        # Ejemplo:
        # bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    
    # Luego ejecutamos el ciclo principal de actualizaciones
    asyncio.create_task(process_updates(semaphore))

if __name__ == "__main__":
    telegram_bot_loop()  # Esto ahora ejecutará el bucle de actualizaciones
