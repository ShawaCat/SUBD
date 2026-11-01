"""Регрессии распределения и записи без запуска Qt."""

import ast
import math
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / "finans.py").read_text(encoding="utf-8"))
FUNCTIONS = [node for node in TREE.body
             if isinstance(node, ast.FunctionDef) and node.name == "allocate_amounts"]
FINANCING_CLASS = next(node for node in TREE.body
                       if isinstance(node, ast.ClassDef) and node.name == "FinancingWindow")
FUNCTIONS += [node for node in FINANCING_CLASS.body
              if isinstance(node, ast.FunctionDef) and node.name in {"raspred_fn", "write_to_db_fn"}]


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


class FractionalPercentageTest(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        # Две строки с одинаковым [НТП, НИР] проверяют запись по rowid.
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
            summ_raspred=SimpleNamespace(text=lambda: "32"),
            quartal_fin=SimpleNamespace(text=lambda: "2"),
            proc_raspred=SimpleNamespace(text=lambda: "10.5"),
            tableView=FakeTableView(),
            con=self.con, cur=self.con.cursor(), report_quarter=None,
            base_dir=ROOT, fill_data=lambda: None,
            save_report=lambda path, date: self.saved.append(path),
        )
        self.context = {
            "math": math,
            "QMessageBox": SimpleNamespace(critical=lambda *args: self.errors.append(args)),
            "QStandardItemModel": FakeModel, "QStandardItem": FakeItem,
        }
        exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), "finans.py", "exec"),
             self.context)

    def test_fractional_percentage_is_applied_not_truncated(self):
        self.context["raspred_fn"](self.window)
        self.assertEqual(self.errors, [])
        self.assertEqual(self.con.execute("""
            SELECT [Доб_фин], [Ф_фин_2], [Факт_фин]
            FROM ram_db.ntp_proj ORDER BY rowid
        """).fetchall(), [(21, 21, 21), (11, 11, 11)])
        self.assertEqual(self.con.execute(
            "SELECT [Факт_фин] FROM main.ntp_proj ORDER BY rowid"
        ).fetchall(), [(0,), (0,)])
        self.assertEqual(self.window.tableView.model.cells[1, 1], "32")
        self.assertEqual(self.window.report_quarter, 2)

    def test_write_matches_duplicate_keys_by_rowid(self):
        from datetime import datetime
        class Clock:
            @staticmethod
            def now():
                return datetime(2026, 11, 1)
        self.context["datetime"] = Clock
        self.context["report_filename"] = lambda date: "report.pdf"
        self.context["raspred_fn"](self.window)
        self.context["write_to_db_fn"](self.window)
        self.assertEqual(self.con.execute(
            "SELECT [Факт_фин], [Ф_фин_2] FROM ntp_proj ORDER BY rowid"
        ).fetchall(), [(21, 21), (11, 11)])
        self.assertEqual(self.saved, [ROOT / "report.pdf"])

    def test_full_sum_for_real_database_at_ten_point_five_percent(self):
        with sqlite3.connect(ROOT / "res/data.db") as database:
            plans = [row[0] for row in database.execute(
                "SELECT [План_фин] FROM ntp_proj ORDER BY rowid"
            )]
        self.assertEqual(sum(plans), 368719200)
        self.assertEqual(sum(self.context["allocate_amounts"](plans, 38715516, 10.5)),
                         38715516)

    def test_invalid_percentage_is_reported_instead_of_crashing(self):
        self.window.proc_raspred = SimpleNamespace(text=lambda: "10..5")
        self.context["raspred_fn"](self.window)
        self.assertEqual(len(self.errors), 1)
        self.assertIn("процент", self.errors[0][2])
        self.assertEqual([row[1] for row in self.con.execute("PRAGMA database_list")], ["main"])


if __name__ == "__main__":
    unittest.main()
