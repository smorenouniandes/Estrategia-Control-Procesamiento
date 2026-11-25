# Contexto del proyecto — para retomar en futuras sesiones

> Documento de handoff. Léelo primero para continuar el trabajo sin perder
> contexto. Resume qué es el proyecto, qué está hecho, cómo está organizado y qué
> queda pendiente. Las decisiones de diseño están en `DECISIONES.md`; el detalle
> técnico en `docs/`.

## 1. Qué es este proyecto

Es la **etapa de procesamiento** de un sistema de asignación de talento a proyectos
2027. Toma tres bases crudas (personas+skills, demanda de plazas, staff disponible)
y produce un **golden set**: un dataset estandarizado y trazable que consumen por
igual dos modelos de optimización construidos por dos personas distintas:

- **CP-SAT** (OR-Tools) — repo/trabajo "Estrategia & Control".
- **MILP** (SciPy/HiGHS) — repo/trabajo "Optimización".

Este repositorio contiene **solo la etapa previa a los modelos**. Los motores de
optimización están fuera de alcance aquí.

**Frontera clave:** el procesamiento define **quién PUEDE** ir en cada plaza
(elegibilidad). Los modelos deciden **a QUIÉN** se asigna (asignación). Esa línea
no se cruza: las reglas de composición/optimización no viven en este repo.

## 2. Por qué existe (el problema que resuelve)

Las dos personas tenían pipelines de procesamiento distintos, lo que haría que sus
modelos partieran de universos de elegibilidad diferentes. Este repo **unifica** ese
procesamiento en una sola fuente de verdad, para que ambos modelos trabajen sobre
exactamente los mismos candidatos.

## 3. Estado actual (hecho)

- Pipeline completo y funcional: carga/normalización → prefiltrado → validación.
- Golden set reproducible en CSV, separado en `golden_set/modelo/` (entrada de los
  modelos) y `golden_set/reportes/` (auditoría).
- Insumos centralizados en `Data/` (búsqueda por patrón `DATA1*`/`DATA2*`/`DATA3*`).
- Dominio único con validación de coincidencia oferta↔demanda.
- Documentación: E2E, arquitectura con diagramas, proceso estándar, decisiones.
- Repo en GitHub, con datos sensibles excluidos por `.gitignore`.

**Cifras de la última corrida (data real):** 370 staff → 190 personas asignables ·
120 plazas · 3.708 candidatos viables (reducción 83,7%) · 89/120 plazas cubribles
(31 sin candidato por familia: faltan LT y QA en el pool).

## 4. Estructura del repositorio

```
├── README.md                 bienvenida + estructura + uso
├── DECISIONES.md             D1–D12, decisiones de diseño (conmutables por flag)
├── CONTEXTO_PROYECTO.md      este archivo
├── requirements.txt          pandas, openpyxl
├── Data/                     INSUMOS (3 Excel, ignorados por git)
├── procesamiento/            CÓDIGO (paquete Python)
│   ├── config.py   carga.py   prefiltrado.py   validacion.py
│   ├── tiempo.py   golden.py  run.py
├── docs/                     documentación + diagramas + proceso estándar
└── golden_set/               SALIDA (ignorada; se regenera)
    ├── modelo/     personas.csv · slots.csv · candidatos.csv
    └── reportes/   cobertura.csv · resumen.json · revision_personas.csv · reporte_normalizacion.txt
```

## 5. Las tres capas (resumen)

1. **Carga/normalización** (`carga.py`): pool = Staff Q4 ⨝ skills de DATA1 por
   `Código`; demanda DATA2 → plazas de 1 FTE; un solo dominio.
2. **Prefiltrado** (`prefiltrado.py`): `es_elegible()` aplica las reglas duras
   (familia, LT, dominio, seniority, skills, int/ext, liberación); `score()` calcula
   la preferencia blanda.
3. **Validación** (`validacion.py`): matriz de elegibilidad + cobertura con causa
   por plaza. Es el insumo del motor.

## 6. Reglas: dónde están y cómo se clasifican

- **Elegibilidad** (duras, en el procesamiento) → `prefiltrado.py::es_elegible`.
- **Normalización** (limpieza del dato) → `carga.py`.
- **Asignación** (composición/optimización) → NO están aquí; son del motor.
- **Fuente de negocio** (las 10 reglas originales) → ver `DECISIONES.md`, que mapea
  cada decisión de diseño a su regla.

## 7. Parámetros actuales (`procesamiento/config.py`)

| flag | valor | significado |
|---|---|---|
| `DOMINIO_ASIGNACION` | `"ENG"` | dominio único de la corrida |
| `QA_SIN_SKILLS_OK` | `True` | slot QA sin skills admite candidatos |
| `SENIORITY_DURA` | `True` | seniority filtro duro (±1 nivel) |
| `SKILLS_MIN_OBLIGATORIAS` | `1` | mínimo de skills (no aplica a QA) |
| `MODO_SCORE` | `"lexicografico"` | criterio del score |
| `CAPACIDAD_UNIFORME` | `True` | ignora capacidad real (todos 100%) |
| `SUSTITUCION_INT_EXT` | `True` | permite tipo opuesto salvo LT |

Cambiar una decisión = cambiar un flag y reejecutar. Ningún supuesto se elimina.

## 8. Cómo ejecutar

```bash
pip install -r requirements.txt
# dejar los 3 Excel en Data/ (DATA1*/DATA2*/DATA3*)
python -m procesamiento.run        # genera golden_set/
```

## 9. Pendientes / decisiones abiertas

- **Capacidad real**: hoy uniforme al 100% (`CAPACIDAD_UNIFORME=True`). Pasar a
  capacidad real cuando se valide la calidad de DATA3.
- **Nueva data de personas** con roles ya normalizados a LT/DEV/QA: al subirla,
  `golden_set/reportes/revision_personas.csv` no debería tener filas de
  "rol fuera de LT/DEV/QA".
- **Multidominio**: hoy descartado por decisión (un dominio por corrida). Si en el
  futuro se asignan varios dominios juntos, hay que reabrir D4.

## 10. Forma de trabajo acordada (importante para continuar)

- **Validar la data primero.** Antes de modelar, revisar que las bases presentes
  sean consistentes (columnas, llaves de cruce `Código`/`SDATOOL`, rangos de skills,
  dominio). Reportar discrepancias; no rellenar en silencio.
- **Separar hard y soft.** Lo duro (qué es posible) vive en el prefiltrado; lo
  blando (qué es preferible) en el score. El golden set no impone reglas de
  asignación.
- **Datos sensibles nunca a git.** Los Excel y el golden set contienen datos reales
  de personas; están en `.gitignore`. Compartirlos solo por canal seguro.
- **Ante ambigüedad, preguntar** antes de codear; usar un supuesto y declararlo.

## 11. Repositorio

`https://github.com/smorenouniandes/Estrategia-Control-Procesamiento` · rama `main`.
