"""LightchangerT entry point. Delegates to python/main.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python'))
from main import *  # noqa
if __name__ == "__main__":
    GameStateController().run()
