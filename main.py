import sys
import os
from core.engine import Engine
from tui.app import App

if __name__ == '__main__':
    if sys.argv[1] == 'bot_on':
        Engine().start()
    elif sys.argv[1] == 'bot_off':
        Engine().stop()
    elif sys.argv[1] == 'tui':
        App().run()
    else:
        print('Comando no reconocido')
