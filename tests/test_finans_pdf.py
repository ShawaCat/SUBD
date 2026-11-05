"""Заголовок PDF и поведение экспорта без запуска PyQt6."""

import ast
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from finans_pdf import build_report_html, report_filename

ROOT = Path(__file__).resolve().parents[1]


class PdfReportTest(unittest.TestCase):
    def test_header_date_quarter_and_view_rows(self):
        exported_at = datetime(2026, 11, 1, 15, 7, 8)
        html = build_report_html(
            ["ВУЗ", "К начислению"],
            [("МГУ & <1>", 1250), ("СПбГУ", 200)], 3, exported_at,
        )
        self.assertIn("Дата и время экспорта:</b> 01.11.2026 15:07:08", html)
        self.assertIn(
            "Распределить денежные средства по следующим вузам в следующем "
            "объёме в качестве финансирования в 3 квартале", html,
        )
        self.assertIn("МГУ &amp; &lt;1&gt;", html)
        self.assertIn("<td>1250</td>", html)
        self.assertLess(html.index("МГУ"), html.index("СПбГУ"))
        self.assertEqual(report_filename(exported_at),
                         "raspredelenie_20261101_150708_000000.pdf")
        for invalid in (None, 0, 5):
            with self.assertRaises(ValueError):
                build_report_html([], [], invalid, exported_at)

    def test_dialog_and_auto_save_share_one_report_without_database_writes(self):
        code = ast.parse((ROOT / "finans.py").read_text(encoding="utf-8"))
        functions = [node for node in code.body
                     if isinstance(node, ast.FunctionDef) and node.name in
                     {"save_report", "export_pdf"}]
        exported_at = datetime(2026, 11, 1, 15, 7, 8)

        class FixedClock:
            @staticmethod
            def now():
                return exported_at

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            calls = []
            errors = []
            file_dialog = SimpleNamespace(getSaveFileName=lambda *args: (str(path / "report"), ""))
            namespace = {
                "datetime": FixedClock, "report_filename": report_filename,
                "QFileDialog": file_dialog, "BASE_DIR": path,
                "finWindow": SimpleNamespace(tableView=object()), "report_quarter": 2,
                "write_table_pdf": lambda *args: calls.append(args),
                "QMessageBox": SimpleNamespace(
                    critical=lambda *args: errors.append(args),
                    information=lambda *args: None,
                ),
            }
            exec(compile(ast.Module(body=functions, type_ignores=[]),
                         "finans.py", "exec"), namespace)
            namespace["export_pdf"]()
            self.assertEqual(calls[-1][1:], (2, str(path / "report.pdf"), exported_at))
            self.assertEqual(errors, [])

            # Отмена диалога не запускает печать и не создаёт файл.
            namespace["QFileDialog"] = SimpleNamespace(
                getSaveFileName=lambda *args: ("", "")
            )
            namespace["export_pdf"]()
            self.assertEqual(len(calls), 1)

            # Экспорт до распределения невозможен.
            namespace["report_quarter"] = None
            namespace["export_pdf"]()
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
