"""Распределение финансирования в окне основного Qt-приложения.

Как и другие окна main.py, форма хранится в finWindow, а обработчики сигналов
работают с ней напрямую. Основное QSql-подключение закрывается до открытия
окна и восстанавливается переданным обработчиком после закрытия sqlite3.
"""

import math
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QRegularExpression, Qt
from PyQt6.QtGui import QRegularExpressionValidator, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from finans_pdf import report_filename, write_table_pdf


BASE_DIR = Path(__file__).resolve().parent
finWindow = None
con = None
cur = None
report_quarter = None  # Квартал распределения, показанного в таблице.
on_close = None
PERCENT_PATTERN = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"


def open_financing_window(db_file=BASE_DIR / "res/data.db", on_close_callback=None):
    """Создать форму и соединение sqlite3 в существующем QApplication."""
    global finWindow, con, cur, report_quarter, on_close
    finWindow = uic.loadUi(str(BASE_DIR / "res/finans.ui"))
    flags = finWindow.windowFlags()
    # Как и в остальных окнах программы, закрытие производится кнопкой формы.
    finWindow.setWindowFlags(
        flags & ~Qt.WindowType.WindowCloseButtonHint
        & ~Qt.WindowType.WindowMinimizeButtonHint
        & ~Qt.WindowType.WindowMaximizeButtonHint
    )
    # При системном закрытии (например, Alt+F4) тоже освобождаем БД.
    finWindow.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    finWindow.destroyed.connect(finish_financing)
    con = sqlite3.connect(str(db_file))
    cur = con.cursor()
    report_quarter = None
    on_close = on_close_callback
    fill_data()

    positive_integer = QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$"))
    percentage = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))
    finWindow.summ_raspred.setValidator(positive_integer)
    finWindow.quartal_fin.setValidator(positive_integer)
    finWindow.proc_raspred.setValidator(percentage)
    finWindow.cancel.clicked.connect(cancel_btn)
    finWindow.cancel_2.clicked.connect(cancel_btn)
    finWindow.summ_raspred.textChanged.connect(summ_raspred_changed)
    finWindow.proc_raspred.textChanged.connect(proc_raspred_changed)
    finWindow.raspred.clicked.connect(raspred_fn)
    finWindow.export_2.clicked.connect(export_pdf)
    finWindow.write_to_db.clicked.connect(write_to_db)
    return finWindow


def cancel_btn():
    if finWindow is not None:
        finWindow.close()


def finish_financing():
    """Освободить SQLite до восстановления главной таблицы через QSql."""
    global finWindow, con, cur, on_close, report_quarter
    if con is None:
        return
    cur.close()
    con.close()
    finWindow = None
    con = None
    cur = None
    report_quarter = None
    callback = on_close
    on_close = None
    if callback is not None:
        callback()


def fill_data():
    finWindow.n_prog.setText(str(cur.execute(
        "SELECT COUNT(DISTINCT [НТП]) FROM ntp_proj").fetchone()[0]))
    finWindow.n_vuz.setText(str(cur.execute(
        "SELECT COUNT(DISTINCT [ВУЗ]) FROM ntp_proj").fetchone()[0]))
    total_plan, total_fact = cur.execute(
        "SELECT COALESCE(SUM([План_фин]), 0), COALESCE(SUM([Факт_фин]), 0) "
        "FROM ntp_proj").fetchone()
    finWindow.now_plan_fin.setText(str(total_plan))
    finWindow.now_fact_fin.setText(str(total_fact))
    finWindow.proc_fact_fin.setText(str(round(total_fact / total_plan * 100, 3))
                                     if total_plan else "0")


def summ_raspred_changed():
    amount = finWindow.summ_raspred.text()
    total = int(finWindow.now_plan_fin.text())
    finWindow.proc_raspred.blockSignals(True)
    if amount.isdecimal() and total:
        finWindow.proc_raspred.setText(str(round(int(amount) / total * 100, 5)))
    else:
        finWindow.proc_raspred.setText("")
    finWindow.proc_raspred.blockSignals(False)


def proc_raspred_changed():
    percentage = finWindow.proc_raspred.text()
    total = int(finWindow.now_plan_fin.text())
    finWindow.summ_raspred.blockSignals(True)
    if re.fullmatch(PERCENT_PATTERN, percentage) and not percentage.endswith("."):
        amount = float(percentage) / 100 * total
        finWindow.summ_raspred.setText(str(round(amount)) if math.isfinite(amount) else "")
    else:
        finWindow.summ_raspred.setText("")
    finWindow.summ_raspred.blockSignals(False)


def allocate_amounts(plans, amount, percentage):
    """Распределить всю целую сумму по планам НИР без потери при округлении."""
    plans = [plan or 0 for plan in plans]
    total_plan = sum(plans)
    if amount <= 0 or any(plan < 0 for plan in plans) or total_plan <= 0:
        raise ValueError("Невозможно распределить сумму по плановому финансированию")
    # Ручной ввод суммы округляет процент до 5 знаков, ввод процента — сумму
    # до целого числа. Допускаем только погрешность этих двух округлений.
    if abs(total_plan * percentage / 100 - amount) > 0.5 + total_plan * 0.00000005 + 1e-6:
        raise ValueError("Сумма и процент распределения не совпадают")
    shares = [divmod(plan * amount, total_plan) for plan in plans]
    result = [whole for whole, _ in shares]
    remainder = amount - sum(result)
    for index in sorted(range(len(plans)), key=lambda i: (-shares[i][1], i))[:remainder]:
        result[index] += 1
    return result


def raspred_fn():
    global report_quarter
    amount_text = finWindow.summ_raspred.text()
    quarter_text = finWindow.quartal_fin.text()
    percentage_text = finWindow.proc_raspred.text()

    if not amount_text:
        QMessageBox.critical(finWindow, "Ошибка", "Не задана сумма распределения")
        return -1
    if not amount_text.isdecimal():
        QMessageBox.critical(finWindow, "Ошибка", "Задана некорректная сумма распределения")
        return -1
    if not quarter_text:
        QMessageBox.critical(finWindow, "Ошибка", "Не задан квартал финансирования")
        return -1
    if quarter_text not in ("1", "2", "3", "4"):
        QMessageBox.critical(finWindow, "Ошибка", "Задан некорректный квартал финансирования")
        return -1
    if not re.fullmatch(PERCENT_PATTERN, percentage_text):
        QMessageBox.critical(finWindow, "Ошибка", "Задан некорректный процент распределения")
        return -1

    num_quart = int(quarter_text)
    procent = float(percentage_text)
    if not math.isfinite(procent):
        QMessageBox.critical(finWindow, "Ошибка", "Задан некорректный процент распределения")
        return -1
    amount = int(amount_text)
    plans = [row[0] for row in cur.execute(
        "SELECT [План_фин] FROM main.ntp_proj ORDER BY rowid").fetchall()]
    total_plan = sum(plan or 0 for plan in plans)
    if amount <= 0 or total_plan <= 0 or any(plan is not None and plan < 0 for plan in plans):
        QMessageBox.critical(finWindow, "Ошибка",
                             "Невозможно распределить сумму по плановому финансированию")
        return -1
    if abs(total_plan * procent / 100 - amount) > 0.5 + total_plan * 0.00000005 + 1e-6:
        QMessageBox.critical(finWindow, "Ошибка", "Сумма и процент распределения не совпадают")
        return -1
    allocated = allocate_amounts(plans, amount, procent)

    # Повторное распределение заменяет снимок. Исходная БД пока не меняется.
    if any(row[1] == "ram_db" for row in con.execute("PRAGMA database_list")):
        cur.execute("DROP TABLE IF EXISTS ram_db.ntp_proj")
    else:
        cur.execute("ATTACH DATABASE ':memory:' AS ram_db")
    # Запоминаем настоящий rowid: [НТП, НИР] не всегда уникальны.
    cur.execute("""CREATE TABLE ram_db.ntp_proj AS
        SELECT rowid AS [source_rowid], *, 0 AS [Доб_фин]
        FROM main.ntp_proj ORDER BY rowid""")
    cur.executemany(f"""
        UPDATE ram_db.ntp_proj
        SET [Доб_фин] = ?,
            [Ф_фин_{num_quart}] = COALESCE([Ф_фин_{num_quart}], 0) + ?,
            [Факт_фин] = COALESCE([Факт_фин], 0) + ?
        WHERE rowid = ?
    """, ((part, part, part, rowid) for rowid, part in enumerate(allocated, 1)))

    vuz_totals = cur.execute("""
        SELECT COALESCE(v.z1, CAST(r.[ВУЗ] AS TEXT)), SUM(r.[Доб_фин])
        FROM ram_db.ntp_proj AS r
        LEFT JOIN main.VUZ AS v ON v.codvuz = r.[ВУЗ]
        GROUP BY r.[ВУЗ] ORDER BY r.[ВУЗ]
    """).fetchall()
    table_data = [*vuz_totals, ("ИТОГО К РАСПРЕДЕЛЕНИЮ", sum(allocated))]
    model = QStandardItemModel(len(table_data), 2, finWindow)
    model.setHorizontalHeaderLabels(["ВУЗ", "К начислению"])
    for row_idx, row in enumerate(table_data):
        for col_idx, value in enumerate(row):
            model.setItem(row_idx, col_idx, QStandardItem(str(value)))
    finWindow.report_model = model
    finWindow.tableView.setModel(model)
    report_quarter = num_quart
    finWindow.tableView.horizontalHeader().setSectionResizeMode(
        finWindow.tableView.horizontalHeader().ResizeMode.ResizeToContents)


def save_report(path, exported_at):
    """Сохранить PDF из отображаемой модели, без изменений в БД."""
    if report_quarter is None:
        QMessageBox.critical(finWindow, "Ошибка экспорта", "Сначала распределите денежные средства")
        return False
    try:
        write_table_pdf(finWindow.tableView, report_quarter, path, exported_at)
    except Exception as error:
        QMessageBox.critical(finWindow, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{error}")
        return False
    QMessageBox.information(finWindow, "PDF сохранён", f"Файл сохранён:\n{path}")
    
    return True


def export_pdf():
    if report_quarter is None:
        QMessageBox.critical(finWindow, "Ошибка экспорта", "Сначала распределите денежные средства")
        return
    exported_at = datetime.now()
    path, _ = QFileDialog.getSaveFileName(
        finWindow, "Сохранить распределение в PDF",
        str(BASE_DIR / report_filename(exported_at)), "PDF-файлы (*.pdf)")
    if not path:
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    save_report(path, exported_at)


def write_to_db():
    """Подтвердить снимок распределения и автоматически сохранить PDF."""
    if report_quarter is None:
        QMessageBox.critical(finWindow, "Ошибка", "Сначала распределите денежные средства")
        return
    cur.execute("""
        UPDATE main.ntp_proj
        SET [Факт_фин] = ram.[Факт_фин],
            [Ф_фин_1] = ram.[Ф_фин_1],
            [Ф_фин_2] = ram.[Ф_фин_2],
            [Ф_фин_3] = ram.[Ф_фин_3],
            [Ф_фин_4] = ram.[Ф_фин_4]
        FROM ram_db.ntp_proj AS ram
        WHERE main.ntp_proj.rowid = ram.source_rowid
    """)
    con.commit()
    fill_data()
    exported_at = datetime.now()
    save_report(BASE_DIR / report_filename(exported_at), exported_at)
    cancel_btn()
