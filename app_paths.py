"""Пути к внешней папке res и файлам рядом с программой.

PyInstaller помещает модули в _internal (или временный _MEIPASS), но данные
приложения пользователь размещает рядом с main.exe. Не ищем БД в _internal:
запись туда может оказаться недоступной или потеряться после запуска.
"""

from pathlib import Path
import sys


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def res_path(filename):
    return app_dir() / "res" / filename
