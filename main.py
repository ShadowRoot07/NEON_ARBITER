import sys
import os
import argparse
import logging
from core.engine import Engine
from tui.app import NeonApp as App

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("NEON_MAIN")

def main():
    parser = argparse.ArgumentParser(description="NEON ARBITER")
    parser.add_argument('comando', choices=['bot_on', 'bot_off', 'tui'])
    parser.add_argument('--test', type=float)
    parser.add_argument('--scalper', action='store_true')
    args, _ = parser.parse_known_args()

    if args.comando == 'bot_on':
        # Pasamos el flag --scalper al Engine
        bot = Engine(test_balance=args.test, is_scalper=args.scalper)
        bot.start()

    elif args.comando == 'bot_off':
        print("Buscando proceso activo para detener...")
        os.system("pkill -f 'python main.py bot_on'")
        
    elif args.comando == 'tui':
        App().run()

if __name__ == '__main__':
    main()

