# Procesador de Facturas

App web para extraer datos de **facturas** (fotos, capturas de pantalla, imágenes o PDF).
Todo el procesamiento ocurre **en el navegador** con OCR local (Tesseract.js + pdf.js) —
no hay servidor, no se necesita clave de API y no se envía nada a Internet.

Mismo modelo que [reporte-cobranza](https://boadar.github.io/reporte-cobranza): una sola
página estática que puede publicarse en GitHub Pages.

## Uso

Abre la app y sube (o toma foto de) una o varias facturas. Extrae:

- **Comercio** y **RIF del comercio** (emisor, el `RIF J-xxxxxxxx` de arriba)
- **Cédula o RIF** y **Nombre / Razón Social** del cliente
- **Fecha y hora**
- **Número de factura**
- **IVA**
- **Monto total**
- **Base** (calculada: `Total − IVA`)

Los datos se muestran en tarjetas **editables** (puedes corregir cualquier campo). Al pulsar
**Guardar facturas** pasan a un **reporte de facturas guardadas** (almacenado en el propio
dispositivo), donde puedes **editar**, **eliminar** (una, varias o todas) y descargarlas a
**Excel** o **CSV**.

## Publicar en GitHub Pages

El sitio se sirve desde el archivo `index.html` en la rama `main`:

1. En GitHub → **Settings → Pages**.
2. En **Source**, elige la rama `main` y la carpeta `/ (root)`.
3. Guarda. En un par de minutos estará disponible en
   `https://boadar.github.io/facturas`.

## Probar localmente

Como usa CDNs y workers, ábrelo mediante un servidor local (no con `file://`):

```bash
python3 -m http.server 8000
# abre http://localhost:8000
```

## Notas

- El OCR de tickets térmicos/fotos puede tener errores; por eso la tabla es editable.
- Formatos: JPG, PNG, WEBP, GIF y PDF (se procesa la primera página).
