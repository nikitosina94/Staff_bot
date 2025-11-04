from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def save_report_xlsx(report, filename="/mnt/data/report.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Отчёт"
    ws.append(["ФИО", "Должность", "Дни присутствия", "Количество смен"])
    for r in report:
        ws.append([r["name"], r["position"] or "-", ", ".join(r["days"]), r["total"]])
    wb.save(filename)
    return filename


def save_report_pdf(report, filename="/mnt/data/report.pdf"):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    elements.append(Paragraph("<b>Отчёт по сотрудникам</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    for r in report:
        elements.append(Paragraph(f"<b>{r['name']}</b> ({r['position'] or '—'})", styles["Heading3"]))
        elements.append(Paragraph(f"Дни: {', '.join(r['days']) or '—'}", styles["BodyText"]))
        elements.append(Paragraph(f"Смен: {r['total']}", styles["BodyText"]))
        elements.append(Spacer(1, 12))
    doc.build(elements)
    return filename
