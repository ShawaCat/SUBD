################################
#Инклюды
################################

import os
import sqlite3

import sys
from PyQt6 import uic
from PyQt6.QtWidgets import *
from PyQt6.QtSql import *
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QRegularExpression, QItemSelectionModel, QModelIndex, QItemSelection
from tkinter import messagebox
from PyQt6.QtGui import QRegularExpressionValidator, QStandardItemModel
import pyqt6_multiselect_combobox

from pdf_export import write_pdf
from finans import FinancingWindow

sys.modules["pyqt6_multiselect-combobox"] = pyqt6_multiselect_combobox

################################
#Функции
################################

def connect_db(db_file):
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(db_file)
    if not db.open():
        form.label.setText(f"ОШИБКА: сбой подключения к {db_file}!")
        return False
    return db

def open_tab_1():
    global model, table_num, proxy_model, filter_query
    model = QSqlQueryModel()
    if len(filter_query) <= 2:
        model.setQuery("SELECT * FROM ntp_proj")
    else:
        model.setQuery(filter_query)
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    form.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    form.tableView.setSortingEnabled(True)
    form.tableView.setModel(proxy_model)
    form.label.setText("Отображена таблица проектов/НИР")
    table_num = 1

    form.Sort_btn.setVisible(True)
    form.Add_btn.setVisible(True)
    form.Edit_btn.setVisible(True)
    form.Del_btn.setVisible(True)
    form.Filter.setVisible(True)

    form.Sort_btn.setEnabled(True)
    form.Add_btn.setEnabled(True)
    form.Filter.setEnabled(True)

def open_tab_2():
    global model, table_num
    model = QSqlQueryModel()
    model.setQuery("SELECT * FROM ntp_prog")
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    form.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    form.tableView.setSortingEnabled(True)
    form.tableView.setModel(proxy_model)
    form.label.setText("Отображена таблица НТП")
    table_num = 2

    form.Sort_btn.setVisible(False)
    form.Add_btn.setVisible(False)
    form.Edit_btn.setVisible(False)
    form.Del_btn.setVisible(False)
    form.Filter.setVisible(False)

    form.Sort_btn.setEnabled(False)
    form.Add_btn.setEnabled(False)
    form.Edit_btn.setEnabled(False)
    form.Del_btn.setEnabled(False)
    form.Filter.setEnabled(False)

def open_tab_3():
    global model, table_num
    model = QSqlQueryModel()
    model.setQuery("SELECT * FROM VUZ")
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    form.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    form.tableView.setSortingEnabled(True)
    form.tableView.setModel(proxy_model)
    form.label.setText("Отображена таблица ВУЗ")
    table_num = 3

    form.Sort_btn.setVisible(False)
    form.Add_btn.setVisible(False)
    form.Edit_btn.setVisible(False)
    form.Del_btn.setVisible(False)
    form.Filter.setVisible(False)

    form.Sort_btn.setEnabled(False)
    form.Add_btn.setEnabled(False)
    form.Edit_btn.setEnabled(False)
    form.Del_btn.setEnabled(False)
    form.Filter.setEnabled(False)

def view_help():
    os.startfile("res\\help.txt")

def exit_btn():
    sys.exit(0)

def sort_table():
    global model, proxy_model, filter_query
    proxy_model.sort(-1, Qt.SortOrder.AscendingOrder)
    if len(filter_query) != 0:
        model.setQuery(f"{filter_query} ORDER BY [НТП] ASC, [НИР] ASC")
    else:
        model.setQuery("SELECT * FROM ntp_proj ORDER BY [НТП] ASC, [НИР] ASC")

def rebuild_db():
    global model

    connection_name = QSqlDatabase.database().connectionName()
    QSqlDatabase.database().close()
    QSqlDatabase.removeDatabase(connection_name)


    con = sqlite3.connect('res/data.db')
    cur = con.cursor()

    # перенос аббреавиатуры ВУЗА из таблицы ВУЗ по коду ВУЗА
    cur.execute("UPDATE ntp_proj SET [Исп_орг] = VUZ.z2 FROM VUZ WHERE ntp_proj.[ВУЗ] = VUZ.codvuz")

    # подсчет числа НИР в каждом НТП
    cur.execute("SELECT [НТП], COUNT(*) FROM ntp_proj GROUP BY [НТП]")
    result_wrong = cur.fetchall()
    result = []
    for i in result_wrong:
        result.append((i[1],i[0]))
    Q1 = "UPDATE ntp_prog SET [Кол_п] = ? WHERE ntp_prog.[код_НТП] = ?"
    cur.executemany(Q1, result)

    # подсчет финансирования (планового) в каждом НТП по всем НИР
    pl_fin_ntp = []
    cur.execute("SELECT DISTINCT [НТП] FROM ntp_proj GROUP BY [НТП]")
    ntp = cur.fetchall()
    for x in ntp:
       sum_fin = 0
       Q2 = "SELECT [План_фин] FROM ntp_proj WHERE [НТП] = ?"
       cur.execute(Q2, x)
       list_fin = cur.fetchall()
       for y in list_fin:
           sum_fin = sum_fin + y[0]
       pl_fin_ntp.append((sum_fin, x[0]))
    Q3 = "UPDATE ntp_prog SET [План_фин] = ? WHERE [код_НТП] = ?"
    cur.executemany(Q3, pl_fin_ntp)

    # делим план финансирование в ntp_proj по кварталам
    cur.execute("SELECT [План_фин], [НТП], [НИР]  FROM ntp_proj")
    pl_f_nir = cur.fetchall()
    for f in pl_f_nir:
        a = f[0]//4
        b = f[0]-3*a
        pl_f_nir_1234 = (a,a,a,b,f[1],f[2])
        Q4 = "UPDATE ntp_proj SET [П_фин_1] = ?, [П_фин_2] = ?, [П_фин_3] = ?, [П_фин_4] = ? WHERE [НТП] = ? AND [НИР] = ?"
        cur.execute(Q4, pl_f_nir_1234)

    # делим план финансирование в ntp_prog по кварталам
    cur.execute("SELECT [План_фин], [код_НТП] FROM ntp_prog")
    pl_f_ntp = cur.fetchall()
    for p in pl_f_ntp:
        c = p[0]//4
        d = p[0]-3*c
        pl_f_ntp_1234 = (c,c,c,d,p[1])
        Q5 = "UPDATE ntp_prog SET [П_фин_1] = ?, [П_фин_2] = ?, [П_фин_3] = ?, [П_фин_4] = ? WHERE [код_НТП] = ?"
        cur.execute(Q5, pl_f_ntp_1234)

    # Фактические суммы и кварталы НИР не пересчитываем: они могут быть
    # распределены вручную. В ntp_prog суммируем сохранённые значения НИР.
    fact_fields = ("Факт_фин", "Ф_фин_1", "Ф_фин_2", "Ф_фин_3", "Ф_фин_4")
    assignments = ", ".join(
        f"[{field}] = COALESCE((SELECT SUM(p.[{field}]) "
        f"FROM ntp_proj AS p WHERE p.[НТП] = ntp_prog.[код_НТП]), 0)"
        for field in fact_fields
    )
    cur.execute(f"UPDATE ntp_prog SET {assignments}")

    con.commit()
    cur.close()
    con.close()

    connect_db(db_file)
    if table_num == 1:
        open_tab_1()
    elif table_num == 2:
        open_tab_2()
    elif table_num == 3:
        open_tab_3()

    #model.select()

def take_record_num(logical_index):
    global form, table_num, key_selected_record, proxy_model, model
    if table_num == 1:
        form.Edit_btn.setEnabled(True)
        form.Del_btn.setEnabled(True)
        proxy_index_col0 = proxy_model.index(logical_index, 0)
        proxy_index_col1 = proxy_model.index(logical_index, 1)
        source_index_col0 = proxy_model.mapToSource(proxy_index_col0)
        source_index_col1 = proxy_model.mapToSource(proxy_index_col1)
        data_col1 = model.data(source_index_col0)
        data_col2 = model.data(source_index_col1)
        # print("Изначальный номер строки в БД:", source_index_col0.row()+1)

        key_selected_record = [data_col1, data_col2]
        # print("Выбранные ключи записи:", key_selected_record)

def off_btns():
    form.Edit_btn.setEnabled(False)
    form.Del_btn.setEnabled(False)

def del_record():
    global key_selected_record, model, form
    form.tableView.setEnabled(False)
    form.Sort_btn.setEnabled(False)
    form.Add_btn.setEnabled(False)
    form.Edit_btn.setEnabled(False)
    form.Del_btn.setEnabled(False)
    form.Filter.setEnabled(False)
    form.menubar.setEnabled(False)
    result = messagebox.askyesno("Подтверждение удаления записи", f"Вы действительно хотите удалить запись\nс ключом {key_selected_record[0]}, {key_selected_record[1]}?")
    if result == 1:
        connection_name = QSqlDatabase.database().connectionName()
        QSqlDatabase.database().close()
        QSqlDatabase.removeDatabase(connection_name)
        con = sqlite3.connect('res/data.db')
        cur = con.cursor()
        cur.execute("DELETE FROM ntp_proj WHERE [НТП] = ? AND [НИР] = ?", (key_selected_record[0], key_selected_record[1]))
        con.commit()
        cur.close()
        con.close()

        connect_db(db_file)
        if table_num == 1:
            open_tab_1()
        elif table_num == 2:
            open_tab_2()
        elif table_num == 3:
            open_tab_3()
        rebuild_db()
        messagebox.showinfo("Удаление", "Удаление прошло успешно")
    form.tableView.setEnabled(True)
    form.Sort_btn.setEnabled(True)
    form.Add_btn.setEnabled(True)
    form.Filter.setEnabled(True)
    form.menubar.setEnabled(True)

    off_btns()
    sort_table()

def select_row_by_values(table_view, val1, val2):
    current_model = table_view.model()
    if not current_model:
        return False
    for row in range(current_model.rowCount()):
        idx_col0 = current_model.index(row, 0)
        idx_col1 = current_model.index(row, 1)
        data0 = current_model.data(idx_col0)
        data1 = current_model.data(idx_col1)
        if str(data0) == str(val1) and str(data1) == str(val2):
            selection_model = table_view.selectionModel()
            selection_model.clearSelection()
            last_col = current_model.columnCount() - 1
            idx_last = current_model.index(row, last_col)

            selection = QItemSelection(idx_col0, idx_last)
            selection_model.select(selection,
                                   QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
            table_view.scrollTo(idx_col0)
            table_view.setCurrentIndex(idx_col0)

            return True  # Строка найдена и выделена

    return False  # Строка не найдена

def add_record():

    global addForm, addWindow, model
    connection_name = QSqlDatabase.database().connectionName()
    QSqlDatabase.database().close()
    QSqlDatabase.removeDatabase(connection_name)
    con = sqlite3.connect('res/data.db')
    cur = con.cursor()

    current_index = 0
    current_vuz = []
    current_ntp = 0
    temp_vuz = []

    def index_changed(index):
        nonlocal current_index, KEY, number_name_NTP, current_ntp
        current_index = index
        current_ntp = number_name_NTP[current_index][0]
        addForm.edit_nir.setText(str(max(KEY[current_ntp], default=0) + 1))

    def vuz_changed(index):
        a = 1

    def addForm_check_and_save():
        nonlocal current_ntp, current_vuz, KEY, VUZ_CODVUZ
        global form

        GRNTI_1 = ''
        GRNTI_2 = ''
        TypeDict = {"Фундаментальное исследование":"Ф", "Прикладное исследование":"П", "Экспериментальная разработка":"Р"}
        errors = []
        error_msg = ""
        ntp = current_ntp
        nir = addForm.edit_nir.text()
        if addForm.combo_program.currentText() == "":
            messagebox.showerror("Ошибка добавления", "Не выбрана НТП")
            return 0
        if addForm.combo_type_2.currentText() == "":
            messagebox.showerror("Ошибка добавления", "Не выбран тип НИР")
            return 0
        if addForm.combo_vuz.currentText() == "":
            messagebox.showerror("Ошибка добавления", "Не выбран ВУЗ исполнитель")
            return 0
        current_vuz = next((item for item in VUZ_CODVUZ if item[1] == addForm.combo_vuz.currentText()), None)
        codvuz = current_vuz[0]
        namevuz = current_vuz[1]
        ruk = addForm.edit_ruk.text()
        doljn_ruk = addForm.edit_doljn_ruk.text()
        temp_grnti_1 = [addForm.GRNTI_1_1.text(), addForm.GRNTI_1_2.text(), addForm.GRNTI_1_3.text()]
        temp_grnti_2 = [addForm.GRNTI_2_1.text(), addForm.GRNTI_2_2.text(), addForm.GRNTI_2_3.text()]
        for i in range(len(temp_grnti_1)):
            if (i == 2): GRNTI_1 = GRNTI_1 + temp_grnti_1[i]
            else: GRNTI_1 = GRNTI_1 + temp_grnti_1[i] + "."
        for i in range(len(temp_grnti_2)):
            if (i == 2): GRNTI_2 = GRNTI_2 + temp_grnti_2[i]
            else: GRNTI_2 = GRNTI_2 + temp_grnti_2[i] + "."
        GRNTI = GRNTI_1
        if len(GRNTI_2) == 8:
            GRNTI = GRNTI + "," + GRNTI_2

        plan_fin = addForm.edit_fin.text()

        name_NIR = addForm.edit_title.toPlainText()

        Sr_N = addForm.spin_start.value()
        Sr_K = addForm.spin_end.value()

        if int(nir) in KEY[ntp]:
            errors.append("Этот номер НИР уже существует")
        if nir == "":
            errors.append("Не задан номер НИР")
        if len(ruk) == 0:
            errors.append("Не задано ФИО руководителя")
        if len(doljn_ruk) == 0:
            errors.append("Не задана должность руководителя")
        if len(GRNTI_1) != 8:
            errors.append("Ошибка в заполнении ГРНТИ 1")
        if not((len(GRNTI_2) == 8) or (len(GRNTI_2) == 2)):
            errors.append("Ошибка в заполнении ГРНТИ 2")
        if len(name_NIR) == 0:
            errors.append("Не задано название НИР")
        if Sr_N > Sr_K:
            errors.append("Ошибка в сроках выполнения НИР")
        if plan_fin != "":
            if (plan_fin[0] == "0") and (len(plan_fin) != 1):
                errors.append("Ошибка в заполнении планового финансирования")
            if (plan_fin[0] == "0") and (len(plan_fin) == 1):
                errors.append("Плановое финансирование не может быть нулевым")
        else:
            errors.append("Ошибка в заполнении планового финансирования")

        Type = TypeDict.get(addForm.combo_type_2.currentText())

        if len(errors) == 0:
            # При создании НИР фактическое финансирование ещё не выделено.
            new_str = (ntp, int(nir), int(codvuz), str(namevuz), str(ruk),
                       str(doljn_ruk), GRNTI, Type, int(plan_fin),
                       0, 0, 0, 0, 0, str(name_NIR), int(Sr_N), int(Sr_K))
            Q8 = """INSERT INTO ntp_proj
                ([НТП], [НИР], [ВУЗ], [Исп_орг], [Руководитель],
                 [Должн_руководитель], [ГРНТИ], [Хар], [План_фин],
                 [Факт_фин], [Ф_фин_1], [Ф_фин_2], [Ф_фин_3], [Ф_фин_4],
                 [Наименование_НИР], [Ср_Н], [Ср_К])
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            cur.execute(Q8, new_str)
            con.commit()
            cur.close()
            con.close()

            rebuild_db()
            sort_table()
            success = select_row_by_values(form.tableView, ntp, int(nir))
            off_btns()
            messagebox.showinfo("Добавление", "Добавление записи прошло успешно")
            addWindow.close()
        else:
            for i in range(len(errors)):
                error_msg = error_msg + errors[i] + "\n"
            messagebox.showerror("Ошибка добавления", f"Обнаружены некорректные данные:\n{error_msg}")

    def addForm_cancel():
        cur.close()
        con.close()
        connect_db(db_file)
        open_tab_1()
        addWindow.close()

    Add_Form, Add_Window = uic.loadUiType("res/add_new.ui")
    addWindow = Add_Window()
    flags = addWindow.windowFlags()
    addWindow.setWindowFlags(
        flags &
        ~Qt.WindowType.WindowCloseButtonHint &
        ~Qt.WindowType.WindowMinimizeButtonHint &
        ~Qt.WindowType.WindowMaximizeButtonHint
    )
    addForm = Add_Form()
    addForm.setupUi(addWindow)



    # Список кортежей (код_НТП + имя_НТП) для пользователя в момент заполнения формы "добавить запись"
    cur.execute("SELECT [код_НТП], [Название_НТП] FROM ntp_prog")
    number_name_NTP = cur.fetchall()

    # Собираем словарь из кода НТП + кода НИР внутри НТП
    # здесь внутри словаря МНОЖЕСТВО, то есть вид такой {404: {1, 2, 3, 4}}
    cur.execute("SELECT [код_НТП] FROM ntp_prog")
    code_NTP = cur.fetchall()
    KEY = {}
    for c in code_NTP:
        KEY[c[0]] = set()
        Q6 = "SELECT [НИР] FROM ntp_proj WHERE [НТП] = ?"
        cur.execute(Q6, c)
        nirs = cur.fetchall()
        for n in nirs:
            KEY[c[0]].add(n[0])

    # Пара Код_ВУЗ + ВУЗ
    cur.execute("SELECT codvuz, z2 FROM VUZ")
    VUZ_CODVUZ = cur.fetchall()

    # Заполняем комбобокс номерами НТП
    for i in number_name_NTP:
        addForm.combo_program.addItem(str(i[0]) + " - " + i[1])

    for i in VUZ_CODVUZ:
        temp_vuz.append(i[1])

    temp_vuz = sorted(temp_vuz)
    for i in temp_vuz:
        addForm.combo_vuz.addItem(i)

    vuz_changed(0)
    index_changed(0)

    addForm.combo_program.setCurrentIndex(-1)
    addForm.combo_vuz.setCurrentIndex(-1)
    addForm.combo_type_2.setCurrentIndex(-1)
    addForm.edit_nir.setText("")

    regex = QRegularExpressionValidator(QRegularExpression(r"^\d{1,2}$"))
    regex_2 = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))
    addForm.GRNTI_1_1.setValidator(regex)
    addForm.GRNTI_1_2.setValidator(regex)
    addForm.GRNTI_1_3.setValidator(regex)
    addForm.GRNTI_2_1.setValidator(regex)
    addForm.GRNTI_2_2.setValidator(regex)
    addForm.GRNTI_2_3.setValidator(regex)
    addForm.edit_fin.setValidator(regex_2)
    addForm.edit_nir.setValidator(regex_2)



    addForm.combo_program.currentIndexChanged.connect(index_changed)
    addForm.combo_vuz.currentIndexChanged.connect(vuz_changed)
    addForm.btn_save.clicked.connect(addForm_check_and_save)
    addForm.btn_cancel.clicked.connect(addForm_cancel)

    addWindow.show()

def edit_record():

    def editForm_cancel():
        cur.close()
        con.close()
        connect_db(db_file)
        open_tab_1()
        editWindow.close()

    def editForm_check_and_save():
        nonlocal current_ntp, current_vuz, KEY, current_data, NTP_NIR

        GRNTI_1 = ''
        GRNTI_2 = ''
        TypeDict = {"Фундаментальное исследование":"Ф", "Прикладное исследование":"П", "Экспериментальная разработка":"Р"}
        errors = []
        error_msg = ""
        ntp = number_name_NTP[editForm.combo_program.currentIndex()][0]
        nir = editForm.edit_nir.text()
        current_vuz = next((item for item in VUZ_CODVUZ if item[1] == editForm.combo_vuz.currentText()), None)
        codvuz = current_vuz[0]
        namevuz = current_vuz[1]
        ruk = editForm.edit_ruk.text()
        doljn_ruk = editForm.edit_doljn_ruk.text()
        temp_grnti_1 = [editForm.GRNTI_1_1.text(), editForm.GRNTI_1_2.text(), editForm.GRNTI_1_3.text()]
        temp_grnti_2 = [editForm.GRNTI_2_1.text(), editForm.GRNTI_2_2.text(), editForm.GRNTI_2_3.text()]
        for i in range(len(temp_grnti_1)):
            if (i == 2): GRNTI_1 = GRNTI_1 + temp_grnti_1[i]
            else: GRNTI_1 = GRNTI_1 + temp_grnti_1[i] + "."
        for i in range(len(temp_grnti_2)):
            if (i == 2): GRNTI_2 = GRNTI_2 + temp_grnti_2[i]
            else: GRNTI_2 = GRNTI_2 + temp_grnti_2[i] + "."
        GRNTI = GRNTI_1
        if len(GRNTI_2) == 8:
            GRNTI = GRNTI + "," + GRNTI_2

        plan_fin = editForm.edit_fin.text()

        name_NIR = editForm.edit_title.toPlainText()

        Sr_N = editForm.spin_start.value()
        Sr_K = editForm.spin_end.value()

        if (int(nir) in KEY[ntp]) and ((int(nir) != current_data[1]) or (int(ntp)) != current_data[0]):
            errors.append("Этот номер НИР уже существует")
        if len(nir) == 0:
            errors.append("Не задан номер НИР")
        if len(ruk) == 0:
            errors.append("Не задан руководитель")
        if len(doljn_ruk) == 0:
            errors.append("Не задана должность руководителя")
        if len(GRNTI_1) != 8:
            errors.append("Ошибка в заполнении ГРНТИ 1")
        if not((len(GRNTI_2) == 8) or (len(GRNTI_2) == 2)):
            errors.append("Ошибка в заполнении ГРНТИ 2")
        if len(name_NIR) == 0:
            errors.append("Задано пустое название НИР")
        if Sr_N > Sr_K:
            errors.append("Ошибка в сроках выполнения НИР")
        if plan_fin != "":
            if (plan_fin[0] == "0") and (len(plan_fin) != 1):
                errors.append("Ошибка в заполнении планового финансирования")
            if (plan_fin[0] == "0") and (len(plan_fin) == 1):
                errors.append("Плановое финансирование не может быть нулевым")
        else:
            errors.append("Ошибка в заполнении планового финансирования")

        Type = TypeDict.get(editForm.combo_type_2.currentText())

        if len(errors) == 0:
            # Запрос ИЗМЕНЕНИЯ записи
            new_str = (int(ntp), int(nir), int(codvuz), str(namevuz), str(ruk), str(doljn_ruk), GRNTI, Type, int(plan_fin),
                       str(name_NIR), int(Sr_N), int(Sr_K))
            # Редактирование реквизитов НИР не должно обнулять уже выделенные средства.
            Q8 = """UPDATE ntp_proj SET [НТП] = ?, [НИР] = ?, [ВУЗ] = ?, [Исп_орг] = ?, [Руководитель] = ?, 
                [Должн_руководитель] = ?, [ГРНТИ] = ?, [Хар] = ?, [План_фин] = ?,
                [Наименование_НИР] = ?, [Ср_Н] = ?, [Ср_К] = ?
                    WHERE [НТП] = ? AND [НИР] = ?"""
            query_params = new_str + NTP_NIR

            cur.execute(Q8, query_params)
            con.commit()
            cur.close()
            con.close()
            messagebox.showinfo("Изменение", "Изменение записи прошло успешно")

            off_btns()
            rebuild_db()
            sort_table()
            success = select_row_by_values(form.tableView, int(ntp), int(nir))
            editWindow.close()
        else:
            for i in range(len(errors)):
                error_msg = error_msg + errors[i] + "\n"
            messagebox.showerror("Ошибка изменения", f"Обнаружены некорректные данные:\n{error_msg}")

    global editForm, editWindow, model, key_selected_record
    connection_name = QSqlDatabase.database().connectionName()
    QSqlDatabase.database().close()
    QSqlDatabase.removeDatabase(connection_name)
    con = sqlite3.connect('res/data.db')
    cur = con.cursor()

    current_index = 0
    current_vuz = []
    current_ntp = 0
    key_rec = key_selected_record
    current_data = []
    temp_vuz = []


    Edit_Form, Edit_Window = uic.loadUiType("res/edit.ui")
    editWindow = Edit_Window()
    flags = editWindow.windowFlags()
    editWindow.setWindowFlags(
        flags &
        ~Qt.WindowType.WindowCloseButtonHint &
        ~Qt.WindowType.WindowMinimizeButtonHint &
        ~Qt.WindowType.WindowMaximizeButtonHint
    )
    editForm = Edit_Form()
    editForm.setupUi(editWindow)

    # Выводим строку по ключу
    NTP_NIR = (key_rec[0], key_rec[1])
    Q7 = "SELECT * FROM ntp_proj WHERE [НТП] = ? AND [НИР] = ?"
    cur.execute(Q7, NTP_NIR)
    current_data = list(cur.fetchone())

    # Список кортежей (код_НТП + имя_НТП) для пользователя в момент заполнения формы "добавить запись"
    cur.execute("SELECT [код_НТП], [Название_НТП] FROM ntp_prog")
    number_name_NTP = cur.fetchall()

    # Собираем словарь из кода НТП + кода НИР внутри НТП
    # здесь внутри словаря МНОЖЕСТВО, то есть вид такой {404: {1, 2, 3, 4}}
    cur.execute("SELECT [код_НТП] FROM ntp_prog")
    code_NTP = cur.fetchall()
    KEY = {}
    for c in code_NTP:
        KEY[c[0]] = set()
        Q6 = "SELECT [НИР] FROM ntp_proj WHERE [НТП] = ?"
        cur.execute(Q6, c)
        nirs = cur.fetchall()
        for n in nirs:
            KEY[c[0]].add(n[0])

    # Пара Код_ВУЗ + ВУЗ
    cur.execute("SELECT codvuz, z2 FROM VUZ")
    VUZ_CODVUZ = cur.fetchall()

    # Заполняем комбобокс номерами НТП и вузов
    for i in number_name_NTP:
        editForm.combo_program.addItem(str(i[0]) + " - " + i[1])

    for i in VUZ_CODVUZ:
        temp_vuz.append(i[1])

    temp_vuz = sorted(temp_vuz)
    for i in temp_vuz:
        editForm.combo_vuz.addItem(i)

    index_ntp = next((i for i, tpl in enumerate(number_name_NTP) if tpl[0] == current_data[0]), None)
    # index_vuz = next((i for i, tpl in enumerate(VUZ_CODVUZ) if tpl[0] == current_data[2]), None)
    index_vuz = next((item for item in VUZ_CODVUZ if item[0] == current_data[2]), None)[1]
    editForm.combo_program.setCurrentIndex(index_ntp)
    editForm.edit_nir.setText(str(current_data[1]))
    editForm.combo_vuz.setCurrentIndex(temp_vuz.index(index_vuz))
    # editForm.combo_vuz.setCurrentIndex(index_vuz)
    editForm.edit_ruk.setText(str(current_data[4]))
    editForm.edit_doljn_ruk.setText(str(current_data[5]))

    temp_grnti = current_data[6].split(",")
    temp_grnti_1 = temp_grnti[0].split(".")
    editForm.GRNTI_1_1.setText(temp_grnti_1[0])
    if len(temp_grnti_1) > 1: editForm.GRNTI_1_2.setText(temp_grnti_1[1])
    if len(temp_grnti_1) == 3: editForm.GRNTI_1_3.setText(temp_grnti_1[2])

    if len(temp_grnti) == 2:
        temp_grnti_2 = temp_grnti[1].split(".")
        editForm.GRNTI_2_1.setText(temp_grnti_2[0])
        if len(temp_grnti_2) > 1: editForm.GRNTI_2_2.setText(temp_grnti_2[1])
        if len(temp_grnti_2) == 3: editForm.GRNTI_2_3.setText(temp_grnti_2[2])

    if current_data[7] == "П": editForm.combo_type_2.setCurrentIndex(1)
    elif current_data[7] == "Р": editForm.combo_type_2.setCurrentIndex(2)
    elif current_data[7] == "Ф": editForm.combo_type_2.setCurrentIndex(0)

    editForm.edit_fin.setText(str(current_data[8]))
    editForm.edit_title.setText(current_data[18])
    editForm.spin_start.setValue(int(current_data[19]))
    editForm.spin_end.setValue(int(current_data[20]))

    regex = QRegularExpressionValidator(QRegularExpression(r"^\d{1,2}$"))
    regex_2 = QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$"))
    editForm.GRNTI_1_1.setValidator(regex)
    editForm.GRNTI_1_2.setValidator(regex)
    editForm.GRNTI_1_3.setValidator(regex)
    editForm.GRNTI_2_1.setValidator(regex)
    editForm.GRNTI_2_2.setValidator(regex)
    editForm.GRNTI_2_3.setValidator(regex)
    editForm.edit_fin.setValidator(regex_2)
    editForm.edit_nir.setValidator(regex_2)

    editForm.btn_cancel.clicked.connect(editForm_cancel)
    editForm.btn_save.clicked.connect(editForm_check_and_save)

    editWindow.show()

def open_filter_window():
    global filterWindow, filter_query, key_selected_record, ntp_combo_selected, okrug_combo_selected
    global region_combo_selected, city_combo_selected, vuz_combo_selected
    global filter_combo_state, filter_first_changed_combo, applied_geo_filters

    connection_name = QSqlDatabase.database().connectionName()
    QSqlDatabase.database().close()
    QSqlDatabase.removeDatabase(connection_name)

    selected_items = []

    filterWindow = uic.loadUi("res/filter.ui")
    flags = filterWindow.windowFlags()
    filterWindow.setWindowFlags(
        flags &
        ~Qt.WindowType.WindowCloseButtonHint &
        ~Qt.WindowType.WindowMinimizeButtonHint &
        ~Qt.WindowType.WindowMaximizeButtonHint
    )

    con = sqlite3.connect("res/data.db")
    cur = con.cursor()

    # Настройка разделителя
    for name in ("ntp", "okrug", "region", "city", "vuz"):
        getattr(filterWindow, f"{name}_combo").setDisplayDelimiter(", ")

    # НТП
    cur.execute("SELECT [код_НТП], [Название_НТП] FROM ntp_prog")

    for code, name in cur.fetchall():
        filterWindow.ntp_combo.addItem(f"{code} - {name}")

    # Полный список НТП нужен, чтобы кнопка «Снять» могла восстановить
    # список и одновременно убрать все его отметки.
    ntp_all_items = [
        filterWindow.ntp_combo.itemText(i)
        for i in range(filterWindow.ntp_combo.count())
    ]

    # Исходные данные вузов
    cur.execute("SELECT region, oblname, city, z2 FROM VUZ")
    VUZ_CODVUZ = cur.fetchall()
    rows = [tuple(r) for r in VUZ_CODVUZ]

    FIELDS = {
        "okrug": 0,
        "region": 1,
        "city": 2,
        "vuz": 3,
    }

    combos = {
        name: getattr(filterWindow, f"{name}_combo")
        for name in FIELDS
    }

    # Полные списки значений
    all_items = {
        name: sorted({
            row[index]
            for row in rows
            if row[index] is not None
        })
        for name, index in FIELDS.items()
    }

    # Восстанавливаем реальный выбор пользователя после повторного открытия окна.
    saved_selection = {
        name: applied_geo_filters.get(name, []) for name in FIELDS
    }
    selected = {
        name: set(values or [])
        for name, values in saved_selection.items()
    }

    # Ведущий ComboBox и состояния списков хранятся вне функции,
    # поэтому не теряются при закрытии и повторном открытии окна.
    first_changed_combo = filter_first_changed_combo

    def set_fn():
        global filter_query
        global ntp_combo_selected, okrug_combo_selected, region_combo_selected, city_combo_selected, vuz_combo_selected
        global applied_geo_filters
        nonlocal VUZ_CODVUZ
        selected_items = []
        selected_ntp = []

        sort_by_geo = 0
        sort_by_ntp = 0

        selected_items.append(filterWindow.okrug_combo.currentData())
        selected_items.append(filterWindow.region_combo.currentData())
        selected_items.append(filterWindow.city_combo.currentData())
        selected_items.append(filterWindow.vuz_combo.currentData())
        selected_ntp.extend(filterWindow.ntp_combo.currentData())
        # Только выбор пользователя: связанные значения могут быть отмечены визуально.
        applied_geo_filters = {name: sorted(selected[name]) for name in FIELDS}
        filter_query = ""
        ntp_combo_selected = filterWindow.ntp_combo.currentData()
        okrug_combo_selected = filterWindow.okrug_combo.currentData()
        region_combo_selected = filterWindow.region_combo.currentData()
        city_combo_selected = filterWindow.city_combo.currentData()
        vuz_combo_selected = filterWindow.vuz_combo.currentData()

        for i in range(3, -1, -1):
            if len(selected_items[i]) != 0:
                print(selected_items[i])
                filt_query_temp = [x[3] for x in VUZ_CODVUZ if x[i] in selected_items[i]]
                quoted_items = [f"'{item}'" for item in filt_query_temp]
                placeholders_geo = ", ".join(quoted_items)
                sort_by_geo = 1
                break

        if len(selected_ntp) != 0:
            sort_by_ntp = 1
            for i in range(len(selected_ntp)):
                selected_ntp[i] = int(selected_ntp[i][:3])
            ntp_ids = ", ".join(map(str, selected_ntp))

        if sort_by_geo == 1 and sort_by_ntp == 0:
            filter_query = f"SELECT * FROM ntp_proj WHERE [Исп_орг] IN ({placeholders_geo})"
        elif sort_by_ntp == 1 and sort_by_geo == 0:
            filter_query = f"SELECT * FROM ntp_proj WHERE [НТП] IN ({ntp_ids})"
        elif sort_by_geo == 1 and sort_by_ntp == 1:
            filter_query = f"SELECT * FROM ntp_proj WHERE [НТП] IN ({ntp_ids}) AND [Исп_орг] IN ({placeholders_geo})"

        cur.close()
        con.close()

        connect_db(db_file)
        open_tab_1()
        rebuild_db()
        sort_table()
        filterWindow.close()

    def cancel_fn():
        cur.close()
        con.close()

        connect_db(db_file)
        open_tab_1()
        filterWindow.close()

    def clear_fn():
        global filter_query
        global ntp_combo_selected, okrug_combo_selected, region_combo_selected, city_combo_selected, vuz_combo_selected
        global applied_geo_filters

        print("Все выделения сброшены.")

        # Сбрасываем сохранённые выделения и разрешаем автообновление заново.
        nonlocal first_changed_combo
        global filter_combo_state, filter_first_changed_combo
        first_changed_combo = None
        filter_first_changed_combo = None
        filter_combo_state = {}
        for name in FIELDS:
            selected[name].clear()

        # Снимаем отметки во всех географических ComboBox и возвращаем
        # полный список элементов без выделения.
        for name, combo in combos.items():
            combo.blockSignals(True)
            try:
                combo.clear()
                combo.addItems(all_items[name])
                combo.setCurrentText("Все")
            finally:
                combo.blockSignals(False)

        # НТП — отдельный ComboBox, его тоже нужно очистить и восстановить.
        ntp_combo = filterWindow.ntp_combo
        ntp_combo.blockSignals(True)
        try:
            ntp_combo.clear()
            ntp_combo.addItems(ntp_all_items)
            ntp_combo.setCurrentText("Все")
        finally:
            ntp_combo.blockSignals(False)

        filter_query = ""
        applied_geo_filters = {}

        ntp_combo_selected = []
        okrug_combo_selected = []
        region_combo_selected = []
        city_combo_selected = []
        vuz_combo_selected = []

        cur.close()
        con.close()

        connect_db(db_file)
        open_tab_1()
        rebuild_db()
        sort_table()
        filterWindow.close()

    def row_matches(row, filters, excluded=None):
        """Проверяет соответствие записи выбранным фильтрам."""
        for name, index in FIELDS.items():
            if name == excluded:
                continue

            values = filters[name]
            if values and row[index] not in values:
                return False

        return True

    def set_combo_items(name, items, visual_chosen):
        """Обновляет список и сохраняет его состояние для следующего открытия."""
        global filter_combo_state
        combo = combos[name]
        items = sorted(set(items))
        visual_chosen = set(visual_chosen) & set(items)

        # Запоминаем и состав списка, и только визуальное выделение.
        # Визуальное выделение не добавляется в selected.
        # Сохраняем и автоматическое визуальное выделение вышестоящих
        # списков, и реальные выбранные пользователем значения (в том числе
        # в нижестоящих списках). Эти два типа выбора остаются раздельными.
        filter_combo_state[name] = {
            "items": list(items),
            "visual_chosen": sorted(visual_chosen),
            "user_selected": sorted(selected[name]),
        }

        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(items)

            # Это только отображение выделения в ComboBox.
            # Реальные фильтры хранятся отдельно в selected.
            display_text = ", ".join(
                item for item in items if item in visual_chosen
            )
            combo.setCurrentText(display_text if display_text else "Все")
        finally:
            combo.blockSignals(False)

    def update_combos(changed_name):
        order = ["okrug", "region", "city", "vuz"]
        changed_index = order.index(changed_name)

        # Реальный выбор пользователя. Визуальные выделения сюда не попадают.
        user_selection = {
            name: set(values)
            for name, values in selected.items()
        }

        # Для определения связанных вышестоящих значений убираем ограничения
        # вышестоящих списков, но сохраняем выбор изменённого/нижестоящих.
        filters = {
            name: set(values)
            for name, values in user_selection.items()
        }
        for name in order[:changed_index]:
            filters[name] = set()

        matching_rows = [
            row for row in rows
            if row_matches(row, filters)
        ]

        # Обновляем доступные элементы. Вышестоящие значения выделяем
        # визуально, но selected (реальные фильтры) не изменяем.
        for name in order:
            index = FIELDS[name]
            name_index = order.index(name)

            if name == changed_name:
                if name in ("region", "city", "vuz"):
                    parents = order[:changed_index]
                    available_rows = [
                        row for row in rows
                        if all(
                            not user_selection[parent]
                            or row[FIELDS[parent]] in user_selection[parent]
                            for parent in parents
                        )
                    ]
                    available = {
                        row[index]
                        for row in available_rows
                        if row[index] is not None
                    }
                    available.update(user_selection[name])
                else:
                    available = set(all_items[name])

                visual_chosen = user_selection[name]

            elif name_index < changed_index:
                # Связанные значения из строк, соответствующих реальному выбору.
                related = {
                    row[index]
                    for row in matching_rows
                    if row[index] is not None
                }
                available = set(related) | user_selection[name]
                visual_chosen = related

            elif name_index > changed_index:
                # Нижестоящие списки фильтруются только реальными выборами.
                available_rows = [
                    row for row in rows
                    if row_matches(row, user_selection, excluded=name)
                ]
                available = {
                    row[index]
                    for row in available_rows
                    if row[index] is not None
                }
                visual_chosen = set()

            else:
                continue

            set_combo_items(name, available, visual_chosen)

    def make_handler(name):
        def handler(selected_list):
            nonlocal selected_items, first_changed_combo

            # Первый изменённый пользователем список становится ведущим.
            # Только он запускает автоматическое изменение других списков.
            global filter_first_changed_combo
            selected[name] = set(selected_list)
            if first_changed_combo is None:
                first_changed_combo = name
                filter_first_changed_combo = name

            if name == first_changed_combo:
                update_combos(name)

            print("Текущий выбор:")
            for key in FIELDS:
                print(f"{key}: {sorted(selected[key])}")

        return handler

    # Первоначальное заполнение: если окно уже открывали, восстанавливаем
    # сохранённые отфильтрованные списки и их визуальные выделения.
    for name, combo in combos.items():
        saved_state = filter_combo_state.get(name)
        if saved_state:
            items_to_restore = saved_state.get("items", all_items[name])
            # Восстанавливаем визуальные отметки, включая реальный выбор
            # пользователя в нижестоящих ComboBox. Выделение родителей,
            # добавленное автоматически, не попадает в selected.
            visual_to_restore = (
                set(saved_state.get("visual_chosen", []))
                | set(saved_state.get("user_selected", []))
                | selected[name]
            )
            items_to_restore = sorted(set(items_to_restore) | visual_to_restore)
        else:
            items_to_restore = all_items[name]
            visual_to_restore = selected[name]

        set_combo_items(name, items_to_restore, visual_to_restore)
        combo.setPlaceholderText("Все")

    # Обработчики всех четырёх списков
    for name, combo in combos.items():
        combo.selectionChanged.connect(make_handler(name))

    filterWindow.clear_btn.clicked.connect(clear_fn)
    filterWindow.set_btn.clicked.connect(set_fn)
    filterWindow.cancel_btn.clicked.connect(cancel_fn)

    filterWindow.ntp_combo.setCurrentText(ntp_combo_selected)

    filterWindow.show()

def analysis_nir_by_vuz_btn():
    analysis(1)

def analysis_nir_by_ntp_btn():
    analysis(2)

def analysis_nir_by_type_btn():
    analysis(3)

def open_financing():
    """Передать владение базой окну финансирования до его закрытия."""
    global finansWindow, model, proxy_model
    if finansWindow is not None:
        finansWindow.raise_()
        finansWindow.activateWindow()
        return

    # Модель и запросы больше не должны удерживать закрываемое Qt-подключение.
    form.tableView.setModel(None)
    model = None
    proxy_model = None
    connection = QSqlDatabase.database()
    connection_name = connection.connectionName()
    connection.close()
    del connection
    QSqlDatabase.removeDatabase(connection_name)
    window.setEnabled(False)
    try:
        finansWindow = FinancingWindow(db_file, on_close=close_financing)
        finansWindow.show()
    except Exception as error:
        close_financing()
        QMessageBox.critical(window, "Ошибка", f"Не удалось открыть финансирование:\n{error}")


def close_financing():
    """После sqlite3 восстановить QSql, таблицу и агрегаты НТП."""
    global finansWindow
    finansWindow = None
    try:
        connect_db(db_file)
        rebuild_db()  # Пересчитывает НТП и заново открывает активную таблицу.
        if table_num == 1:
            sort_table()
    finally:
        window.setEnabled(True)


def analysis(mode):
    global analysisWindow, filter_query

    connection_name = QSqlDatabase.database().connectionName()
    QSqlDatabase.database().close()
    QSqlDatabase.removeDatabase(connection_name)

    analysisWindow = uic.loadUi("res/table.ui")
    flags = analysisWindow.windowFlags()
    analysisWindow.setWindowFlags(
        flags &
        ~Qt.WindowType.WindowCloseButtonHint &
        ~Qt.WindowType.WindowMinimizeButtonHint &
        ~Qt.WindowType.WindowMaximizeButtonHint
    )

    con = sqlite3.connect('res/data.db')
    cur = con.cursor()
    table_model = None

    if len(filter_query) <= 2:
        cur.execute("SELECT * FROM ntp_proj")
    else:
        cur.execute(filter_query)
    base_data = cur.fetchall()
    cur.execute("SELECT [код_НТП], [Название_НТП] FROM ntp_prog")
    number_name_NTP = cur.fetchall()

    def export_table_to_pdf(table_view):
        titles = {
            1: "Распределение НИР по ВУЗ",
            2: "Распределение НИР по НТП",
            3: "Распределение НИР по типам",
        }
        if table_view.model() is None:
            messagebox.showwarning("Предупреждение", "У таблицы отсутствует модель данных.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            analysisWindow,
            "Сохранить таблицу в PDF",
            "export.pdf",
            "PDF-файлы (*.pdf)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        # Используем только применённые фильтры (а не SQL или неподтверждённые
        # изменения в окне). НТП сохраняется независимо от геофильтров.
        filters = {name: list(values) for name, values in applied_geo_filters.items()}
        filters["ntp"] = list(ntp_combo_selected)
        try:
            write_pdf(table_view, file_path, titles[mode], filters)
            messagebox.showinfo("Успешно", f"Данные экспортированы в файл:\n{file_path}")
        except Exception as error:
            messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл:\n{error}")

    def analysisWindow_close():
        cur.close()
        con.close()

        connect_db(db_file)
        open_tab_1()
        analysisWindow.close()

    def analysis_nir_by_vuz():
        nonlocal table_model, base_data
        list_vuz = []
        all_ntp = []
        all_finans = 0
        all_nir = 0

        analysisWindow.setWindowTitle("Анализ: распределение НИР по ВУЗ")

        if len(base_data) != 0:
            for i in range(len(base_data)):
                list_vuz.append(base_data[i][3])
            list_vuz = list(set(list_vuz))
            table_model = QStandardItemModel(len(list_vuz)+1, 4)
            headers = ["ВУЗ", "Количество НИР", "Количество НТП", "Сумм. План. Фин"]
            table_model.setHorizontalHeaderLabels(headers)
            analysisWindow.tableView.setModel(table_model)
            for i in range(len(list_vuz)):
                string_to_add = [list_vuz[i], 0, 0, 0]
                temp_ntp = []
                for j in range(len(base_data)):
                    if (base_data[j][3] == list_vuz[i]):
                        temp_ntp.append(base_data[j][0])
                        string_to_add[1] += 1 # счётчик НИРов
                        all_nir += 1
                        string_to_add[3] += base_data[j][8] # Счётчик планового финансирования
                        all_finans += base_data[j][8]
                all_ntp.extend(temp_ntp)
                string_to_add[2] = len(set(temp_ntp))
                for k in range(4):
                    table_model.setData(table_model.index(i, k), str(string_to_add[k]))
            itog = ["ИТОГО: ", str(all_nir), str(len(set(all_ntp))), str(all_finans)]
            for k in range(4):
                table_model.setData(table_model.index(i+1, k), str(itog[k]))

    def analysis_nir_by_ntp():
        nonlocal table_model, base_data, number_name_NTP
        list_ntp = []
        all_vuz = []
        all_finans = 0
        all_nir = 0

        analysisWindow.setWindowTitle("Анализ: распределение НИР по НТП")

        if len(base_data) != 0:
            for i in range(len(base_data)):
                list_ntp.append(base_data[i][0])
            list_ntp = list(set(list_ntp))
            table_model = QStandardItemModel(len(list_ntp)+1, 5)
            headers = ["Код НТП", "Название НТП", "Количество НИР", "Колич. ВУЗ", "Сумм. План. Фин"]
            table_model.setHorizontalHeaderLabels(headers)
            analysisWindow.tableView.setModel(table_model)
            for i in range(len(list_ntp)):
                name_ntp = next((item[1] for item in number_name_NTP if item[0] == list_ntp[i]), None)
                string_to_add = [list_ntp[i], name_ntp, 0, 0, 0]
                temp_vuz = []
                for j in range(len(base_data)):
                    if (base_data[j][0] == list_ntp[i]):
                        temp_vuz.append(base_data[j][3])
                        string_to_add[2] += 1  # счётчик НИРов
                        all_nir += 1
                        string_to_add[4] += base_data[j][8]  # Счётчик планового финансирования
                        all_finans += base_data[j][8]
                all_vuz.extend(temp_vuz)
                string_to_add[3] = len(set(temp_vuz))
                for k in range(5):
                    table_model.setData(table_model.index(i, k), str(string_to_add[k]))
            itog = ["", "ИТОГО: ", str(all_nir), str(len(set(all_vuz))), str(all_finans)]
            for k in range(5):
                table_model.setData(table_model.index(i+1, k), str(itog[k]))

    def analysis_nir_by_type():
        nonlocal table_model, base_data
        list_type = []
        all_ntp = []
        all_vuz = []
        all_finans = 0
        all_nir = 0

        analysisWindow.setWindowTitle("Анализ: распределение НИР по типам")

        if len(base_data) != 0:
            for i in range(len(base_data)):
                list_type.append(base_data[i][7])
            list_type = list(set(list_type))
            table_model = QStandardItemModel(len(list_type)+1, 5)
            headers = ["Тип", "Количество НИР", "Количество НТП", "Количество ВУЗ", "Сумм. План. Фин"]
            table_model.setHorizontalHeaderLabels(headers)
            analysisWindow.tableView.setModel(table_model)
            for i in range(len(list_type)):
                type_nir = ""
                if list_type[i] == "П":
                    type_nir = "Прикладное исследование"
                elif list_type[i] == "Ф":
                    type_nir = "Фундаментальное исследование"
                elif list_type[i] == "Р":
                    type_nir = "Экспериментальная разработка"
                string_to_add = [type_nir, 0, 0, 0, 0]
                temp_ntp = []
                temp_vuz = []
                for j in range(len(base_data)):
                    if (base_data[j][7] == list_type[i]):
                        temp_ntp.append(base_data[j][0])
                        temp_vuz.append(base_data[j][3])
                        string_to_add[1] += 1 # счётчик НИРов
                        all_nir += 1
                        string_to_add[4] += base_data[j][8] # Счётчик планового финансирования
                        all_finans += base_data[j][8]
                all_ntp.extend(temp_ntp)
                all_vuz.extend(temp_vuz)
                string_to_add[2] = len(set(temp_ntp))
                string_to_add[3] = len(set(temp_vuz))
                for k in range(5):
                    table_model.setData(table_model.index(i, k), str(string_to_add[k]))
            itog = ["ИТОГО: ", str(all_nir), str(len(set(all_ntp))), str(len(set(all_vuz))), str(all_finans)]
            for k in range(5):
                table_model.setData(table_model.index(i + 1, k), str(itog[k]))


    if(mode == 1):
        analysis_nir_by_vuz()
    elif(mode == 2):
        analysis_nir_by_ntp()
    elif(mode == 3):
        analysis_nir_by_type()

    analysisWindow.close_btn.clicked.connect(analysisWindow_close)
    # analysisWindow.tableView.setSortingEnabled(True)
    analysisWindow.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    analysisWindow.save_btn.clicked.connect(lambda: export_table_to_pdf(analysisWindow.tableView))
    analysisWindow.show()


################################
# Переменные
################################

addForm = None
addWindow = None
filterForm = None
filterWindow = None
editForm = None
editWindow = None
analysisWindow = None
finansWindow = None
model = None
proxy_model = None
table_num = 1
filter_query = ""
# Применённые пользователем географические фильтры, без автоотметок в ComboBox.
applied_geo_filters = {}
key_selected_record = []
ntp_combo_selected = []
okrug_combo_selected = []
region_combo_selected = []
city_combo_selected = []
vuz_combo_selected = []
# Состояние географических фильтров сохраняется между открытиями окна.
filter_combo_state = {}
filter_first_changed_combo = None

################################
# Инит
################################

Form, Window = uic.loadUiType("res/main_py.ui")

db_file = "res/data.db"

app = QApplication([])
window = Window()
form = Form()
form.setupUi(window)

if not connect_db(db_file):
    sys.exit(-1)
else:
    form.label.setText("Успешное подключение к БД")

form.tableView.setSortingEnabled(True)

form.Sort_btn.setVisible(False)
form.Add_btn.setVisible(False)
form.Edit_btn.setVisible(False)
form.Del_btn.setVisible(False)
form.Filter.setVisible(False)

form.Sort_btn.setEnabled(False)
form.Add_btn.setEnabled(False)
form.Edit_btn.setEnabled(False)
form.Del_btn.setEnabled(False)
form.Filter.setEnabled(False)


################################
# Привязки
################################

form.open_tab_1.triggered.connect(open_tab_1)
form.open_tab_2.triggered.connect(open_tab_2)
form.open_tab_3.triggered.connect(open_tab_3)
form.exit_btn.triggered.connect(exit_btn)
form.rebuild_btn.triggered.connect(rebuild_db)
form.help_btn.triggered.connect(view_help)
form.NIR_by_VUZ.triggered.connect(analysis_nir_by_vuz_btn)
form.NIR_by_NTP.triggered.connect(analysis_nir_by_ntp_btn)
form.NIR_by_type.triggered.connect(analysis_nir_by_type_btn)
form.finans_btn.triggered.connect(open_financing)
form.Sort_btn.clicked.connect(sort_table)
form.tableView.clicked.connect(off_btns)
form.tableView.verticalHeader().sectionClicked.connect(take_record_num)
form.Del_btn.clicked.connect(del_record)
form.Add_btn.clicked.connect(add_record)
form.Edit_btn.clicked.connect(edit_record)
form.Filter.clicked.connect(open_filter_window)

window.show()
app.exec()