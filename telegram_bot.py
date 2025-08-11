import asyncio
import time
from telegram_handler import get_updates, handle_telegram_message

async def process_updates(semaphore):
    offset = None  # Inicializa el offset para evitar mensajes duplicados
    while True:
        try:
            updates = get_updates(offset)
            if updates:
                for update in updates:
                    update_id = update.get("update_id")
                    async with semaphore:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, handle_telegram_message, update)
                    offset = update_id + 1  # Actualiza el offset para futuros mensajes
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Error en el bucle del bot: {e}")
            await asyncio.sleep(10)

def telegram_bot_loop():
    """
    Bucle principal para escuchar mensajes de Telegram de forma asíncrona.
    Se utiliza un semáforo para limitar las actualizaciones procesadas simultáneamente.
    """
    semaphore = asyncio.Semaphore(5)
    asyncio.run(process_updates(semaphore))

if __name__ == "__main__":
    telegram_bot_loop()
