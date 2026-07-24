#!/usr/bin/env python3
"""Procesador de facturas: extrae datos de facturas en PDF e imagen usando IA.

Lee todas las facturas de una carpeta y extrae, con el modelo de Claude, los
campos: Cédula o RIF, Nombre o Razón Social, Fecha y hora, Número de factura y
Monto total. Vuelca el resultado a un Excel y a un CSV.

Uso básico:
    python procesar_facturas.py ./facturas
    python procesar_facturas.py ./facturas -o resultados.xlsx

Requisitos:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="tu-api-key"   (o usa `ant auth login`)
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

# Modelo a usar. Opus 4.8 es el más capaz para lectura de documentos.
MODELO = "claude-opus-4-8"

# Extensiones de archivo que sabemos procesar.
EXTENSIONES_IMAGEN = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
EXTENSIONES_PDF = {".pdf": "application/pdf"}


# ---------------------------------------------------------------------------
# Esquema de datos que queremos extraer de cada factura.
# ---------------------------------------------------------------------------
class Factura(BaseModel):
    """Datos que se extraen de cada factura."""

    comercio: str | None = Field(
        default=None,
        description="Nombre del comercio/emisor (la razón social que aparece arriba, p.ej. 'FARMATODO, C.A.')",
    )
    rif_comercio: str | None = Field(
        default=None,
        description="RIF de la empresa/emisor, el que aparece arriba con formato 'J-xxxxxxxx' (p.ej. 'J-000202001')",
    )
    cedula_rif: str | None = Field(
        default=None,
        description="Cédula o RIF del cliente/receptor (campo 'RIF/C.I.'), NO el RIF de la tienda o emisor",
    )
    nombre_razon_social: str | None = Field(
        default=None,
        description="Nombre o Razón Social del cliente/receptor (campo 'RAZON SOCIAL')",
    )
    fecha_hora: str | None = Field(
        default=None,
        description="Fecha y hora de la factura, combinadas (p.ej. '09-07-2026 17:06')",
    )
    numero_factura: str | None = Field(
        default=None,
        description="Número de factura (campo 'FACTURA'), tal cual aparece",
    )
    iva: float | None = Field(
        default=None,
        description="Monto del IVA como número con punto decimal (p.ej. 3027.21), sin símbolo de moneda ni separadores de miles",
    )
    monto_total: float | None = Field(
        default=None,
        description="Monto total de la factura como número con punto decimal (p.ej. 21947.26), sin símbolo de moneda ni separadores de miles",
    )

    @property
    def base(self) -> float | None:
        """Base imponible = TOTAL - IVA (calculada, redondeada a 2 decimales)."""
        if self.monto_total is None or self.iva is None:
            return None
        return round(self.monto_total - self.iva, 2)


# Columnas de salida (orden fijo) y cómo obtener cada valor de una Factura.
COLUMNAS = [
    "archivo", "comercio", "rif_comercio", "cedula_rif", "nombre_razon_social",
    "fecha_hora", "numero_factura", "base", "iva", "monto_total",
]

PROMPT = (
    "Eres un asistente experto en facturas. Extrae de esta factura EXCLUSIVAMENTE estos "
    "datos, en el formato estructurado solicitado:\n"
    "- Nombre del comercio/emisor (la razón social de arriba, p.ej. 'FARMATODO, C.A.').\n"
    "- RIF de la empresa/emisor (el de arriba, formato 'J-xxxxxxxx').\n"
    "- Cédula o RIF del cliente/receptor (el campo 'RIF/C.I.'), NO el RIF de la tienda/emisor.\n"
    "- Nombre o Razón Social del cliente/receptor (el campo 'RAZON SOCIAL').\n"
    "- Fecha y hora de la factura (combínalas en un solo texto).\n"
    "- Número de factura (el campo 'FACTURA').\n"
    "- IVA (el monto del impuesto IVA).\n"
    "- Monto total (el 'TOTAL').\n"
    "Si un campo no aparece, déjalo vacío (null); no inventes valores. Los montos (IVA y total) deben "
    "ser numéricos con punto decimal (p.ej. 21947.26), sin símbolo de moneda ni separadores de miles."
)


def bloque_desde_bytes(nombre: str, contenido: bytes) -> dict:
    """Construye el bloque de contenido (imagen o documento) a partir de bytes."""
    ext = Path(nombre).suffix.lower()
    datos = base64.standard_b64encode(contenido).decode("utf-8")

    if ext in EXTENSIONES_IMAGEN:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": EXTENSIONES_IMAGEN[ext], "data": datos},
        }
    if ext in EXTENSIONES_PDF:
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": datos},
        }
    raise ValueError(f"Extensión no soportada: {ext}")


def bloque_contenido(ruta: Path) -> dict:
    """Construye el bloque de contenido (imagen o documento) desde un archivo."""
    return bloque_desde_bytes(ruta.name, ruta.read_bytes())


def procesar_bytes(client: anthropic.Anthropic, nombre: str, contenido: bytes) -> Factura:
    """Envía una factura (en bytes) a Claude y devuelve los datos extraídos."""
    respuesta = client.messages.parse(
        model=MODELO,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [bloque_desde_bytes(nombre, contenido), {"type": "text", "text": PROMPT}],
            }
        ],
        output_format=Factura,
    )
    return respuesta.parsed_output


def procesar_factura(client: anthropic.Anthropic, ruta: Path) -> Factura:
    """Envía una factura (desde archivo) a Claude y devuelve los datos extraídos."""
    return procesar_bytes(client, ruta.name, ruta.read_bytes())


def fila(nombre: str, f: Factura) -> list:
    """Devuelve la fila de salida (en el orden de COLUMNAS) para una factura."""
    return [
        nombre, f.comercio, f.rif_comercio, f.cedula_rif, f.nombre_razon_social,
        f.fecha_hora, f.numero_factura, f.base, f.iva, f.monto_total,
    ]


def buscar_facturas(carpeta: Path) -> list[Path]:
    """Devuelve la lista ordenada de archivos procesables en la carpeta."""
    validas = set(EXTENSIONES_IMAGEN) | set(EXTENSIONES_PDF)
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in validas)


def exportar(resultados: list[tuple[str, Factura]], salida_xlsx: Path) -> None:
    """Escribe los resultados a un Excel y a un CSV (una fila por factura)."""
    import csv

    from openpyxl import Workbook

    wb = Workbook()
    hoja = wb.active
    hoja.title = "Facturas"
    hoja.append(COLUMNAS)
    filas = [fila(archivo, f) for archivo, f in resultados]
    for fl in filas:
        hoja.append(fl)
    wb.save(salida_xlsx)

    salida_csv = salida_xlsx.with_suffix(".csv")
    with salida_csv.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.writer(fh)
        escritor.writerow(COLUMNAS)
        escritor.writerows(filas)

    print(f"\n✓ Excel:  {salida_xlsx}")
    print(f"✓ CSV:    {salida_csv}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae datos de facturas (PDF/imagen) a Excel y CSV.")
    parser.add_argument("carpeta", type=Path, help="Carpeta con las facturas a procesar")
    parser.add_argument("-o", "--salida", type=Path, default=Path("facturas_procesadas.xlsx"), help="Archivo Excel de salida")
    args = parser.parse_args()

    if not args.carpeta.is_dir():
        print(f"Error: '{args.carpeta}' no es una carpeta.", file=sys.stderr)
        return 1

    facturas = buscar_facturas(args.carpeta)
    if not facturas:
        print(f"No se encontraron facturas (PDF/JPG/PNG) en '{args.carpeta}'.", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()  # Toma ANTHROPIC_API_KEY o el perfil de `ant auth login`.

    resultados: list[tuple[str, Factura]] = []
    print(f"Procesando {len(facturas)} factura(s)...\n")
    for i, ruta in enumerate(facturas, 1):
        print(f"[{i}/{len(facturas)}] {ruta.name} ...", end=" ", flush=True)
        try:
            factura = procesar_factura(client, ruta)
            resultados.append((ruta.name, factura))
            print(f"OK  (factura: {factura.numero_factura}, total: {factura.monto_total})")
        except Exception as exc:  # noqa: BLE001 - queremos continuar con las demás
            print(f"ERROR: {exc}")

    if resultados:
        exportar(resultados, args.salida)
    else:
        print("\nNo se pudo procesar ninguna factura.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
