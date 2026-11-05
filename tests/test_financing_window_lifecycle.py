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

        def open_financing_window(db_file, on_close_callback):
            events.append(("finance_open", db_file))
            return SimpleNamespace(on_close=on_close_callback,
                                   show=lambda: events.append("finance_shown"))

        namespace = {
            "form": form, "window": window, "model": object(),
            "proxy_model": object(), "finansWindow": None,
            "QSqlDatabase": QSql, "open_financing_window": open_financing_window,
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

    def test_closing_window_closes_sqlite_before_callback(self):
        functions = [node for node in FINANS.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"cancel_btn", "finish_financing"}]
        events = []
        namespace = {
            "cur": SimpleNamespace(close=lambda: events.append("cursor_close")),
            "con": SimpleNamespace(close=lambda: events.append("sqlite_close")),
            "report_quarter": 2,
            "on_close": lambda: events.append("restore_qsql"),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     "finans.py", "exec"), namespace)
        def close_window():
            events.append("window_close")
            namespace["finish_financing"]()  # Qt destroyed после close.
        namespace["finWindow"] = SimpleNamespace(close=close_window)
        namespace["cancel_btn"]()
        namespace["finish_financing"]()  # Повторный сигнал не восстанавливает БД дважды.
        self.assertEqual(events, ["window_close", "cursor_close", "sqlite_close",
                                  "restore_qsql"])
        self.assertIsNone(namespace["finWindow"])
        self.assertIsNone(namespace["report_quarter"])


if __name__ == "__main__":
    unittest.main()
