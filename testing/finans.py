import math
import sqlite3
from datetime import datetime
from pathlib import Path

from pdf_report import report_filename, write_table_pdf
from PyQt6 import uic
from PyQt6.QtWidgets import *
from PyQt6.QtSql import *
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QRegularExpression, QItemSelectionModel, QModelIndex, QItemSelection
from tkinter import messagebox
from PyQt6.QtGui import QRegularExpressionValidator, QStandardItemModel, QStandardItem

BASE_DIR = Path(__file__).resolve().parent

app = QApplication([])
finWindow = uic.loadUi(str(BASE_DIR / "res/finans.ui"))
report_quarter = None  # Квартал того распределения, которое показано в TableView.
flags = finWindow.windowFlags()
finWindow.setWindowFlags(
    flags &
    ~Qt.WindowType.WindowCloseButtonHint &
    ~Qt.WindowType.WindowMinimizeButtonHint &
    ~Qt.WindowType.WindowMaximizeButtonHint
)

def fill_data():
    cur.execute("SELECT [НТП] FROM ntp_proj")
    code_NTP = cur.fetchall()
    code_NTP = list(set(code_NTP))
    finWindow.n_prog.setText(str(len(code_NTP)))

    cur.execute("SELECT [ВУЗ] FROM ntp_proj")
    code_VUZ = cur.fetchall()
    code_VUZ = list(set(code_VUZ))
    finWindow.n_vuz.setText(str(len(code_VUZ)))

    cur.execute("SELECT [План_фин] FROM ntp_proj")
    plan_fin = cur.fetchall()
    for i in range(len(plan_fin)):
        plan_fin[i] = plan_fin[i][0]
    finWindow.now_plan_fin.setText(str(sum(plan_fin)))

    cur.execute("SELECT [Факт_фин] FROM ntp_proj")
    fact_fin = cur.fetchall()
    for i in range(len(fact_fin)):
        fact_fin[i] = fact_fin[i][0]
    finWindow.now_fact_fin.setText(str(sum(fact_fin)))

    procent_fact = (sum(fact_fin) / sum(plan_fin)) * 100
    finWindow.proc_fact_fin.setText(str(procent_fact))

def cancel_btn():
    cur.close()
    con.close()
    # connect_db(db_file)
    # open_tab_1()
    finWindow.close()

def summ_raspred_changed():
    if finWindow.summ_raspred.text() != "" and not ("." in finWindow.summ_raspred.text()):
        finWindow.proc_raspred.blockSignals(True)
        now_plan = int(finWindow.now_plan_fin.text())
        summa_raspred = int(finWindow.summ_raspred.text())
        procent = (summa_raspred / now_plan) * 100
        finWindow.proc_raspred.setText(str(round(procent, 5)))
        finWindow.proc_raspred.blockSignals(False)
    else:
        finWindow.proc_raspred.blockSignals(True)
        finWindow.proc_raspred.setText("")
        finWindow.proc_raspred.blockSignals(False)

def proc_raspred_changed():
    if finWindow.proc_raspred.text() != "" and not (finWindow.proc_raspred.text()[-1] == "."):
        print(finWindow.proc_raspred.text())
        finWindow.summ_raspred.blockSignals(True)
        now_plan = int(finWindow.now_plan_fin.text())
        a = finWindow.proc_raspred.text()
        procent_raspred = float(finWindow.proc_raspred.text())
        summa = (procent_raspred / 100) * now_plan
        finWindow.summ_raspred.setText(str(round(summa)))
        finWindow.summ_raspred.blockSignals(False)
    else:
        finWindow.summ_raspred.blockSignals(True)
        finWindow.summ_raspred.setText("")
        finWindow.summ_raspred.blockSignals(False)

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


def raspred_fn():
    global report_quarter

    if finWindow.summ_raspred.text() == "":
        messagebox.showerror("Ошибка", "Не задана сумма распределения")
        return -1
    if finWindow.quartal_fin.text() == "":
        messagebox.showerror("Ошибка", "Не задан квартал финансирования")
        return -1
    try:
        num_quart = int(finWindow.quartal_fin.text())
    except ValueError:
        messagebox.showerror("Ошибка", "Задан некорректный квартал финансирования")
        return -1
    if not 1 <= num_quart <= 4:
        messagebox.showerror("Ошибка", "Задан некорректный квартал финансирования")
        return -1

    # Процент из LineEdit может быть дробным (например, 10.5).
    try:
        procent = float(finWindow.proc_raspred.text())
    except ValueError:
        messagebox.showerror("Ошибка", "Задан некорректный процент распределения")
        return -1
    if not math.isfinite(procent) or procent < 0:
        messagebox.showerror("Ошибка", "Задан некорректный процент распределения")
        return -1
    try:
        amount = int(finWindow.summ_raspred.text())
        plans = [row[0] for row in cur.execute(
            "SELECT [План_фин] FROM main.ntp_proj ORDER BY rowid"
        ).fetchall()]
        allocated = allocate_amounts(plans, amount, procent)
    except ValueError as error:
        messagebox.showerror("Ошибка", str(error))
        return -1

    # Повторное распределение создаёт новый снимок; ram_db уже может быть подключена.
    if any(row[1] == "ram_db" for row in con.execute("PRAGMA database_list")):
        cur.execute("DROP TABLE IF EXISTS ram_db.ntp_proj")
    else:
        cur.execute("ATTACH DATABASE ':memory:' AS ram_db")
    cur.execute("""CREATE TABLE ram_db.ntp_proj AS
        SELECT *, 0 AS [Доб_фин] FROM main.ntp_proj ORDER BY rowid""")
    # Виртуальные rowid здесь 1..N в том же порядке, что и планы выше.
    cur.executemany(f"""
        UPDATE ram_db.ntp_proj
        SET [Доб_фин] = ?,
            [Ф_фин_{num_quart}] = COALESCE([Ф_фин_{num_quart}], 0) + ?,
            [Факт_фин] = COALESCE([Факт_фин], 0) + ?
        WHERE rowid = ?
    """, ((part, part, part, rowid) for rowid, part in enumerate(allocated, 1)))


    list_vuz = []
    list_added_fin = []
    table_data = []
    cur.execute("SELECT [ВУЗ], [Доб_фин] FROM ram_db.ntp_proj")
    vuz_fin = cur.fetchall()
    for i in vuz_fin:
        list_vuz.append(i[0])
    list_vuz = list(set(list_vuz))
    list_vuz.sort()
    for i in list_vuz:
        summa = 0
        for j in vuz_fin:
            if j[0] == i:
                summa += j[1]
        list_added_fin.append(int(summa))
    for i in range(len(list_vuz)):
        cur.execute(f"SELECT z1 FROM VUZ WHERE codvuz IS {list_vuz[i]}")
        table_data.append((cur.fetchone()[0], list_added_fin[i]))
    table_data.append(("ИТОГО К РАСПРЕДЕЛЕНИЮ", sum(list_added_fin)))

    rows = len(table_data)
    model = QStandardItemModel(rows, 2, finWindow)
    model.setHorizontalHeaderLabels(["ВУЗ", "К начислению"])
    for row_idx, current_tuple in enumerate(table_data):
        for col_idx, value in enumerate(current_tuple):
            # QStandardItem принимает только строки, поэтому приводим value к str()
            item = QStandardItem(str(value))

            # Записываем элемент в ячейку (строка, колонка)
            model.setItem(row_idx, col_idx, item)
    finWindow.report_model = model  # Держим модель до следующего распределения и экспорта.
    finWindow.tableView.setModel(model)
    report_quarter = num_quart
    finWindow.tableView.horizontalHeader().setSectionResizeMode(
        finWindow.tableView.horizontalHeader().ResizeMode.ResizeToContents
    )


def save_report(path, exported_at):
    """Записать PDF показанной таблицы, не обновляя основную базу данных."""
    if report_quarter is None:
        messagebox.showerror("Ошибка экспорта", "Сначала распределите денежные средства")
        return
    try:
        write_table_pdf(finWindow.tableView, report_quarter, path, exported_at)
    except Exception as error:
        messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить PDF:\n{error}")
        return
    messagebox.showinfo("PDF сохранён", f"Файл сохранён:\n{path}")


def export_pdf():
    if report_quarter is None:
        messagebox.showerror("Ошибка экспорта", "Сначала распределите денежные средства")
        return
    exported_at = datetime.now()
    path, _ = QFileDialog.getSaveFileName(
        finWindow, "Сохранить распределение в PDF",
        str(BASE_DIR / report_filename(exported_at)), "PDF-файлы (*.pdf)"
    )
    if not path:  # Пользователь отменил диалог.
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    save_report(path, exported_at)


def write_to_db():
    cur.execute("""
                UPDATE main.ntp_proj
                SET [Факт_фин] = ram.[Факт_фин],
                    [Ф_фин_1] = ram.[Ф_фин_1],
                    [Ф_фин_2] = ram.[Ф_фин_2],
                    [Ф_фин_3] = ram.[Ф_фин_3],
                    [Ф_фин_4] = ram.[Ф_фин_4]
                FROM ram_db.ntp_proj AS ram
                WHERE main.ntp_proj.[НТП] = ram.[НТП]
                    AND main.ntp_proj.[НИР] = ram.[НИР]
                """)
    con.commit()
    exported_at = datetime.now()
    save_report(BASE_DIR / report_filename(exported_at), exported_at)


con = sqlite3.connect(str(BASE_DIR / 'res/data.db'))
cur = con.cursor()

fill_data()

validator = QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$"))
validator2 = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))

finWindow.cancel.clicked.connect(cancel_btn)
finWindow.cancel_2.clicked.connect(cancel_btn)
finWindow.summ_raspred.textChanged.connect(summ_raspred_changed)
finWindow.proc_raspred.textChanged.connect(proc_raspred_changed)
finWindow.raspred.clicked.connect(raspred_fn)
finWindow.export_2.clicked.connect(export_pdf)
finWindow.write_to_db.clicked.connect(write_to_db)

finWindow.summ_raspred.setValidator(validator)
finWindow.quartal_fin.setValidator(validator)
finWindow.proc_raspred.setValidator(validator2)


finWindow.show()
app.exec()