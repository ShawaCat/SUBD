"""Отдельный запуск того же окна на тестовой базе; без второго QApplication при импорте."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication
from finans import FinancingWindow


def main():
    app = QApplication(sys.argv)
    window = FinancingWindow(Path(__file__).parent / "res/data.db")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
