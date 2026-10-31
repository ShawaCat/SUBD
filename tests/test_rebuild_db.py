"""Проверки пересчёта БД без запуска графического интерфейса PyQt."""

import ast
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


# main.py запускает GUI при импорте; загружаем только проверяемую функцию.
source = ast.parse((Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8"))
rebuild_function = next(node for node in source.body
                        if isinstance(node, ast.FunctionDef) and node.name == "rebuild_db")
rebuild_code = compile(ast.Module(body=[rebuild_function], type_ignores=[]),
                       "main.py", "exec")


class RebuildDbTest(unittest.TestCase):
    def test_actual_totals_and_quarters_are_recalculated(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "data.db"
            with sqlite3.connect(db_path) as con:
                con.executescript("""
                    CREATE TABLE VUZ (codvuz INTEGER, z2 TEXT);
                    INSERT INTO VUZ VALUES (1, 'ВУЗ');
                    CREATE TABLE ntp_proj (
                        [НТП] INTEGER, [НИР] INTEGER, [ВУЗ] INTEGER, [Исп_орг] TEXT,
                        [План_фин] INTEGER, [Факт_фин] INTEGER,
                        [П_фин_1] INTEGER, [П_фин_2] INTEGER,
                        [П_фин_3] INTEGER, [П_фин_4] INTEGER,
                        [Ф_фин_1] INTEGER, [Ф_фин_2] INTEGER,
                        [Ф_фин_3] INTEGER, [Ф_фин_4] INTEGER
                    );
                    CREATE TABLE ntp_prog (
                        [код_НТП] INTEGER, [Кол_п] INTEGER,
                        [План_фин] INTEGER, [Факт_фин] INTEGER,
                        [П_фин_1] INTEGER, [П_фин_2] INTEGER,
                        [П_фин_3] INTEGER, [П_фин_4] INTEGER,
                        [Ф_фин_1] INTEGER, [Ф_фин_2] INTEGER,
                        [Ф_фин_3] INTEGER, [Ф_фин_4] INTEGER
                    );
                    INSERT INTO ntp_prog ([код_НТП], [План_фин], [Факт_фин])
                    VALUES (1, 0, 0), (2, 0, 0), (3, 0, 99);
                    INSERT INTO ntp_proj ([НТП], [НИР], [ВУЗ], [План_фин], [Факт_фин])
                    VALUES (1, 1, 1, 8, 5), (1, 2, 1, 11, 7),
                           (2, 1, 1, 9, NULL);
                """)

            database = SimpleNamespace(connectionName=lambda: "test", close=lambda: None)
            context = {
                "QSqlDatabase": SimpleNamespace(database=lambda: database,
                                                removeDatabase=lambda name: None),
                "sqlite3": SimpleNamespace(connect=lambda ignored: sqlite3.connect(db_path)),
                "db_file": str(db_path), "table_num": 1,
                "connect_db": lambda name: None, "open_tab_1": lambda: None,
            }
            exec(rebuild_code, context)
            context["rebuild_db"]()

            with sqlite3.connect(db_path) as con:
                def quarters(table, code_column, code, nir=None):
                    fields = ', '.join(f'[Ф_фин_{i}]' for i in range(1, 5))
                    where = f'[{code_column}] = ?'
                    params = [code]
                    if nir is not None:
                        where += ' AND [НИР] = ?'
                        params.append(nir)
                    return con.execute(
                        f'SELECT [Факт_фин], {fields} FROM {table} WHERE {where}',
                        params,
                    ).fetchone()

                self.assertEqual(quarters('ntp_proj', 'НТП', 1, 1), (5, 1, 1, 1, 2))
                self.assertEqual(quarters('ntp_proj', 'НТП', 1, 2), (7, 1, 1, 1, 4))
                self.assertEqual(quarters('ntp_proj', 'НТП', 2, 1), (None, 0, 0, 0, 0))
                self.assertEqual(quarters('ntp_prog', 'код_НТП', 1), (12, 3, 3, 3, 3))
                self.assertEqual(quarters('ntp_prog', 'код_НТП', 2), (0, 0, 0, 0, 0))
                self.assertEqual(quarters('ntp_prog', 'код_НТП', 3), (0, 0, 0, 0, 0))
                self.assertEqual(con.execute(
                    'SELECT [План_фин], [П_фин_1], [П_фин_4] '
                    'FROM ntp_prog WHERE [код_НТП] = 1'
                ).fetchone(), (19, 4, 7))
                con.execute('UPDATE ntp_proj SET [Факт_фин] = 10 '
                            'WHERE [НТП] = 1 AND [НИР] = 2')
                con.commit()

            context["rebuild_db"]()
            with sqlite3.connect(db_path) as con:
                self.assertEqual(con.execute(
                    'SELECT [Факт_фин], [Ф_фин_1], [Ф_фин_2], [Ф_фин_3], [Ф_фин_4] '
                    'FROM ntp_prog WHERE [код_НТП] = 1'
                ).fetchone(), (15, 3, 3, 3, 6))


if __name__ == "__main__":
    unittest.main()
