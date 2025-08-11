#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lógica de Higgs X – Monitor de Trading

Se centra en:
  - Monitoreo de indicadores técnicos en tiempo real.
  - Lógica de obtención y cálculo delegada a módulos externos.
  - Envío de mensajes a Telegram con el estado del mercado.
"""

import threading
import time
import logging
from datetime import datetime
import pytz

from market import fetch_data, start_dominance_monitor  # Asegúrate de importar la función start_dominance_monitor
from indicators import calculate_indicators
from config import SYMBOL, TIMEFRAME
from telegram_bot import telegram_bot_loop
from trading_signals import monitor_signals

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class MarketMonitor:
    def __init__(self):
        self.monitoring = False
        self.signals_thread_started = False

    def start_monitoring(self):
        logging.info("Monitoreando mercado...")
        # Iniciar el monitoreo de indicadores en un hilo
        threading.Thread(target=self.monitor_market, daemon=True).start()
        # Iniciar el monitoreo de señales si aún no se ha iniciado
        if not self.signals_thread_started:
            threading.Thread(target=monitor_signals, daemon=True).start()
            self.signals_thread_started = True

        # Iniciar el monitor de dominancia de BTC
        start_dominance_monitor()

    def monitor_market(self):
        while True:
            try:
                data = fetch_data(SYMBOL, TIMEFRAME)
                indicadores = calculate_indicators(data)
                dominance_text = f"{indicadores['btc_dominance']:.2f}%" if indicadores.get('btc_dominance') is not None else "N/D"
                
                general_msg = (
                    f"📊 {SYMBOL}:\n"
                    f"Precio: ${indicadores['price']:.2f}\n"
                    f"RSI: {indicadores['rsi']:.2f}\n"
                    f"MACD: {indicadores['macd']:.2f} (Señal: {indicadores['macd_signal']:.2f})\n"
                    f"ADX: {indicadores['adx']:.2f}\n"
                    f"SMA: {indicadores['sma_10']:.2f} / {indicadores['sma_25']:.2f} / {indicadores['sma_50']:.2f}\n"
                    f"Volumen: {indicadores['volume_level']} (CMF: {indicadores['cmf']:.2f})\n"
                    f"Bandas de Bollinger: Low ${indicadores['bb_low']:.2f}, Med ${indicadores['bb_medium']:.2f}, High ${indicadores['bb_high']:.2f}\n"
                    f"BTC Dominancia: {dominance_text}"
                )
                logging.info(general_msg)  # Mostrar en log

                # Enviar mensaje a Telegram
                self.send_to_telegram(general_msg)
                time.sleep(10)
            except Exception as e:
                logging.error(f"Error: {e}")
                break

    def send_to_telegram(self, message):
        # Llamar al bot de Telegram para enviar el mensaje
        logging.info("Enviando mensaje a Telegram...")
        # Aquí puedes utilizar tu función para enviar el mensaje a Telegram (ya está definida en telegram_bot.py)
        telegram_bot_loop()


def run_market_monitor():
    # Iniciar el monitoreo
    monitor = MarketMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    # Ejecutar la lógica de monitoreo en Railway (sin interfaz)
    run_market_monitor()
