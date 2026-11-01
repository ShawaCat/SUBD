"""Проверки фактического финансирования без запуска окон PyQt."""

import ast
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))


def statement_in(form_function, handler_name, sql_prefix):
    form = next(node for node in TREE.body
                if isinstance(node, ast.FunctionDef) and node.name == form_function)
    handler = next(node for node in form.body
                   if isinstance(node, ast.FunctionDef) and node.name == handler_name)
    return next(node.value.value for node in ast.walk(handler)
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "Q8"
                        for target in node.targets)
                and isinstance(node.value, ast.Constant)
                and sql_prefix in node.value.value)


class RebuildFinancingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "data.db"
        with closing(sqlite3.connect(ROOT / "res/data.db")) as source:
            with closing(sqlite3.connect(self.db_path)) as target:
                source.backup(target)

    def rebuild(self):
        function = next(node for node in TREE.body
                        if isinstance(node, ast.FunctionDef) and node.name == "rebuild_db")
        context = {
            "sqlite3": SimpleNamespace(connect=lambda ignored: sqlite3.connect(self.db_path)),
            "QSqlDatabase": SimpleNamespace(
                database=lambda: SimpleNamespace(connectionName=lambda: "test",
                                                 close=lambda: None),
                removeDatabase=lambda name: None,
            ),
            "db_file": str(self.db_path), "table_num": 1,
            "connect_db": lambda ignored: None, "open_tab_1": lambda: None,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), "main.py", "exec"),
             context)
        context["rebuild_db"]()

    def test_rebuild_does_not_modify_nir_actuals_but_sums_by_program(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute("""UPDATE ntp_proj SET [Факт_фин] = 25,
                [Ф_фин_1] = 1, [Ф_фин_2] = 2, [Ф_фин_3] = 3, [Ф_фин_4] = 4
                WHERE [НТП] = 401 AND [НИР] = 1""")
            con.execute("""UPDATE ntp_proj SET [Факт_фин] = 7,
                [Ф_фин_1] = 0, [Ф_фин_2] = 5, [Ф_фин_3] = 0, [Ф_фин_4] = 2
                WHERE [НТП] = 401 AND [НИР] = 2""")
            # Программа без проектов тоже должна получить нулевые итоги.
            con.execute("""INSERT INTO ntp_prog
                ([код_НТП], [План_фин], [Факт_фин], [Ф_фин_1])
                VALUES (9999, 0, 99, 99)""")
            con.commit()
            before = con.execute("""SELECT rowid, [Факт_фин], [Ф_фин_1],
                [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]
                FROM ntp_proj ORDER BY rowid""").fetchall()

        self.rebuild()
        with closing(sqlite3.connect(self.db_path)) as con:
            self.assertEqual(con.execute("""SELECT rowid, [Факт_фин], [Ф_фин_1],
                [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]
                FROM ntp_proj ORDER BY rowid""").fetchall(), before)
            self.assertEqual(con.execute("""SELECT [Факт_фин], [Ф_фин_1],
                [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]
                FROM ntp_prog WHERE [код_НТП] = 401""").fetchone(),
                (32, 1, 7, 3, 6))
            self.assertEqual(con.execute("""SELECT [Факт_фин], [Ф_фин_1],
                [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]
                FROM ntp_prog WHERE [код_НТП] = 9999""").fetchone(),
                (0, 0, 0, 0, 0))

    def test_new_nir_has_zero_actuals_after_rebuild_and_edit_preserves_them(self):
        insert = statement_in("add_record", "addForm_check_and_save", "INSERT INTO ntp_proj")
        update = statement_in("edit_record", "editForm_check_and_save", "UPDATE ntp_proj")
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(insert, (401, 9999, 90, 'РГГРУ', 'Руководитель', 'Должность',
                                 '01.01.01', 'П', 1000, 0, 0, 0, 0, 0,
                                 'Новая НИР', 1, 4))
            self.assertEqual(con.execute("""
                SELECT [Факт_фин], [Ф_фин_1], [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]
                FROM ntp_proj WHERE [НТП] = 401 AND [НИР] = 9999
            """).fetchone(), (0, 0, 0, 0, 0))
            # Существующее финансирование нельзя терять при правке реквизитов.
            con.execute("""UPDATE ntp_proj SET [Факт_фин] = 17,
                [Ф_фин_1] = 2, [Ф_фин_2] = 4, [Ф_фин_3] = 5, [Ф_фин_4] = 6
                WHERE [НТП] = 401 AND [НИР] = 1""")
            con.execute(update, (401, 1, 90, 'РГГРУ', 'Новый руководитель',
                                 'Должность', '01.01.01', 'П', 800000,
                                 'Название', 1, 4, 401, 1))
            con.commit()

        self.rebuild()
        with closing(sqlite3.connect(self.db_path)) as con:
            actuals = "[Факт_фин], [Ф_фин_1], [Ф_фин_2], [Ф_фин_3], [Ф_фин_4]"
            self.assertEqual(con.execute(
                f"SELECT {actuals} FROM ntp_proj WHERE [НТП] = 401 AND [НИР] = 9999"
            ).fetchone(), (0, 0, 0, 0, 0))
            self.assertEqual(con.execute(
                f"SELECT {actuals} FROM ntp_proj WHERE [НТП] = 401 AND [НИР] = 1"
            ).fetchone(), (17, 2, 4, 5, 6))


if __name__ == "__main__":
    unittest.main()
