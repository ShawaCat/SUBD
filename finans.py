"""Окно распределения финансирования в существующем Qt-приложении.

До открытия окна вызывающий код должен закрыть своё QSql-подключение. Здесь
используется только sqlite3; после закрытия соединение закрывается до вызова
on_close, чтобы основной интерфейс мог восстановить QSql и пересчитать итоги.
"""

import math
import sqlite3
from datetime import datetime
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from finans_pdf import report_filename, write_table_pdf


BASE_DIR = Path(__file__).resolve().parent


def allocate_amounts(plans, amount, percentage):
    """Распределить всю целую сумму по планам НИР без потери при округлении."""
    plans = [plan or 0 for plan in plans]
    total_plan = sum(plans)
    if amount <= 0 or any(plan < 0 for plan in plans) or total_plan <= 0:
        raise ValueError("Невозможно распределить сумму по плановому финансированию")
    # Процент при ручном вводе суммы округляется до 5 знаков, сумма при вводе
    # процента — до целого числа. Учитываем оба округления при проверке.
    if abs(total_plan * percentage / 100 - amount) > 0.5 + total_plan * 0.00000005 + 1e-6:
        raise ValueError("Сумма и процент распределения не совпадают")
    shares = [divmod(plan * amount, total_plan) for plan in plans]
    result = [whole for whole, _ in shares]
    remainder = amount - sum(result)
    for index in sorted(range(len(plans)), key=lambda i: (-shares[i][1], i))[:remainder]:
        result[index] += 1
    return result


class FinancingWindow(QMainWindow):
    def __init__(self, db_file=BASE_DIR / "res/data.db", on_close=None):
        super().__init__()
        uic.loadUi(str(BASE_DIR / "res/finans.ui"), self)
        self.base_dir = BASE_DIR
        self.report_quarter = None  # Квартал показанного в таблице распределения.
        self._on_close = on_close
        self._closed = False
        self.con = sqlite3.connect(str(db_file))
        self.cur = self.con.cursor()
        try:
            self.fill_data()
            positive_integer = QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$"))
            percentage = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))
            self.summ_raspred.setValidator(positive_integer)
            self.quartal_fin.setValidator(positive_integer)
            self.proc_raspred.setValidator(percentage)
            self.cancel.clicked.connect(self.close)
            self.cancel_2.clicked.connect(self.close)
            self.summ_raspred.textChanged.connect(self.summ_raspred_changed)
            self.proc_raspred.textChanged.connect(self.proc_raspred_changed)
            self.raspred.clicked.connect(self.raspred_fn)
            self.export_2.clicked.connect(self.export_pdf)
            self.write_to_db.clicked.connect(self.write_to_db_fn)
        except Exception:
            self.cur.close()
            self.con.close()
            raise

    def closeEvent(self, event):
        # Срабатывает и для кнопок «Отмена», и для системного закрытия окна.
        if not self._closed:
            self._closed = True
            self.cur.close()
            self.con.close()
            if self._on_close is not None:
                self._on_close()
        super().closeEvent(event)

    def fill_data(self):
        self.n_prog.setText(str(self.cur.execute(
            "SELECT COUNT(DISTINCT [НТП]) FROM ntp_proj").fetchone()[0]))
        self.n_vuz.setText(str(self.cur.execute(
            "SELECT COUNT(DISTINCT [ВУЗ]) FROM ntp_proj").fetchone()[0]))
        total_plan, total_fact = self.cur.execute(
            "SELECT COALESCE(SUM([План_фин]), 0), COALESCE(SUM([Факт_фин]), 0) "
            "FROM ntp_proj").fetchone()
        self.now_plan_fin.setText(str(total_plan))
        self.now_fact_fin.setText(str(total_fact))
        self.proc_fact_fin.setText(str(total_fact / total_plan * 100 if total_plan else 0))

    def summ_raspred_changed(self):
        self.proc_raspred.blockSignals(True)
        try:
            amount = self.summ_raspred.text()
            total = int(self.now_plan_fin.text())
            self.proc_raspred.setText(
                str(round(int(amount) / total * 100, 5)) if amount and total else "")
        finally:
            self.proc_raspred.blockSignals(False)

    def proc_raspred_changed(self):
        self.summ_raspred.blockSignals(True)
        try:
            percentage = self.proc_raspred.text()
            if percentage and not percentage.endswith("."):
                total = int(self.now_plan_fin.text())
                self.summ_raspred.setText(str(round(float(percentage) / 100 * total)))
            else:
                self.summ_raspred.setText("")
        finally:
            self.summ_raspred.blockSignals(False)

    def raspred_fn(self):
        if not self.summ_raspred.text():
            QMessageBox.critical(self, "Ошибка", "Не задана сумма распределения")
            return -1
        try:
            num_quart = int(self.quartal_fin.text())
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Не задан квартал финансирования")
            return -1
        if num_quart not in (1, 2, 3, 4):
            QMessageBox.critical(self, "Ошибка", "Задан некорректный квартал финансирования")
            return -1
        try:
            procent = float(self.proc_raspred.text())
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Задан некорректный процент распределения")
            return -1
        if not math.isfinite(procent) or procent < 0:
            QMessageBox.critical(self, "Ошибка", "Задан некорректный процент распределения")
            return -1
        try:
            amount = int(self.summ_raspred.text())
            plans = [row[0] for row in self.cur.execute(
                "SELECT [План_фин] FROM main.ntp_proj ORDER BY rowid").fetchall()]
            allocated = allocate_amounts(plans, amount, procent)
        except ValueError as error:
            QMessageBox.critical(self, "Ошибка", str(error))
            return -1

        # Повторное распределение заменяет снимок. Исходная БД пока не меняется.
        if any(row[1] == "ram_db" for row in self.con.execute("PRAGMA database_list")):
            self.cur.execute("DROP TABLE IF EXISTS ram_db.ntp_proj")
        else:
            self.cur.execute("ATTACH DATABASE ':memory:' AS ram_db")
        # Запоминаем настоящий rowid, т.к. [НТП, НИР] не всегда уникальны.
        self.cur.execute("""CREATE TABLE ram_db.ntp_proj AS
            SELECT rowid AS [source_rowid], *, 0 AS [Доб_фин]
            FROM main.ntp_proj ORDER BY rowid""")
        self.cur.executemany(f"""
            UPDATE ram_db.ntp_proj
            SET [Доб_фин] = ?,
                [Ф_фин_{num_quart}] = COALESCE([Ф_фин_{num_quart}], 0) + ?,
                [Факт_фин] = COALESCE([Факт_фин], 0) + ?
            WHERE rowid = ?
        """, ((part, part, part, rowid) for rowid, part in enumerate(allocated, 1)))

        vuz_totals = self.cur.execute("""
            SELECT COALESCE(v.z1, CAST(r.[ВУЗ] AS TEXT)), SUM(r.[Доб_фин])
            FROM ram_db.ntp_proj AS r
            LEFT JOIN main.VUZ AS v ON v.codvuz = r.[ВУЗ]
            GROUP BY r.[ВУЗ] ORDER BY r.[ВУЗ]
        """).fetchall()
        table_data = [*vuz_totals, ("ИТОГО К РАСПРЕДЕЛЕНИЮ", sum(allocated))]
        model = QStandardItemModel(len(table_data), 2, self)
        model.setHorizontalHeaderLabels(["ВУЗ", "К начислению"])
        for row_idx, row in enumerate(table_data):
            for col_idx, value in enumerate(row):
                model.setItem(row_idx, col_idx, QStandardItem(str(value)))
        self.report_model = model
        self.tableView.setModel(model)
        self.report_quarter = num_quart
        self.tableView.horizontalHeader().setSectionResizeMode(
            self.tableView.horizontalHeader().ResizeMode.ResizeToContents)

    def save_report(self, path, exported_at):
        """Сохранить PDF из отображаемой модели, без изменений в БД."""
        if self.report_quarter is None:
            QMessageBox.critical(self, "Ошибка экспорта", "Сначала распределите денежные средства")
            return False
        try:
            write_table_pdf(self.tableView, self.report_quarter, path, exported_at)
        except Exception as error:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF:\n{error}")
            return False
        QMessageBox.information(self, "PDF сохранён", f"Файл сохранён:\n{path}")
        return True

    def export_pdf(self):
        if self.report_quarter is None:
            QMessageBox.critical(self, "Ошибка экспорта", "Сначала распределите денежные средства")
            return
        exported_at = datetime.now()
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить распределение в PDF",
            str(self.base_dir / report_filename(exported_at)), "PDF-файлы (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.save_report(path, exported_at)

    def write_to_db_fn(self):
        """Подтвердить снимок распределения и автоматически сохранить PDF."""
        if self.report_quarter is None:
            QMessageBox.critical(self, "Ошибка", "Сначала распределите денежные средства")
            return
        try:
            self.cur.execute("""
                UPDATE main.ntp_proj
                SET [Факт_фин] = ram.[Факт_фин],
                    [Ф_фин_1] = ram.[Ф_фин_1],
                    [Ф_фин_2] = ram.[Ф_фин_2],
                    [Ф_фин_3] = ram.[Ф_фин_3],
                    [Ф_фин_4] = ram.[Ф_фин_4]
                FROM ram_db.ntp_proj AS ram
                WHERE main.ntp_proj.rowid = ram.source_rowid
            """)
            self.con.commit()
        except sqlite3.Error as error:
            self.con.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось записать финансирование:\n{error}")
            return
        self.fill_data()
        exported_at = datetime.now()
        self.save_report(self.base_dir / report_filename(exported_at), exported_at)
