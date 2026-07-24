#!/usr/bin/env python3
"""Interfaz web para el procesador de facturas.

Sube una o varias facturas (PDF/imagen) desde el navegador, extrae los datos
con IA y muestra el resultado en una tabla. Permite descargar el Excel/CSV.

Uso:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="tu-api-key"
    python app.py
    # abre http://127.0.0.1:5000

No usar tal cual en producción/Internet: es un servidor local de un solo
usuario, sin autenticación.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import anthropic
from flask import Flask, abort, render_template, request, send_file

from procesar_facturas import (
    EXTENSIONES_IMAGEN,
    EXTENSIONES_PDF,
    Factura,
    exportar,
    procesar_bytes,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB por petición

EXTENSIONES_VALIDAS = set(EXTENSIONES_IMAGEN) | set(EXTENSIONES_PDF)

# Carpeta temporal donde guardamos los Excel generados para descargar.
DIR_DESCARGAS = Path(tempfile.gettempdir()) / "facturas_web"
DIR_DESCARGAS.mkdir(exist_ok=True)


def _cliente() -> anthropic.Anthropic:
    """Crea el cliente de Anthropic (usa ANTHROPIC_API_KEY o el perfil de `ant`)."""
    return anthropic.Anthropic()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/procesar", methods=["POST"])
def procesar():
    archivos = [f for f in request.files.getlist("facturas") if f.filename]
    if not archivos:
        return render_template("index.html", error="No seleccionaste ningún archivo.")

    client = _cliente()
    resultados: list[tuple[str, Factura]] = []
    errores: list[tuple[str, str]] = []

    for f in archivos:
        nombre = f.filename
        if Path(nombre).suffix.lower() not in EXTENSIONES_VALIDAS:
            errores.append((nombre, "Formato no soportado"))
            continue
        try:
            factura = procesar_bytes(client, nombre, f.read())
            resultados.append((nombre, factura))
        except Exception as exc:  # noqa: BLE001 - continuar con las demás
            errores.append((nombre, str(exc)))

    token = None
    if resultados:
        # Genera el Excel + CSV en la carpeta temporal para poder descargarlo.
        token = uuid.uuid4().hex
        exportar(resultados, DIR_DESCARGAS / f"{token}.xlsx")

    return render_template(
        "index.html",
        resultados=resultados,
        errores=errores,
        token=token,
    )


@app.route("/descargar/<token>.<ext>", methods=["GET"])
def descargar(token: str, ext: str):
    if ext not in {"xlsx", "csv"} or not token.isalnum():
        abort(404)
    ruta = DIR_DESCARGAS / f"{token}.{ext}"
    if not ruta.is_file():
        abort(404)
    return send_file(ruta, as_attachment=True, download_name=f"facturas.{ext}")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
