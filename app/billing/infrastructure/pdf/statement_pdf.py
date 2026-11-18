"""The printable statement of a cycle (screen N1), in Spanish like the user's other screens."""

from datetime import date, datetime, tzinfo
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.billing.application.ports.account_directory import AccountHolderInfo
from app.billing.application.query_services.billing_query_service import Statement
from app.shared.domain.value_objects import Money

CYCLE_STATUS = {"OPEN": "Abierto", "CLOSED": "Cerrado", "OVERDUE": "Vencido", "PAID": "Pagado"}
MODE = {"SINGLE_DATE": "Fecha única", "WEEKLY": "Semanal"}
PURCHASE_STATUS = {
    "ACTIVE": "Pendiente",
    "PAID": "Pagada",
    "PREPAID": "Prepagada",
    "VOIDED": "Anulada",
}
GRID = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef3")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]
)


def soles(money: Money | Decimal) -> str:
    amount = money.amount if isinstance(money, Money) else money
    return f"S/ {amount:,.2f}"


def day(value: date | datetime, time_zone: tzinfo | None) -> str:
    if isinstance(value, datetime):
        value = value.astimezone(time_zone).date()
    return value.strftime("%d/%m/%Y")


def render_statement(
    statement: Statement,
    store_name: str,
    holder: AccountHolderInfo,
    issued_at: datetime,
) -> bytes:
    """Return the statement as an A4 PDF, with purchase dates in the time zone of issued_at."""
    time_zone = issued_at.tzinfo
    styles = getSampleStyleSheet()
    cycle = statement.cycle
    header = Table(
        [
            ["Cliente", f"{holder.full_name} (DNI {holder.dni})"],
            ["Periodo", f"{cycle.month:02d}/{cycle.year}"],
            ["Fecha de corte", day(cycle.cutoff_date, time_zone)],
            ["Fecha de pago", day(cycle.payment_date, time_zone)],
            ["Estado", CYCLE_STATUS[statement.status.value]],
            ["Emitido el", day(issued_at, time_zone)],
        ],
        colWidths=[4 * cm, 12 * cm],
        hAlign="LEFT",
    )
    purchases = Table(
        [["Fecha", "Modalidad", "Monto", "Interés", "Estado"]]
        + [
            [
                day(purchase.purchased_at, time_zone),
                MODE[purchase.mode],
                soles(purchase.amount),
                soles(purchase.ordinary_interest),
                PURCHASE_STATUS.get(purchase.status, purchase.status),
            ]
            for purchase in statement.purchases
        ],
        colWidths=[3 * cm, 3 * cm, 3.5 * cm, 3 * cm, 3.5 * cm],
        hAlign="LEFT",
        repeatRows=1,
    )
    purchases.setStyle(GRID)
    totals = Table(
        [
            ["Capital", soles(statement.totals.capital)],
            ["Interés ordinario", soles(statement.totals.ordinary_interest)],
            ["Interés moratorio", soles(statement.late_interest)],
            ["Total a pagar", soles(statement.total)],
        ],
        colWidths=[4 * cm, 4 * cm],
        hAlign="LEFT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    output = BytesIO()
    SimpleDocTemplate(
        output, pagesize=A4, title=f"Estado de cuenta {cycle.month:02d}/{cycle.year}"
    ).build(
        [
            Paragraph(store_name, styles["Title"]),
            Paragraph("Estado de cuenta", styles["Heading2"]),
            header,
            Spacer(1, 0.6 * cm),
            Paragraph("Compras del ciclo", styles["Heading3"]),
            purchases,
            Paragraph(
                "Las compras semanales se pagan en sus cuotas y no suman en este total.",
                styles["Italic"],
            ),
            Spacer(1, 0.6 * cm),
            totals,
        ]
    )
    return output.getvalue()
