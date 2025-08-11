import sys
import asyncio
from qasync import QEventLoop

# Importa la lógica de monitoreo de mercado
from interface import MarketMonitor
# Importa el bucle asíncrono del bot de Telegram
from telegram_bot import process_updates
# Importa el scheduler
from scheduler import scheduler_loop

async def main():
    # Crear el bucle asíncrono
    loop = QEventLoop()
    asyncio.set_event_loop(loop)
    
    # Instanciar el monitor de mercado
    market_monitor = MarketMonitor()
    market_monitor.start_monitoring()  # Inicia el monitoreo en segundo plano
    
    # Lanzar la tarea del bot de Telegram
    telegram_task = asyncio.create_task(process_updates(asyncio.Semaphore(5)))
    
    # Lanzar el scheduler en un executor para que corra de forma bloqueante
    loop.run_in_executor(None, scheduler_loop)
    
    # El loop se mantendrá activo mientras todo esté corriendo
    await loop.run_forever()

if __name__ == '__main__':
    asyncio.run(main())
