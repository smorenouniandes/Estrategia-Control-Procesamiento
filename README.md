# Estrategia-Control-Procesamiento

Etapa de **procesamiento** previa al modelo de optimización de asignación de talento
2027. Toma las tres bases crudas (personas+skills, demanda, staff) y produce el
**golden set**: el dataset estandarizado que consumen por igual el modelo CP-SAT y
el modelo MILP.

El procesamiento define **quién puede** ir en cada plaza (elegibilidad). Los modelos,
que viven fuera de este repo, deciden **a quién** se asigna.

## Estructura del repositorio

```
Estrategia-Control-Procesamiento/
├── README.md                 este archivo
├── DECISIONES.md             decisiones de diseño (conmutables por flag)
├── requirements.txt          dependencias (pandas, openpyxl)
├── Data/                     INSUMOS — los 3 Excel (ignorados por git)
│   └── .gitkeep
├── procesamiento/            CÓDIGO — paquete Python
│   ├── config.py             rutas, flags, catálogo de roles
│   ├── carga.py              Capa 1: carga y normalización
│   ├── prefiltrado.py        Capa 2: reglas de elegibilidad + score
│   ├── validacion.py         Capa 3: matriz de elegibilidad + cobertura
│   ├── tiempo.py             utilidades de trimestres/fechas
│   ├── golden.py             escribe / carga el golden set
│   └── run.py                orquestador de las 3 capas
├── docs/                     DOCUMENTACIÓN
│   ├── DOCUMENTACION_E2E.md       flujo técnico de punta a punta
│   ├── REPORTE_ARQUITECTURA.md    diagramas funcional y técnico
│   ├── PROCESO_ESTANDAR_PREMODELO.md  decisiones de proceso (conceptual)
│   ├── README_paquete.md          detalle del paquete y del golden set
│   ├── generar_diagramas.py       regenera los diagramas
│   ├── arquitectura_funcional.png
│   └── arquitectura_tecnica.png
└── golden_set/               SALIDA (ignorada por git; se regenera)
    ├── modelo/     personas.csv · slots.csv · candidatos.csv
    └── reportes/   cobertura.csv · resumen.json · revision_personas.csv · reporte_normalizacion.txt
```

## Datos (importante)

Este repo contiene **solo código y documentación**. Los Excel reales y el golden set
generado **no se versionan** (datos de personas del banco). Van en `Data/` y
`golden_set/`, ambos ignorados por git.

## Uso

```bash
pip install -r requirements.txt

# Dejar los 3 Excel en Data/ (se buscan por patrón DATA1*/DATA2*/DATA3*):
#   Data/DATA1_personas.xlsx · Data/DATA2_demanda.xlsx · Data/DATA3_staffq4.xlsx

python -m procesamiento.run      # genera golden_set/
```

La entrada de los modelos queda en `golden_set/modelo/` (`candidatos.csv` es el
insumo principal). Los archivos de `golden_set/reportes/` son auditoría.

## Más información

- **Contexto para retomar el proyecto: `CONTEXTO_PROYECTO.md`** (empieza por aquí).
- Decisiones de diseño y flags: `DECISIONES.md`.
- Flujo técnico detallado: `docs/DOCUMENTACION_E2E.md`.
- Arquitectura (diagramas): `docs/REPORTE_ARQUITECTURA.md`.
