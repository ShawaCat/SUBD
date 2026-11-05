"""PDF-отчёт по распределению средств из TableView."""

from datetime import datetime
from html import escape
from pathlib import Path


def report_filename(exported_at):
    """Уникальное имя для автоматического сохранения в папку программы."""
    return f"raspredelenie_{exported_at.strftime('%Y%m%d_%H%M%S_%f')}.pdf"


def build_report_html(headers, rows, quarter, exported_at):
    """Дата, назначение средств и снимок таблицы без подстановки HTML из БД."""
    if not isinstance(quarter, int) or isinstance(quarter, bool) or quarter not in (1, 2, 3, 4):
        raise ValueError("Не выбран квартал финансирования")

    def text(value):
        return escape("" if value is None else str(value)).replace("\n", "<br/>")

    heading = (
        "Распределить денежные средства по следующим вузам в следующем объёме "
        f"в качестве финансирования в {quarter} квартале"
    )
    header_html = "".join(f"<th bgcolor='#e8edf3'>{text(value)}</th>" for value in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{text(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return (
        "<html><body>"
        f"<p><b>Дата и время экспорта:</b> {text(exported_at.strftime('%d.%m.%Y %H:%M:%S'))}</p>"
        f"<h2>{text(heading)}</h2>"
        "<table width='100%' border='1' cellspacing='0' cellpadding='5'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody></table>"
        "</body></html>"
    )


def write_table_pdf(table_view, quarter, path, exported_at=None):
    """Печатать именно отображаемую модель TableView на страницы PDF."""
    from PyQt6.QtCore import QMarginsF, Qt
    from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QTextDocument
    from PyQt6.QtPrintSupport import QPrinter

    model = table_view.model()
    if model is None or model.rowCount() == 0:
        raise ValueError("Сначала распределите денежные средства")
    if exported_at is None:
        exported_at = datetime.now()

    headers = [model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
               for col in range(model.columnCount())]
    rows = [
        [model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)
         for col in range(model.columnCount())]
        for row in range(model.rowCount())
    ]
    html = build_report_html(headers, rows, quarter, exported_at)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)

    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 9))
    document.setHtml(html)
    document.print(printer)
    output = Path(path)
    if not output.is_file() or output.stat().st_size == 0:
        raise OSError("PDF-файл не был создан")
