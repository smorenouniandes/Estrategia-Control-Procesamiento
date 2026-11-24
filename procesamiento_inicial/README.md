# procesamiento_inicial — Golden Set compartido

Pipeline único de **carga → normalización → prefiltrado → validación** que
produce el **golden set**: el conjunto de datos estandarizado que consumen por
igual el modelo CP-SAT (`Estrategia&Control`) y el modelo MILP (`Optimizacion`).

Implementa el proceso descrito en `../PROCESO_ESTANDAR_PREMODELO.md`.

## Datos y golden set (importante al clonar)

Este repositorio contiene **solo código y documentación**. Por tratarse de datos
reales de personas del banco, **no se versionan**:

- los Excel de origen, que van en `Data/` (`Data/DATA1_personas.xlsx`,
  `Data/DATA2_demanda.xlsx`, `Data/DATA3_staffq4.xlsx`), y
- el `golden_set/` generado (contiene códigos y nombres reales).

Ambos están excluidos en `.gitignore`. Quien clone el repo **no encontrará** el
golden set: lo **regenera** localmente. Los Excel se comparten por un canal
seguro aparte (no por git).

### Pasos para generar el golden set tras clonar

```bash
git clone <URL_DEL_REPO>
cd Estrategia-Control-Procesamiento      # raíz donde está el paquete
pip install -r procesamiento_inicial/requirements.txt

# Deja los tres Excel en la carpeta Data/ (ya existe en el repo):
#   Data/DATA1_personas.xlsx · Data/DATA2_demanda.xlsx · Data/DATA3_staffq4.xlsx
# El pipeline los busca por patrón de nombre (DATA1*, DATA2*, DATA3*), así que
# toleran sufijos de versión.

python -m procesamiento_inicial.run      # crea procesamiento_inicial/golden_set/
```

El pipeline es reproducible: mismos Excel + mismos flags de `config.py` ⇒ mismo
golden set. Por eso basta versionar el código.

## Ejecución

```bash
pip install -r requirements.txt
python -m procesamiento_inicial.run          # desde la raíz del workspace
# o
cd procesamiento_inicial && python run.py
```

Lee los Excel de la carpeta `Data/` (`Data/DATA1_personas.xlsx`,
`Data/DATA2_demanda.xlsx`, `Data/DATA3_staffq4.xlsx`) y escribe el golden set en
`procesamiento_inicial/golden_set/`.

## Qué produce (golden set)

Todo en **CSV**, separado en dos subcarpetas según su uso:

```
golden_set/
├── modelo/        ← ENTRADA de los modelos (CP-SAT / MILP)
│   ├── personas.csv     pool normalizado, 1 fila = 1 persona
│   ├── slots.csv        demanda normalizada, 1 fila = 1 plaza (1 FTE)
│   └── candidatos.csv   pares viables (persona, slot) + score  ← insumo principal
└── reportes/      ← AUDITORÍA para humanos (no entran al modelo)
    ├── cobertura.csv            cobertura y causa por slot
    ├── resumen.json             metadatos, parámetros, resumen de cobertura
    ├── revision_personas.csv    personas excluidas con motivo
    └── reporte_normalizacion.txt  traza de todas las transformaciones
```

- `modelo/` es lo que un modelo necesita para construir variables y objetivo.
  `candidatos.csv` ya es el conjunto filtrado de pares elegibles con su `score`.
- `reportes/` es diagnóstico y trazabilidad; ningún modelo lo lee.
- Las columnas de lista (`skills_obligatorias`, `trimestres`, `sdas_grupo`,
  `sdas_vigentes_2027`) se serializan como JSON dentro de la celda en los CSV.

## Cómo lo consume cada modelo

```python
from procesamiento_inicial.golden import cargar_golden_set

gs = cargar_golden_set("procesamiento_inicial/golden_set")
gs.personas      # DataFrame  (modelo/personas.csv)
gs.slots         # DataFrame  (modelo/slots.csv)
gs.candidatos    # DataFrame  (modelo/candidatos.csv) — insumo principal
gs.cobertura     # DataFrame  (reportes/cobertura.csv)
gs.resumen       # dict       (reportes/resumen.json)
```

Para asignar, un modelo usa **`candidatos`** (define las variables `x[p,s]` y
trae el `score`) y **`slots`**/**`personas`** para las restricciones. `cobertura`
y `resumen` son informativos.

Ambos modelos arrancan desde `gs` y solo difieren a partir de la frontera del
modelo (CP-SAT / MILP).

## Parámetros (línea base, ver `config.py`)

Las decisiones del proceso están expuestas como flags para afinarlas sin tocar
la lógica (valores por defecto = decisiones de la sesión 24-nov):

- `DOMINIO_ASIGNACION` (str) — dominio único de la corrida; no multidominio.
- `QA_SIN_SKILLS_OK` (bool) — un slot QA puede no declarar skills obligatorias.
- `SENIORITY_DURA` (bool) — seniority como filtro duro (máx. 1 nivel).
- `SKILLS_MIN_OBLIGATORIAS` (int) — mínimo de skills obligatorias (no aplica a QA).
- `MODO_SCORE` (`"lexicografico" | "ponderado"`).
- `CAPACIDAD_UNIFORME` (bool) — ignorar capacidad real (hoy True).
- `SUSTITUCION_INT_EXT` (bool) — permitir tipo opuesto salvo LT.

**Familias de asignación:** exactamente tres (`LT`, `DEV`, `QA`), una por persona
y por slot. No se infiere LT por seniority. Un rol de persona que no caiga en
esas tres no se descarta en silencio: se reporta en `revision_personas.csv`.
