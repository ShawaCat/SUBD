"""Экспорт таблицы анализа в PDF средствами уже используемого PyQt6."""

from datetime import datetime
from html import escape

from PyQt6.QtCore import QMarginsF, Qt
from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QTextDocument
from PyQt6.QtPrintSupport import QPrinter


FILTER_LABELS = (
    ("okrug", "Округ"),
    ("region", "Регион"),
    ("city", "Город"),
    ("vuz", "Название ВУЗа"),
    ("ntp", "НТП"),
)


def build_export_html(table_view, title, filters, exported_at):
    """Составить отчёт из данных модели, а не из SQL (включая строку ИТОГО)."""
    model = table_view.model()
    if model is None:
        raise ValueError("У таблицы отсутствует модель данных.")

    def text(value):
        return escape("" if value is None else str(value)).replace("\n", "<br/>")

    headers = [
        model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        for col in range(model.columnCount())
    ]
    header_cells = "".join(f"<th bgcolor='#e8edf3'>{text(header)}</th>" for header in headers)
    rows = []
    for row in range(model.rowCount()):
        cells = "".join(
            f"<td>{text(model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole))}</td>"
            for col in range(model.columnCount())
        )
        rows.append(f"<tr>{cells}</tr>")

    selected = [
        (label, list(filters.get(key) or []))
        for key, label in FILTER_LABELS
        if filters.get(key)
    ]
    footer = ""
    if selected:
        lines = "".join(
            f"<p><b>{text(label)}:</b> {', '.join(text(value) for value in values)}</p>"
            for label, values in selected
        )
        footer = f"<h3>Выбранные фильтры</h3>{lines}"

    return (
        "<html><body>"
        f"<h2>{text(title)}</h2>"
        f"<p><b>Дата и время экспорта:</b> {text(exported_at.strftime('%d.%m.%Y %H:%M:%S'))}</p>"
        "<table width='100%' border='1' cellspacing='0' cellpadding='5'>"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"{footer}</body></html>"
    )


def write_pdf(table_view, file_path, title, filters, exported_at=None):
    """Печатать весь отчёт, включая длинные таблицы, на страницах A4 PDF."""
    html = build_export_html(table_view, title, filters, exported_at or datetime.now())
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(file_path)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)

    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 9))
    document.setHtml(html)
    document.print_(printer)
