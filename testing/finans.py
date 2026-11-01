import sqlite3
from PyQt6 import uic
from PyQt6.QtWidgets import *
from PyQt6.QtSql import *
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QRegularExpression, QItemSelectionModel, QModelIndex, QItemSelection
from tkinter import messagebox
from PyQt6.QtGui import QRegularExpressionValidator, QStandardItemModel

app = QApplication([])
finWindow = uic.loadUi("res/finans.ui")
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

def raspred_fn():
    if finWindow.summ_raspred.text() == "":
        messagebox.showerror("Ошибка", "Не задана сумма распределения")
        return -1
    if finWindow.quartal_fin.text() == "":
        messagebox.showerror("Ошибка", "Не задан квартал финансирования")
        return -1
    if not (1 <= int(finWindow.quartal_fin.text()) <= 4):
        messagebox.showerror("Ошибка", "Задан некорректный квартал финансирования")
        return -1

    cur.execute("ATTACH DATABASE ':memory:' AS ram_db")
    cur.execute("CREATE TABLE ram_db.ntp_proj AS SELECT * FROM main.ntp_proj")

con = sqlite3.connect('res/data.db')
cur = con.cursor()

fill_data()

validator = QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$"))
validator2 = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))

finWindow.cancel.clicked.connect(cancel_btn)
finWindow.cancel_2.clicked.connect(cancel_btn)
finWindow.summ_raspred.textChanged.connect(summ_raspred_changed)
finWindow.proc_raspred.textChanged.connect(proc_raspred_changed)
finWindow.raspred.clicked.connect(raspred_fn)

finWindow.summ_raspred.setValidator(validator)
finWindow.quartal_fin.setValidator(validator)
finWindow.proc_raspred.setValidator(validator2)


finWindow.show()
app.exec()