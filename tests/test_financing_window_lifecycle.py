"""Переход между QSql и финансированием без запуска Qt event loop."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
FINANS = ast.parse((ROOT / "finans.py").read_text(encoding="utf-8"))


class FinancingWindowLifecycleTest(unittest.TestCase):
    def test_action_closes_qsql_and_restores_main_after_close(self):
        functions = [node for node in MAIN.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"open_financing", "close_financing"}]
        events = []
        window = SimpleNamespace(
            setEnabled=lambda enabled: events.append(("main_enabled", enabled)))
        table_view = SimpleNamespace(setModel=lambda model: events.append(("model", model)))
        form = SimpleNamespace(tableView=table_view)

        class Connection:
            def connectionName(self):
                return "qt-main"

            def close(self):
                events.append("qsql_closed")

        class QSql:
            @staticmethod
            def database():
                return Connection()

            @staticmethod
            def removeDatabase(name):
                events.append(("qsql_removed", name))

        class Finance:
            def __init__(self, db_file, on_close):
                events.append(("finance_open", db_file))
                self.on_close = on_close

            def show(self):
                events.append("finance_shown")

        namespace = {
            "form": form, "window": window, "model": object(),
            "proxy_model": object(), "finansWindow": None,
            "QSqlDatabase": QSql, "FinancingWindow": Finance,
            "db_file": "res/data.db", "table_num": 1,
            "connect_db": lambda db: events.append(("qsql_connected", db)),
            "rebuild_db": lambda: events.append("rebuild"),
            "sort_table": lambda: events.append("sort"),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "main.py", "exec"),
             namespace)
        namespace["open_financing"]()
        finance = namespace["finansWindow"]
        self.assertIsNotNone(finance)
        self.assertEqual(events[:5], [
            ("model", None), "qsql_closed", ("qsql_removed", "qt-main"),
            ("main_enabled", False), ("finance_open", "res/data.db")])
        self.assertEqual(events[-1], "finance_shown")
        finance.on_close()
        self.assertIsNone(namespace["finansWindow"])
        self.assertEqual(events[-4:], [
            ("qsql_connected", "res/data.db"), "rebuild", "sort",
            ("main_enabled", True)])

    def test_close_event_closes_sqlite_before_callback(self):
        window_class = next(node for node in FINANS.body
                            if isinstance(node, ast.ClassDef) and node.name == "FinancingWindow")
        close_event = next(node for node in window_class.body
                           if isinstance(node, ast.FunctionDef) and node.name == "closeEvent")
        events = []
        class Base:
            def closeEvent(self, event):
                events.append("base_close")
        isolated = ast.ClassDef(name="FinancingWindow", bases=[ast.Name(id="Base", ctx=ast.Load())],
                                keywords=[], body=[close_event], decorator_list=[])
        namespace = {"Base": Base}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])),
                     "finans.py", "exec"), namespace)
        window = namespace["FinancingWindow"]()
        window._closed = False
        window.cur = SimpleNamespace(close=lambda: events.append("cursor_close"))
        window.con = SimpleNamespace(close=lambda: events.append("sqlite_close"))
        window._on_close = lambda: events.append("restore_qsql")
        window.closeEvent(object())
        window.closeEvent(object())
        self.assertEqual(events, ["cursor_close", "sqlite_close", "restore_qsql",
                                  "base_close", "base_close"])


if __name__ == "__main__":
    unittest.main()
