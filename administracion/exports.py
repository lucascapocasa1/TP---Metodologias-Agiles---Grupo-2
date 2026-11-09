"""Exportación de reportes a Excel (openpyxl).

Todas las funciones reciben un `negocio` y devuelven un objeto
openpyxl.workbook.workbook.Workbook listo para ser guardado o enviado como
respuesta HTTP.
"""
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from ventas.models import Producto

# Estilos reutilizables
HEADER_FILL = PatternFill(start_color="00C8E0", end_color="00C8E0", fill_type="solid")
HEADER_FONT = Font(bold=True, color="05121A")
CELL_FONT = Font(color="17130E")
TITLE_FONT = Font(bold=True, size=14, color="05121A")
BORDER = Border(
    left=Side(style="thin", color="5A7E8E"),
    right=Side(style="thin", color="5A7E8E"),
    top=Side(style="thin", color="5A7E8E"),
    bottom=Side(style="thin", color="5A7E8E"),
)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")


def _formatear_fecha_ddmmaaaa(fecha):
    """Devuelve una fecha como DD/MM/AAAA o cadena vacía si es None."""
    if fecha is None:
        return ""
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return fecha.strftime("%d/%m/%Y")


def exportar_stock_a_excel(negocio):
    """Genera un Workbook de Excel con el stock de un negocio.

    Columnas:
    - Producto
    - Categoría
    - Código de barras
    - Stock actual
    - Stock mínimo
    - Precio
    - Costo
    - Valor a costo (stock × costo)
    - Valor a venta (stock × precio)
    - Margen unitario (precio − costo)
    - Margen % ((margen / costo) × 100)

    Solo incluye productos activos del negocio indicado, incluso si tienen
    stock en cero.
    """
    productos = (
        Producto.objects.filter(negocio=negocio, activo=True)
        .select_related("categoria")
        .order_by("categoria__nombre", "nombre")
    )

    wb = Workbook()
    ws = wb.active
    ws.title = f"Stock {negocio.nombre}"

    # Título
    ws.merge_cells("A1:K1")
    celda_titulo = ws["A1"]
    celda_titulo.value = f"Stock - {negocio.nombre}"
    celda_titulo.font = TITLE_FONT
    celda_titulo.alignment = LEFT

    # Fecha de generación
    ws.merge_cells("A2:K2")
    celda_fecha = ws["A2"]
    celda_fecha.value = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    celda_fecha.font = Font(size=10, color="6A6154")
    celda_fecha.alignment = LEFT

    # Encabezados
    encabezados = [
        "Producto",
        "Categoría",
        "Código de barras",
        "Stock actual",
        "Stock mínimo",
        "Precio",
        "Costo",
        "Valor a costo",
        "Valor a venta",
        "Margen unitario",
        "Margen %",
    ]
    fila_encabezados = 4
    for col_idx, encabezado in enumerate(encabezados, start=1):
        celda = ws.cell(row=fila_encabezados, column=col_idx, value=encabezado)
        celda.font = HEADER_FONT
        celda.fill = HEADER_FILL
        celda.border = BORDER
        celda.alignment = CENTER

    # Datos
    for fila_idx, producto in enumerate(productos, start=fila_encabezados + 1):
        margen_unitario = producto.precio - producto.costo
        margen_porcentual = (
            (margen_unitario / producto.costo * 100) if producto.costo else 0
        )

        datos = [
            producto.nombre,
            producto.categoria.nombre,
            producto.codigo_barras or "",
            producto.stock,
            producto.stock_minimo,
            float(producto.precio),
            float(producto.costo),
            float(producto.costo * producto.stock),
            float(producto.precio * producto.stock),
            float(margen_unitario),
            float(margen_porcentual),
        ]

        for col_idx, valor in enumerate(datos, start=1):
            celda = ws.cell(row=fila_idx, column=col_idx, value=valor)
            celda.font = CELL_FONT
            celda.border = BORDER
            if col_idx in (6, 7, 8, 9, 10):  # columnas monetarias
                celda.number_format = '"$"#,##0.00'
            if col_idx == 11:  # margen %
                celda.number_format = '0.00"%"'
            celda.alignment = CENTER if col_idx != 1 else LEFT

    # Anchos de columna
    anchos = [25, 20, 20, 15, 15, 12, 12, 15, 15, 15, 12]
    for idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ancho

    # Congelar encabezados
    ws.freeze_panes = f"A{fila_encabezados + 1}"

    return wb
