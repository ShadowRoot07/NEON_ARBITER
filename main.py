import sys
import os
import argparse
import logging
from core.engine import Engine
from tui.app import NeonApp as App
from datetime import datetime

# --- CONFIGURACIÓN DE LOGS DINÁMICOS ---
if not os.path.exists('logs'):
    os.makedirs('logs')

# Nombre del archivo con fecha y hora: logs/2026-05-15_14-30.txt
log_filename = f"logs/{datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename), # Escribe en el archivo txt
        logging.StreamHandler()            # Mantiene la salida en terminal (Termux)
    ]
)
logger = logging.getLogger("NEON_MAIN")

def main():
    parser = argparse.ArgumentParser(description="NEON ARBITER")
    parser.add_argument('comando', choices=['bot_on', 'bot_off', 'tui'])
    parser.add_argument('--test', type=float)
    parser.add_argument('--scalper', action='store_true')
    args, _ = parser.parse_known_args()
    parser.add_argument('--duration', type=int, help="Duración de la sesión en minutos")

# Luego, en la ejecución del bot:
    if args.comando == 'bot_on':
        import asyncio
        bot = Engine(test_balance=args.test, is_scalper=args.scalper)
        
        try:
            # Pasamos la duración al motor
            asyncio.run(bot.run_bot(duration_mins=args.duration))
        except KeyboardInterrupt:
            logger.info("🛑 Bot detenido por el usuario.")

        except Exception as e:
            logger.error(f"❌ Error fatal al ejecutar el bot: {e}")

    elif args.comando == 'bot_off':
        print("Buscando proceso activo para detener...")
        os.system("pkill -f 'python main.py bot_on'")
        
    elif args.comando == 'tui':
        App().run()

if __name__ == '__main__':
    main()

