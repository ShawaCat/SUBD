"""Проверки экспорта без открытия окон приложения и без базы данных."""

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QApplication, QTableView

from pdf_export import build_export_html, write_pdf


class PdfExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = QTableView()
        model = QStandardItemModel(2, 2)
        model.setHorizontalHeaderLabels(["Название", "Количество НИР"])
        model.setData(model.index(0, 0), 'ВУЗ <№1> & "Партнёр"')
        model.setData(model.index(0, 1), 12)
        model.setData(model.index(1, 0), "ИТОГО:")
        model.setData(model.index(1, 1), 12)
        self.view.setModel(model)
        self.timestamp = datetime(2026, 10, 30, 14, 5, 6)

    def test_report_with_independent_ntp_and_geo_filters(self):
        html = build_export_html(
            self.view, "Распределение НИР по ВУЗ",
            {"city": ["Москва", "Казань"], "vuz": ['МГУ & <1>'],
             "ntp": ["001 - Программа"], "okrug": [], "region": []},
            self.timestamp,
        )
        self.assertIn("30.10.2026 14:05:06", html)
        self.assertIn("Распределение НИР по ВУЗ", html)
        self.assertIn("ВУЗ &lt;№1&gt; &amp; &quot;Партнёр&quot;", html)
        self.assertIn("ИТОГО:", html)
        self.assertIn("<b>Город:</b> Москва, Казань", html)
        self.assertIn("<b>Название ВУЗа:</b> МГУ &amp; &lt;1&gt;", html)
        self.assertIn("<b>НТП:</b> 001 - Программа", html)
        self.assertNotIn("<b>Округ:</b>", html)
        self.assertLess(html.index("</table>"), html.index("Выбранные фильтры"))

    def test_no_filters_means_no_footer(self):
        html = build_export_html(self.view, "Анализ", {}, self.timestamp)
        self.assertNotIn("Выбранные фильтры", html)

    def test_creates_real_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            write_pdf(self.view, str(path), "Распределение НИР по ВУЗ",
                      {"ntp": ["001 - Программа"]}, self.timestamp)
            self.assertTrue(path.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(path.stat().st_size, 1000)

    def test_missing_model_is_rejected(self):
        with self.assertRaises(ValueError):
            build_export_html(QTableView(), "Анализ", {}, self.timestamp)


if __name__ == "__main__":
    unittest.main()
