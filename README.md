# Procesador de facturas

Script de línea de comandos que lee facturas en **PDF** e **imagen** (JPG/PNG),
extrae automáticamente los datos con IA (modelo Claude) y los vuelca a un
**Excel** y un **CSV**.

Campos que extrae por factura:

- **Comercio** (nombre del comercio/emisor, p.ej. FARMATODO, C.A.)
- **RIF del comercio** (RIF de la empresa emisora, formato J-xxxxxxxx)
- **Cédula o RIF** (del cliente/receptor)
- **Nombre o Razón Social** (del cliente/receptor)
- **Fecha y hora**
- **Número de factura**
- **IVA**
- **Monto total**
- **Base** (calculada: `Base = Monto total − IVA`)

Se puede usar de dos formas: como **script de línea de comandos** o como
**interfaz web** (subiendo las facturas desde el navegador).

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate   # opcional, recomendado
pip install -r requirements.txt
```

## Configurar la clave de API

El script usa la API de Claude, así que necesitas una clave de Anthropic:

```bash
export ANTHROPIC_API_KEY="tu-api-key"
```

(También funciona con `ant auth login` si tienes la CLI de Anthropic.)

## Uso: interfaz web

```bash
python app.py
# abre http://127.0.0.1:5000 en el navegador
```

Arrastra una o varias facturas, procésalas y verás los datos en una tabla.
Desde ahí puedes descargar el Excel o el CSV.

> Es un servidor local para un solo usuario, sin autenticación; no lo expongas
> a Internet tal cual.

## Uso: línea de comandos

```bash
# Procesa todas las facturas de una carpeta
python procesar_facturas.py ./mis_facturas

# Especificar el archivo Excel de salida
python procesar_facturas.py ./mis_facturas -o resultados.xlsx
```

Genera dos archivos:

- `facturas_procesadas.xlsx` — con dos hojas:
  - **Resumen**: una fila por factura.
  - **Conceptos**: una fila por partida/línea.
- `facturas_procesadas.csv` — el resumen en CSV (útil para importar a otros sistemas).

## Notas

- Formatos soportados: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`.
- Si un campo no aparece en la factura, se deja vacío (el script no inventa datos).
- Si una factura falla, el script lo reporta y continúa con las demás.
- El coste depende del número y tamaño de las facturas (se paga por tokens de la API).
