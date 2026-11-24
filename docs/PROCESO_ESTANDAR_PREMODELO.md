# Proceso estándar pre-modelo — Asignación de Talento 2027

**Estado:** borrador de línea base (v0.1) para validación conjunta.
**Alcance:** todas las etapas **anteriores al motor de optimización**. El motor
(CP-SAT o MILP) queda fuera de este documento; aquí se define solo cómo llegar a
sus insumos de forma idéntica en ambos equipos.

Este documento unifica las dos implementaciones existentes (`Estrategia&Control`,
CP-SAT; `Optimizacion`, MILP) en un único proceso. Donde las dos diferían, se
eligió una opción y se explica por qué. Las decisiones que dependen de negocio
están marcadas **[A CONFIRMAR]**; el resto son decisiones técnicas ya fijadas.

---

## 0. Principios de diseño

1. **Un solo contrato de datos por etapa.** Cada etapa recibe y entrega
   estructuras con columnas y tipos fijos (ver §6). El motor nunca lee los Excel
   crudos; solo consume la salida de la etapa de validación.
2. **Las reglas de negocio viven en el prefiltrado, no en el motor.** El motor
   solo impone estructura (capacidad, composición, cobertura). Así CP-SAT y MILP
   son intercambiables sin cambiar reglas.
3. **Toda decisión de limpieza es trazable.** Cada transformación referencia un
   supuesto y se acumula en un reporte de normalización imprimible.
4. **Lo que no se puede asignar se reporta, no se descarta en silencio.**
   Personas excluidas, slots sin candidato y contradicciones de datos van a una
   salida de revisión.

---

## 1. Capas del proceso

```
  DATA1 personas (skills)   DATA2 demanda        DATA3 staff Q4
         │                       │                     │
         ▼                       ▼                     ▼
  ┌─────────────────────────────────────────────────────────┐
  │ CAPA 1 · CARGA + NORMALIZACIÓN                            │
  │   1a. Pool de personas  (staff Q4  ⨝  skills por código) │
  │   1b. Demanda / slots   (DATA2 normalizada)              │
  └─────────────────────────────────────────────────────────┘
         │ personas[]            slots[]
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ CAPA 2 · PREFILTRADO (reglas duras + score blando)       │
  │   es_elegible(persona, slot) → poda                      │
  │   score(persona, slot)       → preferencia               │
  └─────────────────────────────────────────────────────────┘
         │ candidatos[] (persona, slot, score)
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ CAPA 3 · VALIDACIÓN                                       │
  │   matriz de elegibilidad  [persona × slot]               │
  │   reporte de cobertura + causa por slot sin candidato    │
  └─────────────────────────────────────────────────────────┘
         │
         ▼
   ╔═══════════════════════════════╗
   ║  FRONTERA DEL MODELO           ║   (fuera de alcance aquí)
   ║  CP-SAT  /  MILP               ║
   ╚═══════════════════════════════╝
```

---

## 2. Capa 1 · Carga y normalización

### 2.1 Decisiones fijadas

| Tema | Decisión | Motivo |
|---|---|---|
| Lectura de Excel | **pandas** (`read_excel`) | más corto y mantenible; ya es dependencia. Se retira el parser XML propio. |
| Origen del pool | **Staff Q4 (DATA3)**; las skills de DATA1 se cruzan por `Código` | el staff define disponibilidad real; DATA1 trae ~1.600 perfiles, muchos no asignables |
| Interno/externo autoritativo | **Staff Q4**, con validación cruzada contra DATA1 que **reporta** contradicciones | el staff manda; la contradicción no se resuelve sola, se marca para revisión |
| Clasificación de pool | persona del staff sin skills en DATA1 → se excluye y se reporta; persona de DATA1 sin registro de staff → `BACKLOG` (no entra al pool activo) | conserva la trazabilidad de `Optimizacion` |
| Tiempo | fechas reales parseadas y **recortadas a Q1–Q2 2027** | más fiel a la demanda que el aplanado uniforme a 4 trimestres |

### 2.2 Normalización de personas (pool)

1. **Deduplicar por `Código`** (primera aparición). Reportar nº de duplicados.
2. **Consolidar persona presente en varias hojas del staff**: capacidad libre =
   **mínimo** entre apariciones (la más restrictiva); dirección = la de mayor peso.
3. **Skills a entero 0–4** (`0 Nulo … 4 Experto`). Celda no numérica → 0, y se
   cuenta en el reporte.
4. **Seniority** a vocabulario controlado `{Junior, Mid-Level, Senior, Lead}`;
   fuera de ese conjunto → `DESCONOCIDO`.
5. **Familias de rol que puede cubrir** la persona, vía catálogo único de mapeo
   (§4). Rol basura o no mapeado → sin familias → excluida del pool activo.
6. **Capacidad libre** por persona en FTE [0,1].
   **[A CONFIRMAR]** hoy `Estrategia&Control` la ignora (todos al 100%). Propuesta:
   usar la capacidad real; si se prefiere simplificar, dejarlo como flag explícito.
7. **Fecha de liberación**: día siguiente a la última `Fecha Fin` de staff Q4; sin
   fecha utilizable → disponible desde el inicio del horizonte.

### 2.3 Normalización de la demanda (slots)

1. **Forward-fill** de identidad del equipo/proyecto (celdas combinadas): Mesa,
   Fábrica, SDATOOL, Nombre Proyecto, fechas, Dirección, Estado.
2. Una fila con **`Rol` no vacío = un slot**.
3. **Clave de equipo** = `(Mesa, Dirección, Fábrica)`.
4. **Familia del rol del slot** vía catálogo único (§4).
5. **Interno/externo del slot** desde `Internal`/`External`; ambiguo o sin marca
   se reporta.
6. **Expansión a plazas de 1 FTE**: cada unidad de `Internal`/`External` es una
   plaza indivisible.
7. **Skills obligatorias** del slot (técnicas + funcionales); las sugeridas no
   cuentan.
8. **SDATOOL válido** solo si matchea `SDATOOL-<número>`; lo demás → sin SDA.
9. **Trimestres 2027** cubiertos por `[inicio, fin]`, recortados al horizonte.

---

## 3. Capa 2 · Prefiltrado

Dos funciones puras sobre `(persona, slot)`: `es_elegible` (poda dura) y `score`
(preferencia blanda). El prefiltrado reduce el espacio de variables y adjunta el
score; **no** decide la asignación.

### 3.1 Reglas duras (`es_elegible`) — línea base propuesta

| Regla | Dura/Blanda | Nota |
|---|---|---|
| Familia de rol compatible | **dura** | |
| LT = Lead + interno | **dura** | LT no admite sustitución de tipo |
| Interno/externo | **dura con sustitución** (salvo LT) | si falta el tipo pedido, se usa el opuesto y se **marca** la sustitución |
| Dominio ENG | **dura** | la persona debe tener ENG entre sus dominios |
| Seniority | **dura, máx. 1 nivel de diferencia** | **[A CONFIRMAR]** · además puntúa en el score |
| Skills obligatorias | **≥1 registrada = dura** | **[A CONFIRMAR]** · el resto puntúa; el nivel no filtra |
| Fecha de liberación | **dura** | la persona debe estar libre al inicio del slot |

Orden de evaluación recomendado (barato → caro): familia → int/ext → dominio →
seniority → liberación → skills.

### 3.2 Score blando — **[A CONFIRMAR: lexicográfico vs. ponderado]**

Recomendación de línea base: **orden lexicográfico**

```
continuidad  >  dominio  >  nº skills obligatorias cubiertas  >  ajuste de seniority
```

Motivos: el motor puede resolverlo por etapas sin que una preferencia blanda
compense otra, y es más explicable a negocio. La alternativa (fit continuo
ponderado `0.8·skills + 0.2·seniority + bonus_continuidad`) es válida pero mezcla
dimensiones en un solo número. **Hay que elegir una; no se combinan.**

Definiciones comunes a ambas opciones:
- **continuidad**: la persona ya venía en un SDA/Mesa del equipo del slot.
- **dominio**: afinidad de dominio persona↔slot.
- **skills cubiertas**: nº de skills obligatorias del slot que la persona posee
  (nivel ≥ 1). El nivel no suma puntos extra en la opción lexicográfica.
- **ajuste de seniority**: exacto > superior > inferior.

---

## 4. Catálogo único de roles (compartido)

Fuente única de verdad para mapear roles. Reemplaza los dos mapeos separados.
Las familias de asignación son **exactamente tres: LT, DEV, QA**. Tanto la
persona como el slot se homologan a **una sola familia** (no un conjunto).

**Rol de slot → familia única:** `LT`, `Product Engineer (LT-IA)`, `Líder
Técnico`, `PO` → `LT`; `QA`, `Quality & Context`, `Testing` → `QA`;
`Dev Int/Ext`, `Desarrollador`, `Arquitecto`, `Despliegues`, `Data Ing`,
`UX` → `DEV`.

**Rol de persona → familia única** (decisión 24-nov con Optimizacion):
- Tech Manager / Líder / Service Reliability Lead / Líder Primera Línea / PTL → `LT`
- QA / Testing / Tester → `QA`
- Desarrollador / Developer / Arquitecto / Arquitectura / Despliegues / Data Ing → `DEV`
- **No se infiere LT por seniority Lead.**
- Rol nulo / `NA…` / `cod eliminado` → sin familia.
- **Cualquier rol que no caiga en LT/DEV/QA NO se descarta en silencio**: se
  reporta en `revision_personas.csv` con el rol crudo para corregirlo en origen.

> La nueva data de personas debe traer el rol ya normalizado a LT/DEV/QA. El
> mapeo anterior tolera roles sueltos conocidos mientras llega esa data.

---

## 5. Capa 3 · Validación

1. **Matriz de elegibilidad** booleana `[persona × slot]` a partir de los
   candidatos viables.
2. **Reporte de cobertura por slot**: nº de candidatos viables, `cubrible`
   (sí/no).
3. **Causa por slot sin candidato**: primer criterio que lo deja vacío
   (rol / seniority / tipo / dominio / skills / liberación).
4. **Resumen**: slots totales, cubribles, sin candidato, con el detalle de estos
   últimos.

Esta capa es un entregable de valor por sí misma (dice qué demanda es imposible
de cubrir y por qué) y es el **único insumo del motor**.

---

## 6. Contrato de datos entre etapas

### `personas` (salida de Capa 1a)
| columna | tipo | descripción |
|---|---|---|
| `codigo` | str | id único |
| `nombre` | str | |
| `direccion` | str | dirección de mayor peso |
| `es_interno` | bool | **autoritativo** (staff Q4) |
| `seniority` | enum | `{Junior, Mid-Level, Senior, Lead, DESCONOCIDO}` |
| `familia` | enum | **una** de `{LT, DEV, QA}` |
| `dominio` | str | dominio único activo (p.ej. `ENG`) |
| `capacidad_libre` | float | FTE libre [0,1] |
| `release_date` | date? | fecha de liberación |
| `sdas_vigentes_2027` | frozenset | para continuidad |
| `skill::<nombre>` | int 0–4 | una columna por skill |

### `slots` (salida de Capa 1b)
| columna | tipo | descripción |
|---|---|---|
| `slot_id` | str | id de plaza (1 FTE) |
| `equipo` | str | `(Mesa, Dirección, Fábrica)` |
| `mesa` / `direccion` / `fabrica` | str | |
| `proyecto` / `sda` / `estado` | str | |
| `rol_slot` | str | |
| `familia` | enum | **una** de `{LT, DEV, QA}` |
| `dominio` | str | dominio único activo |
| `grupo_mesa_foco` | str | `(Mesa, Fábrica)` para consolidar SDA |
| `sdas_grupo` | list[str] | SDA deduplicadas del grupo (base de continuidad) |
| `seniority_req` | enum | |
| `requiere_interno` | bool | |
| `skills_obligatorias` | list[str] | vacío admitido solo para QA |
| `trimestres` | list[str] | trimestres 2027 cubiertos |

### `candidatos` (salida de Capa 2)
Lista de `(idx_persona, slot_id, score)` que pasan `es_elegible`.

### `validacion` (salida de Capa 3, insumo del modelo)
- `matriz_elegibilidad: DataFrame[bool]` `[persona × slot]`
- `cobertura: DataFrame` por slot
- `resumen_cobertura: dict`

---

## 7. Decisiones cerradas (sesión 24-nov)

Tras revisar el repo `Optimizacion` actualizado, se cerraron estas decisiones.
Todas son conmutables por flag en `procesamiento/config.py`; ningún
supuesto se eliminó, solo se fijó su valor por defecto.

| # | Tema | Decisión | Flag |
|---|---|---|---|
| 1 | Familia de rol | **una sola** `LT/DEV/QA` por persona y por slot; rol fuera de las 3 se reporta | `FAMILIAS_VALIDAS` |
| 2 | Inferencia LT por Lead | **eliminada** (como Optimizacion) | — |
| 3 | Dominio | **único por corrida, configurable**; no multidominio; falla si la demanda trae >1 | `DOMINIO_ASIGNACION` |
| 4 | QA sin skills | **permitido** (slot QA sin skills tiene candidatos por rol+seniority) | `QA_SIN_SKILLS_OK` |
| 5 | SDA | **consolidada por Mesa+Foco** (lista deduplicada = base de continuidad) | — |
| 6 | Base del pool | **Staff Q4** (enriquecido con skills de DATA1) | — |

Decisiones previas que se mantienen: seniority dura (máx. 1 nivel,
`SENIORITY_DURA`), skills obligatorias ≥1 duras salvo QA
(`SKILLS_MIN_OBLIGATORIAS`), scoring lexicográfico (`MODO_SCORE`), interno/externo
autoritativo = Staff Q4.

### Pendiente real
- **Capacidad**: hoy uniforme al 100% (`CAPACIDAD_UNIFORME=True`), heredado de
  ambos equipos. Cambiar a capacidad real cuando se valide la calidad de DATA3.
- **Nueva data de personas** (roles ya normalizados a LT/DEV/QA): al subirla,
  reejecutar el pipeline; el reporte de "rol fuera de LT/DEV/QA" debe quedar vacío.

El proceso queda cerrado para implementación. El motor (CP-SAT/MILP) se conecta
detrás de la Capa 3 sin tocar reglas.
