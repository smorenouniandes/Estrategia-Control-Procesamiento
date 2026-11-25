# Documentación técnica E2E — Procesamiento inicial y Golden Set

**Proyecto:** Asignación de Talento 2027
**Componente:** `procesamiento/` — pipeline previo al modelo de optimización
**Salida:** *golden set*, dataset estandarizado que consumen por igual el modelo
CP-SAT (`Estrategia&Control`) y el modelo MILP (`Optimizacion`).
**Alcance:** desde los tres Excel de origen hasta el golden set. El motor de
optimización queda fuera.

Documento de referencia de decisiones de negocio: `../PROCESO_ESTANDAR_PREMODELO.md`.

---

## 1. Visión general

El pipeline convierte tres bases crudas (personas con skills, demanda de plazas,
staff disponible) en un conjunto de artefactos limpios, trazables y reproducibles.
Un solo comando ejecuta las tres capas en orden y escribe el golden set.

```
 ENTRADA (Excel)                PIPELINE (3 capas)                SALIDA (golden set)
 ───────────────                ──────────────────                ───────────────────
 DATA1_personas.xlsx ─┐
 DATA2_demanda.xlsx  ─┼──▶  1. Carga + Normalización  ──▶  personas · slots
 DATA3_staffq4.xlsx  ─┘           (carga.py)
                                      │
                                      ▼
                            2. Prefiltrado            ──▶  candidatos (+score)
                               (prefiltrado.py)
                                      │
                                      ▼
                            3. Validación             ──▶  matriz · cobertura · resumen
                               (validacion.py)
                                      │
                                      ▼
                            Serialización (CSV)       ──▶  modelo/ + reportes/
                               (golden.py)
```

**Principios** (detallados en el proceso estándar):
1. Un contrato de datos fijo por etapa.
2. Reglas de negocio en el prefiltrado, nunca en el motor.
3. Toda transformación es trazable (reporte de normalización).
4. Lo no asignable se reporta, no se descarta en silencio.

**Reproducibilidad:** el resultado depende solo de (a) los tres Excel de entrada
y (b) los parámetros de `config.py`. El `resumen.json` registra ambos, de modo que
cualquier golden set es rastreable a sus insumos y a su configuración.

---

## 2. Bases de entrada y su esquema

Las tres bases viven en la carpeta `Data/` del repo (se buscan por patrón de
nombre `DATA1*`/`DATA2*`/`DATA3*`). Son Excel crudos de negocio: cabeceras en la
segunda fila, celdas combinadas, columnas sucias y mezcla de tipos.

### 2.1 `DATA1_personas.xlsx` — hoja `Hoja 1`
Catálogo de ~1.680 perfiles con su matriz de skills. **Tabla de consulta por
`Código`**, no es el pool.

- **Estructura:** fila 0 = banner; **fila 1 = nombres de columna**; fila 2+ = datos.
- **160 columnas.** Las 6 primeras son identidad; las ~153 siguientes son skills.

| # | Columna | Uso en el pipeline |
|---|---|---|
| 0 | `Código` | clave de cruce con el staff |
| 1 | `Nombre` | informativo |
| 2 | `Tipo de Recurso` | validación cruzada int/ext (no autoritativa) |
| 3 | `Empresa` | no usado |
| 4 | `Rol Principal` | → **familia** LT/DEV/QA |
| 5 | `Nivel del Rol Actual` | → **seniority** normalizado |
| 6–158 | `Java`, `Python`, `aso`, `cobol`, … | nivel de skill por persona |

- **Valores de skill:** etiquetas `0 - Nulo … 4 - Experto`, enteros, o texto libre.
- **Supuesto:** si un `Código` está duplicado, se conserva la **primera** aparición.

### 2.2 `DATA2_demanda.xlsx` — hoja `Hoja 1`
Demanda de plazas por proyecto/mesa. Cada fila con `Rol` es una necesidad; las
columnas `Internal`/`External` indican cuántos FTE de cada tipo pide.

- **Estructura:** fila 0 = banner; **fila 1 = nombres**; fila 2+ = datos.
- **Celdas combinadas:** la identidad de proyecto (Mesa, Fábrica, fechas…) aparece
  una sola vez y se arrastra hacia abajo (forward-fill).

| Columna | Uso |
|---|---|
| `Mesa` | identidad de equipo / grupo |
| `Foco estratégico (Fábrica)` | identidad de equipo / grupo |
| `SDATOOL` | SDA del proyecto (continuidad) |
| `Nombre Proyecto` | informativo |
| `Fecha Inicio`, `Fecha Fin` | ventana temporal → trimestres 2027 |
| `Dirección` | identidad de equipo; dominio |
| `Estado` | `Stock`/`Flow` (lo sucio → `Flow`) |
| `Internal`, `External` | nº de plazas de cada tipo → expansión a slots |
| `Rol` | → **familia** del slot |
| `Seniority` | seniority requerido |
| `Habilidades técnicas obligatorias 1..5` | skills duras del slot |
| `Habilidades funcionales obligatorias 1..5` | skills duras del slot |
| `Habilidades sugerida 1..3` | **no** se usan |
| `Nivel general skills técnicos`, `Nivel IA` | **no** se usan |

### 2.3 `DATA3_staffq4.xlsx` — 3 hojas = **POOL** de personas disponibles
Staff del Q4 por dirección. Las tres hojas tienen **esquemas distintos** y se
homologan a un esquema común. Es la fuente de verdad de quién está disponible y de
su tipo interno/externo.

| Hoja | Clave | Interno/ext | Capacidad | Modo |
|---|---|---|---|---|
| `Staff System` | `Código` | `Interno` | `% Dedicación` | compromiso |
| `Staff Data` | `Codigo` | `Interno/ Externo` | `% Total x usuario` | disponible |
| `Staff Arquitectura` | `Código` | `Interno` | `% Dedicación` | compromiso |

- **Modo `compromiso`:** la columna es la dedicación ya ocupada → libre = 1 − Σ.
- **Modo `disponible`:** la columna ya es la disponibilidad → libre = valor.
- Solo `Staff System` trae `Proyecto` + `Fecha Fin Actual`, usados para continuidad
  (SDA vigente 2027) y fecha de liberación.
- El mapeo exacto de columnas por hoja vive en `config.STAFF_HOJAS`.

---

## 3. Capa 1 · Carga y normalización (`carga.py`)

**Objetivo:** producir dos tablas limpias, `personas` y `slots`, con tipos fijos.
**Entrada:** los tres Excel. **Salida:** `personas` (DataFrame), `slots` (DataFrame),
y un objeto `Reporte` con la traza y la lista de revisión.

### 3.1 Construcción del pool de personas

Tres pasos encadenados:

**(a) `cargar_staff(rep)` — POOL base desde DATA3.**
- Lee las 3 hojas, homologa columnas, calcula capacidad libre por hoja según su modo.
- **Consolida** persona presente en varias hojas: capacidad = **mínimo** (la más
  restrictiva); dirección = la de mayor peso.
- Deriva `es_interno` (autoritativo), `dominio` (único de la corrida),
  `sdas_vigentes_2027` y `release_date`.
- Si `CAPACIDAD_UNIFORME=True`, fija toda capacidad a 1.0.
- *Salida:* 1 fila por persona del staff (hoy 370).

**(b) `cargar_skills(rep)` — tabla de consulta desde DATA1.**
- Normaliza skills a entero 0–4, seniority a vocabulario controlado, y
  `Rol Principal` → **familia única** LT/DEV/QA (`familia_persona`).
- Deduplica por `Código`.
- *Salida:* 1 fila por perfil único (hoy 1.677), con 153 columnas `skill::<nombre>`.

**(c) `construir_pool(staff, skills, rep)` — cruce `staff ⨝ skills` por `codigo`.**
- *left join* del staff con las skills.
- **Excluye y reporta** (no descarta en silencio):
  - staff sin perfil en DATA1 (no hay skills → inservible);
  - persona con rol fuera de LT/DEV/QA (se registra el rol crudo).
- Valida cruzada int/ext (staff manda; la discrepancia se reporta).
- *Salida:* `personas` (hoy 190).

### 3.2 Construcción de los slots (`cargar_slots(rep)`)

- Forward-fill de identidad de proyecto (celdas combinadas).
- Una fila con `Rol` = una necesidad; `Rol` → **familia** del slot.
- **Dominio único (coincidencia real oferta↔demanda):** el dominio de las
  personas se lee del dato real del staff (DATA3, columna `Dominio`); el de los
  slots es `DOMINIO_ASIGNACION` (DATA2 no trae dominio). El pipeline exige que el
  dominio del staff sea único y **coincida** con `DOMINIO_ASIGNACION`; si no,
  aborta. El filtro de dominio en el prefiltrado descarta (y reporta) a quien no
  coincida.
- **SDA consolidada por grupo `(Mesa, Fábrica)`:** `sdas_grupo` = conjunto
  deduplicado de SDA válidas del grupo (base de la continuidad).
- Skills obligatorias = técnicas + funcionales no vacías; sugeridas descartadas.
- Ventana `[inicio, fin]` → lista de `trimestres` de 2027 (recortada).
- **Expansión a plazas de 1 FTE:** por cada unidad en `Internal`/`External` se crea
  un `slot_id` con `requiere_interno` True/False.
- *Salida:* `slots` (hoy 120 plazas desde 114 filas de demanda).

### 3.3 Reglas de normalización aplicadas

| Campo | Regla |
|---|---|
| skill | etiqueta/num → 0–4; no parseable → 0 |
| seniority | `{Junior, Mid-Level, Senior, Lead}`; otro → `DESCONOCIDO` |
| familia persona | una de LT/DEV/QA; sin mapeo → reporte (no se infiere LT por Lead) |
| int/ext | autoritativo = Staff Q4 |
| dominio persona | dato real del staff (DATA3); debe coincidir con el de la corrida |
| estado slot | `Stock`/`Flow`; sucio → `Flow` |
| SDA | solo `SDATOOL-<n>` válido |
| capacidad | mínimo entre hojas; uniforme 100% si el flag está activo |
| tiempo | trimestres 2027, recortado; sin fecha → los 4 trimestres |

---

## 4. Capa 2 · Prefiltrado (`prefiltrado.py`)

**Objetivo:** reducir el espacio de decisión y puntuar la preferencia.
**Entrada:** `personas`, `slots`. **Salida:** lista `candidatos` + reporte de poda.

### 4.1 Reglas duras — `es_elegible(persona, slot) → (bool, causa)`

Se evalúan en orden barato→caro; la primera que falla da la causa de rechazo:

1. **slot sin familia** → descarta el slot.
2. **dominio** — persona y slot deben coincidir en el dominio activo.
3. **familia** — la familia única de la persona debe ser la del slot.
   - **LT**: además exige persona de familia LT, **Lead**, **interna**, y slot
     interno (LT no admite sustitución de tipo).
   - **DEV/QA**: si el tipo int/ext no coincide, pasa solo si `SUSTITUCION_INT_EXT`
     (se marca la sustitución); si no, se rechaza.
4. **seniority** (si `SENIORITY_DURA`) — máx. 1 nivel de diferencia; sin dato rechaza.
5. **skills** — ≥ `SKILLS_MIN_OBLIGATORIAS` registradas. **Excepción QA:** un slot
   QA sin skills declaradas pasa (si `QA_SIN_SKILLS_OK`).
6. **liberación** — la persona debe estar libre al inicio del slot.

### 4.2 Score blando — `score(persona, slot) → dict`

Expone **todas las componentes crudas** (para que cada motor arme su criterio) más
un escalar `score` listo para ordenar. Según `MODO_SCORE`:

- **`lexicografico`** (por defecto): `continuidad > dominio > nº skills cubiertas >
  ajuste seniority`, con pesos posicionales amplios para no mezclar niveles.
- **`ponderado`**: `0.8·fit_skills + 0.2·fit_seniority + bonus_continuidad`.

Componentes: `continuidad`, `dominio`, `n_skills_cubiertas`, `n_obligatorias`,
`seniority_match`, `sustitucion_int_ext`.

### 4.3 Salida

`construir_candidatos` devuelve la lista de candidatos viables (un dict por par
`persona×slot` elegible) y un `reporte` con: combinaciones posibles vs. viables,
% de reducción, candidatos por slot, **causa por slot** y slots sin candidato.

*Corrida actual:* 22.800 combinaciones posibles → 3.708 viables (**reducción 83,7%**).

---

## 5. Capa 3 · Validación (`validacion.py`)

**Objetivo:** formalizar la elegibilidad como insumo del motor y entregar el
diagnóstico de cobertura. **Entrada:** `candidatos`, `personas`, `slots`, reporte de
poda. **Salida:** matriz, cobertura, resumen.

- **`matriz_elegibilidad`** → `DataFrame[bool]` `[código persona × slot_id]`. Se
  calcula en memoria para el resumen; **no se escribe como archivo** (es
  equivalente a `candidatos`).
- **`reporte_cobertura`** → por slot: `n_candidatos`, `cubrible`,
  `causa_sin_candidato` (la causa dominante de rechazo).
- **`resumen_cobertura`** → totales, cubribles, sin candidato, causas agregadas y
  detalle de los no cubribles.

Esta capa es un **entregable de valor**: dice qué demanda es imposible de cubrir y
por qué, antes de optimizar.

*Corrida actual:* 89/120 slots cubribles; 31 sin candidato por `familia` (20 LT,
11 QA), reflejo de que el pool LT real (8 Lead internos) no alcanza para 31 slots LT.

---

## 6. Serialización del golden set (`golden.py`)

**Entrada:** las estructuras de las tres capas. **Salida:** artefactos en
`golden_set/`, todo en **CSV**, separados en dos subcarpetas según su uso:

```
golden_set/
├── modelo/     entrada de los modelos (personas, slots, candidatos)
└── reportes/   auditoría para humanos (cobertura, resumen, revisión, traza)
```

Las columnas de lista (`skills_obligatorias`, `trimestres`, `sdas_grupo`,
`sdas_vigentes_2027`) se serializan como JSON dentro de la celda.
`cargar_golden_set()` reconstruye las tablas y re-parsea esas columnas.

---

## 7. Artefactos del golden set

| Archivo | Carpeta | Uso | Contenido |
|---|---|---|---|
| `personas.csv` | `modelo/` | entrada modelo | pool normalizado (1 fila = persona) |
| `slots.csv` | `modelo/` | entrada modelo | demanda normalizada (1 fila = plaza 1 FTE) |
| `candidatos.csv` | `modelo/` | **entrada principal** | pares viables con score y componentes |
| `cobertura.csv` | `reportes/` | auditoría | cobertura y causa por slot |
| `resumen.json` | `reportes/` | auditoría | parámetros, conteos, resumen de cobertura |
| `revision_personas.csv` | `reportes/` | auditoría | excluidos con motivo |
| `reporte_normalizacion.txt` | `reportes/` | auditoría | traza de transformaciones |

> La matriz de elegibilidad `[persona × slot]` **no se materializa** como archivo:
> es equivalente a `candidatos` (misma relación en forma booleana). Si un modelo la
> necesita, la reconstruye en memoria a partir de `candidatos`.

### 7.1 Esquema de `personas`

| columna | tipo | descripción |
|---|---|---|
| `codigo` | str | id único (clave) |
| `nombre` | str | |
| `direccion` | str | dirección de mayor peso (staff) |
| `empresa` | str | |
| `rol_staff` | str | rol según staff (informativo) |
| `rol_principal` | str | rol según DATA1 |
| `familia` | enum | **una** de `{LT, DEV, QA}` |
| `seniority` | enum | `{Junior, Mid-Level, Senior, Lead, DESCONOCIDO}` |
| `es_interno` | bool | **autoritativo** (staff Q4) |
| `tipo_recurso_d1` | str | tipo según DATA1 (validación cruzada) |
| `dominio` | str | dominio **real** del staff (DATA3); debe coincidir con `DOMINIO_ASIGNACION` |
| `capacidad_libre` | float | FTE libre [0,1] |
| `release_date` | date? | fecha de liberación |
| `sdas_vigentes_2027` | list[str] | para continuidad |
| `skill::<nombre>` | int 0–4 | 153 columnas, una por skill |

### 7.2 Esquema de `slots`

| columna | tipo | descripción |
|---|---|---|
| `slot_id` | str | id de plaza (1 FTE) |
| `mesa`, `direccion`, `fabrica` | str | identidad |
| `equipo` | str | `(Mesa, Dirección, Fábrica)` |
| `grupo_mesa_foco` | str | `(Mesa, Fábrica)` para consolidar SDA |
| `proyecto` | str | |
| `rol_slot` | str | rol original |
| `familia` | enum | **una** de `{LT, DEV, QA}` |
| `seniority_req` | enum | seniority pedido |
| `requiere_interno` | bool | tipo pedido |
| `dominio` | str | dominio único activo |
| `estado` | enum | `Stock`/`Flow` |
| `sda` | str? | SDA de la fila |
| `sdas_grupo` | list[str] | SDA deduplicadas del grupo (continuidad) |
| `skills_obligatorias` | list[str] | vacío admitido solo para QA |
| `fecha_inicio_orig`, `fecha_fin_orig` | str | fechas originales |
| `trimestres` | list[str] | trimestres 2027 cubiertos |

### 7.3 Esquema de `candidatos`

| columna | tipo | descripción |
|---|---|---|
| `idx_persona` | int | índice en `personas` |
| `codigo` | str | persona |
| `slot_id` | str | plaza |
| `continuidad` | 0/1 | SDA de la persona en `sdas_grupo` del slot |
| `dominio` | 0/1 | afinidad de dominio |
| `n_skills_cubiertas` | int | skills obligatorias que posee (nivel ≥1) |
| `n_obligatorias` | int | skills obligatorias del slot |
| `seniority_match` | enum | `coincide/por_encima/por_debajo/sin_dato` |
| `sustitucion_int_ext` | 0/1 | se cubrió con el tipo opuesto |
| `score` | num | escalar de preferencia (según `MODO_SCORE`) |

### 7.4 Esquema de `cobertura`

`slot_id, equipo, mesa, proyecto, rol_slot, familia, seniority_req,
requiere_interno, n_candidatos, cubrible, causa_sin_candidato`.

---

## 8. Cómo lo consume cada modelo

```python
from procesamiento.golden import cargar_golden_set

gs = cargar_golden_set("golden_set")
gs.personas     # DataFrame (modelo/personas.csv)
gs.slots        # DataFrame (modelo/slots.csv)
gs.candidatos   # DataFrame (modelo/candidatos.csv) — insumo principal
gs.cobertura    # DataFrame (reportes/cobertura.csv) — informativo
gs.resumen      # dict      (reportes/resumen.json) — informativo
```

Ambos modelos arrancan desde `gs` y solo divergen a partir de la frontera del
modelo. Las variables de decisión del motor se construyen sobre `gs.candidatos`;
ninguno vuelve a leer los Excel ni re-aplica reglas.

### 8.1 Contrato de uso del golden set (obligatorio para ambos modelos)

El golden set es la **única fuente de verdad** de la elegibilidad. Para que
CP-SAT y MILP optimicen sobre exactamente el mismo universo, ambos deben cumplir:

1. **Ningún modelo re-aplica reglas de elegibilidad.** `candidatos` ya es el
   resultado de aplicar todas las reglas duras (familia, LT, dominio, seniority,
   skills, int/ext, liberación). El motor lo trata como verdad dada; no vuelve a
   filtrar por rol, dominio, seniority ni skills.
2. **Ningún modelo lee los Excel de origen** ni recalcula normalizaciones. Solo
   consume los CSV de `golden_set/modelo/`.
3. **La elegibilidad vive en `candidatos`.** Es la lista de pares viables
   `(persona, slot)` con sus componentes de score, lista para construir las
   variables de decisión. Si un modelo prefiere una matriz booleana
   `[persona × slot]`, la deriva en memoria desde `candidatos`; no es un artefacto.
4. **Las preferencias blandas no son reglas.** El `score` y sus componentes
   (continuidad, dominio, skills, seniority) son insumos que el motor pondera en
   su objetivo; no filtran. Cada motor decide cómo usarlos.
5. **Las reglas de estructura/composición son del motor**, no del golden set:
   capacidad, máximo de proyectos simultáneos, 1 LT por equipo, tope de FTE por
   mesa, equilibrio interno/externo, maximización de cobertura. El golden set no
   las impone.

> En `Optimizacion`, la elegibilidad se recalcula dentro del solver
> (`eligibility()` en `asignacion_milp.py`) y la matriz de viabilidad es un
> parámetro **interno y opcional** del modelo, no un artefacto. Al promoverla al
> procesamiento, deja de ser responsabilidad del motor: pasa a ser insumo común.

---

## 9. Parámetros de configuración (`config.py`)

| parámetro | valor por defecto | efecto |
|---|---|---|
| `DOMINIO_ASIGNACION` | `"ENG"` | dominio único de la corrida (no multidominio) |
| `QA_SIN_SKILLS_OK` | `True` | slot QA sin skills tiene candidatos |
| `SENIORITY_DURA` | `True` | seniority filtro duro (±1 nivel) |
| `SKILLS_MIN_OBLIGATORIAS` | `1` | mínimo de skills (no aplica a QA) |
| `MODO_SCORE` | `"lexicografico"` | criterio del score |
| `CAPACIDAD_UNIFORME` | `True` | ignora capacidad real (todos 100%) |
| `SUSTITUCION_INT_EXT` | `True` | permite tipo opuesto salvo LT |

Cambiar una decisión de negocio = cambiar un flag y reejecutar. Ningún supuesto se
elimina del código; solo se conmuta su valor.

---

## 10. Ejecución y reproducibilidad

```bash
pip install -r requirements.txt   # pandas, openpyxl
python -m procesamiento.run                     # desde la raíz del repo
```

- Lee los tres Excel de `Data/` (por patrón de nombre `DATA1*`/`DATA2*`/`DATA3*`;
  si falta alguno, aborta con un mensaje claro) y escribe `golden_set/` en la raíz
  del repo.
- El `resumen.json` sella entrada (conteos) y configuración (parámetros), de modo
  que un golden set es reproducible: mismos Excel + mismos flags ⇒ mismo resultado.
- La ejecución imprime las tres capas y los conteos, y deja la traza completa en
  `reporte_normalizacion.txt`.

---

## 11. Trazabilidad y control de calidad

- **`revision_personas.csv`** — toda persona excluida con su motivo:
  `Sin perfil de skills en DATA1` o `Rol fuera de LT/DEV/QA: '<rol>'`.
  *Al subir la nueva data de personas (roles ya normalizados), este archivo no
  debería tener filas de "rol fuera de LT/DEV/QA".*
- **`reporte_normalizacion.txt`** — conteos de cada transformación (duplicados,
  exclusiones, familias, dominios, plazas).
- **`cobertura.csv` + `resumen.json`** — demanda no cubrible y su causa, antes de
  optimizar.

Estos tres artefactos permiten auditar por qué el golden set tiene exactamente las
personas, slots y candidatos que tiene.
