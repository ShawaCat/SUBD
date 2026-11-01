"""Регрессии распределения и записи без запуска Qt."""

import ast
import math
from datetime import datetime
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / "finans.py").read_text(encoding="utf-8"))
FUNCTIONS = [node for node in TREE.body
             if isinstance(node, ast.FunctionDef) and node.name in
             {"allocate_amounts", "raspred_fn", "write_to_db", "fill_data", "proc_raspred_changed"}]


class FakeItem:
    def __init__(self, value):
        self.value = value


class FakeModel:
    def __init__(self, rows, cols, parent):
        self.rows = rows
        self.cols = cols
        self.cells = {}

    def setHorizontalHeaderLabels(self, labels):
        self.headers = labels

    def setItem(self, row, col, item):
        self.cells[row, col] = item.value


class FakeTableView:
    def __init__(self):
        self.model = None
        self.header = SimpleNamespace(
            ResizeMode=SimpleNamespace(ResizeToContents=object()),
            setSectionResizeMode=lambda *args: None,
        )

    def setModel(self, model):
        self.model = model

    def horizontalHeader(self):
        return self.header


class FakeLineEdit:
    def __init__(self, value=""):
        self.value = value

    def text(self):
        return self.value

    def setText(self, value):
        self.value = value

    def blockSignals(self, blocked):
        pass


class FractionalPercentageTest(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        # Повторяющиеся [НТП, НИР] и пропущенные rowid проверяют сохранение.
        self.con.executescript("""
            CREATE TABLE ntp_proj (
                [НТП] INTEGER, [НИР] INTEGER, [ВУЗ] INTEGER, [План_фин] INTEGER,
                [Ф_фин_1] INTEGER, [Ф_фин_2] INTEGER,
                [Ф_фин_3] INTEGER, [Ф_фин_4] INTEGER, [Факт_фин] INTEGER
            );
            INSERT INTO ntp_proj VALUES (401, 1, 1, 200, 0, 0, 0, 0, 0),
                                        (401, 1, 1, 100, 0, 0, 0, 0, 0);
            CREATE TABLE VUZ (codvuz INTEGER, z1 TEXT);
            INSERT INTO VUZ VALUES (1, 'Университет');
            UPDATE ntp_proj SET rowid = 43 WHERE rowid = 2;
        """)
        self.errors = []
        self.saved = []
        self.window = SimpleNamespace(
            summ_raspred=FakeLineEdit("32"),
            quartal_fin=FakeLineEdit("2"),
            proc_raspred=FakeLineEdit("10.5"),
            tableView=FakeTableView(),
            n_prog=FakeLineEdit(), n_vuz=FakeLineEdit(),
            now_plan_fin=FakeLineEdit(), now_fact_fin=FakeLineEdit(),
            proc_fact_fin=FakeLineEdit(),
        )
        self.context = {
            "con": self.con, "cur": self.con.cursor(), "finWindow": self.window,
            "report_quarter": None, "BASE_DIR": ROOT, "re": re, "math": math,
            "PERCENT_PATTERN": r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)",
            "datetime": SimpleNamespace(now=lambda: datetime(2026, 11, 1)),
            "report_filename": lambda date: "report.pdf",
            "save_report": lambda path, date: self.saved.append(path),
            "QMessageBox": SimpleNamespace(critical=lambda *args: self.errors.append(args)),
            "QStandardItemModel": FakeModel, "QStandardItem": FakeItem,
        }
        exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), "finans.py", "exec"),
             self.context)

    def test_fractional_percentage_is_applied_not_truncated(self):
        self.context["raspred_fn"]()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.con.execute("""
            SELECT [Доб_фин], [Ф_фин_2], [Факт_фин]
            FROM ram_db.ntp_proj ORDER BY rowid
        """).fetchall(), [(21, 21, 21), (11, 11, 11)])
        self.assertEqual(self.con.execute(
            "SELECT [Факт_фин] FROM main.ntp_proj ORDER BY rowid"
        ).fetchall(), [(0,), (0,)])
        self.assertEqual(self.window.tableView.model.cells[1, 1], "32")
        self.assertEqual(self.context["report_quarter"], 2)

    def test_half_percent_from_line_edit(self):
        self.window.proc_raspred.setText(".5")
        self.window.now_plan_fin.setText("300")
        self.context["proc_raspred_changed"]()
        self.assertEqual(self.window.summ_raspred.text(), "2")
        self.context["raspred_fn"]()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.window.tableView.model.cells[1, 1], "2")

    def test_write_matches_duplicate_keys_by_rowid(self):
        self.context["raspred_fn"]()
        self.context["write_to_db"]()
        self.assertEqual(self.con.execute(
            "SELECT [Факт_фин], [Ф_фин_2] FROM ntp_proj ORDER BY rowid"
        ).fetchall(), [(21, 21), (11, 11)])
        self.assertEqual(self.saved, [ROOT / "report.pdf"])

    def test_actual_percentage_rounded_to_three_digits(self):
        self.con.execute("UPDATE ntp_proj SET [Факт_фин] = 1 WHERE rowid = 1")
        self.context["fill_data"]()
        self.assertEqual(self.window.proc_fact_fin.text(), "0.333")
        self.con.execute("UPDATE ntp_proj SET [План_фин] = 0")
        self.context["fill_data"]()
        self.assertEqual(self.window.proc_fact_fin.text(), "0")

    def test_full_sum_for_real_database_at_ten_point_five_percent(self):
        with sqlite3.connect(ROOT / "res/data.db") as database:
            plans = [row[0] for row in database.execute(
                "SELECT [План_фин] FROM ntp_proj ORDER BY rowid"
            )]
        self.assertEqual(sum(plans), 368719200)
        self.assertEqual(sum(self.context["allocate_amounts"](plans, 38715516, 10.5)),
                         38715516)

    def test_invalid_percentage_is_reported_instead_of_crashing(self):
        self.window.proc_raspred.setText("10..5")
        self.context["raspred_fn"]()
        self.assertEqual(len(self.errors), 1)
        self.assertIn("процент", self.errors[0][2])
        self.assertEqual([row[1] for row in self.con.execute("PRAGMA database_list")], ["main"])


if __name__ == "__main__":
    unittest.main()
