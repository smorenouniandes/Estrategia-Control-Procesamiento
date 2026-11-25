# Reglas del sistema: filtrado vs. asignación

Consolidación de **todas** las reglas del sistema de asignación de talento 2027,
reunidas de cuatro fuentes:

- **(N)** Reglas de negocio entregadas (`Reglas.md`, 10 reglas).
- **(D)** Decisiones de diseño del procesamiento (`DECISIONES.md`, D1–D12).
- **(CP)** Reglas del modelo CP-SAT (Estrategia & Control).
- **(ML)** Reglas del modelo MILP (Optimización).

El documento tiene dos partes:
1. **Inventario completo** de reglas (sin omitir ninguna).
2. **Clasificación**: cuáles son de **filtrado** (elegibilidad, en el
   procesamiento) y cuáles de **asignación** (optimización, en el modelo).

> Definiciones.
> **Filtrado / elegibilidad:** decide si un par (persona, plaza) es *posible*.
> Produce `candidatos`. Vive en `procesamiento/` (capas carga + prefiltrado +
> validación). Es idéntico para ambos modelos.
> **Asignación:** decide, entre los pares posibles, *a quién* se asigna. Vive en
> el motor (CP-SAT o MILP). Puede diferir entre modelos.
> **Normalización:** limpieza previa del dato; es condición para el filtrado.

---

## Parte 1 · Inventario completo de reglas

### A. Reglas de negocio entregadas (N1–N10)

| # | Regla |
|---|---|
| N1 | **Población.** La base se enriquece con Staffing Q4; sin dominio o sin tipo interno/externo válido no entra al pool; roles vacíos/`NA`/fuera de catálogo se excluyen y se reportan. |
| N2 | **Fuente de rol.** Rol principal normalizado a DEV/QA/LT (Desarrollador/Arquitecto/Despliegues→DEV; QA→QA; Tech Manager/Líder, Service Reliability Lead, Líder Primera Línea, PTL→LT). No se infiere LT por seniority. |
| N3 | **Dominios + SDA.** Un dominio por corrida (en este repo; el original asignaba ENG+GRM juntos). SDA consolidada por grupo Mesa + Foco. |
| N4 | **Capacidad.** Cada plaza = 1 FTE; máx. 2 proyectos simultáneos por persona; capacidad teórica 100%; la dedicación real solo resuelve continuidad. |
| N5 | **Prioridad tras maximizar cobertura:** continuidad SDA → dominio → rol+seniority (exacto>superior>inferior) → skills (2+ > 1 > 0). |
| N6 | **Skills.** Cualquier nivel positivo cuenta; penalización 5 (una coincidencia) / 10 (ninguna); respaldo sin skills exige dominio; QA puede no declarar skills; sin umbral de nivel por seniority. |
| N7 | **Seniority.** Máx. una categoría adyacente. No se convierte en umbral de skill. |
| N8 | **LT y mezcla.** LT solo interno; se maximiza presencia interna+externa por mesa cuando ambos tipos están disponibles. |
| N9 | **Límite por mesa.** Máx. 7 asignaciones base + 3 recomendaciones DEV/QA; todos los grupos con igual prioridad proporcional de cobertura. |
| N10 | **Campos no usados.** `Nivel general skills técnicos`, `Nivel IA` y skills sugeridas no se usan como requisito ni como match. |

### B. Decisiones de diseño del procesamiento (D1–D12)

| # | Decisión | Flag |
|---|---|---|
| D1 | Base del pool = **Staff Q4** (⨝ skills de DATA1). | — |
| D2 | Interno/externo **autoritativo = Staff Q4**; discrepancia se reporta. | — |
| D3 | Familia **única** LT/DEV/QA; sin inferencia LT por Lead; rol fuera de las 3 se reporta. | `FAMILIAS_VALIDAS` |
| D4 | **Dominio único** por corrida; coincidencia real oferta↔demanda; aborta si no. | `DOMINIO_ASIGNACION` |
| D5 | **Excepción QA sin skills** (respaldo exige dominio). | `QA_SIN_SKILLS_OK` |
| D6 | **SDA consolidada** por grupo Mesa + Foco. | — |
| D7 | **Seniority duro** (±1 nivel) + puntúa. | `SENIORITY_DURA` |
| D8 | **≥1 skill obligatoria** dura (salvo QA). | `SKILLS_MIN_OBLIGATORIAS` |
| D9 | **Sustitución int/ext** salvo LT (se marca). | `SUSTITUCION_INT_EXT` |
| D10 | **Score lexicográfico** (continuidad > dominio > skills > seniority). | `MODO_SCORE` |
| D11 | Reglas de composición/optimización **fuera del procesamiento** (son del motor). | — |
| D12 | Insumos en `Data/`, salida en `golden_set/`. | — |

### C. Reglas del modelo CP-SAT (CP1–CP9)

| # | Regla |
|---|---|
| CP1 | Variable de decisión `x[p,s]` = dedicación de la persona p al slot s. |
| CP2 | **FTE en cuartos** (0/.25/.5/.75/1 → 0–100 paso 25). |
| CP3 | **Capacidad** por persona: Σ_s x[p,s] ≤ capacidad libre (≤ 1 FTE). |
| CP4 | **Cobertura de slot**: Σ_p x[p,s] ≤ 100 (un slot ≤ 1 FTE). |
| CP5 | **1 LT por proyecto**, LT = Lead + interno. |
| CP6 | **Equipo ≤ 7 FTE** (referencia 1 LT + 3 Dev + 3 Tester). |
| CP7 | **Mezcla interno/externo** según demanda del slot. |
| CP8 | **Cobertura parcial permitida** (el modelo decide qué cubrir por prioridad). |
| CP9 | **Objetivo (blando):** maximizar fit·FTE + premio por cobertura; fit = 0.8·skills + 0.2·seniority + bonus continuidad − penalización no cubierto. |

### D. Reglas del modelo MILP (ML1–ML9)

| # | Regla |
|---|---|
| ML1 | Variable binaria `x[p,s]`; cada plaza = **1 FTE indivisible**. |
| ML2 | Cada plaza recibe ≤ 1 persona; cada persona ≤ 1 plaza por proyecto. |
| ML3 | **Máx. 2 proyectos simultáneos** por persona (según solapamiento con el horizonte). |
| ML4 | Por grupo Mesa+Dominio: **≤ 7 base + 3 recomendaciones** DEV/QA. |
| ML5 | **1 LT por grupo**, LT solo interno (sin sustitución de tipo). |
| ML6 | **Mezcla interno/externo** maximizada por mesa sin reducir cobertura. |
| ML7 | **Orden lexicográfico del objetivo:** cobertura → equilibrio entre grupos → presencia int/ext → tipo solicitado → seniority (exacto>superior>inferior) → continuidad SDA → dominio + nº skills. |
| ML8 | **Puntaje de skills:** penalización 5 (una coincidencia en vacante de 2+) / 10 (ninguna); respaldo sin skills exige dominio. |
| ML9 | Plaza sin candidato elegible queda **vacante y se reporta con la causa**. |

---

## Parte 2 · Clasificación: filtrado vs. asignación

### 2.1 Reglas de FILTRADO (elegibilidad — en el procesamiento)

Deciden si un par (persona, plaza) es posible. Están implementadas en
`procesamiento/` y producen `candidatos` / `matriz de elegibilidad`.

| Origen | Regla | Dónde se implementa |
|---|---|---|
| N1, D1, D2 | Población y pool (quién entra); int/ext autoritativo | `carga.py` (normalización + exclusión con reporte) |
| N2, D3 | Rol → familia única LT/DEV/QA; sin inferir LT por seniority | `carga.py::familia_persona` + catálogo en `config.py` |
| N3(parcial), D4 | Dominio único; coincidencia oferta↔demanda (duro) | `prefiltrado.py::es_elegible` (causa `dominio`) |
| N7, D7 | Seniority ±1 nivel (duro) | `prefiltrado.py::es_elegible` (causa `seniority`) |
| N6(parcial), D8 | ≥1 skill obligatoria registrada (duro) | `prefiltrado.py::es_elegible` (causa `skills`) |
| N6(parcial), D5 | Excepción QA sin skills; respaldo exige dominio | `prefiltrado.py::es_elegible` (causa `slot_sin_skills` / `respaldo_sin_skills_sin_dominio`) |
| N8(parcial), D9 | LT = Lead + interno (duro); sustitución int/ext salvo LT | `prefiltrado.py::es_elegible` (causas `lt_*`, `int_ext`) |
| N4(parcial) | Liberación: persona disponible al inicio de la plaza | `prefiltrado.py::es_elegible` (causa `liberacion`) |
| N3(parcial), D6 | SDA consolidada por grupo (insumo de continuidad) | `carga.py` (normalización de la demanda) |
| N10 | Campos no usados (Nivel general, Nivel IA, sugeridas) | `carga.py` (se ignoran al leer skills) |

**También son filtrado (preferencia blanda, se calcula aquí pero no descarta):**

| Origen | Componente | Dónde |
|---|---|---|
| N5, D10 | `score` + componentes (continuidad, dominio, nº skills, seniority_match) | `prefiltrado.py::score` |

> El `score` se **calcula** en el filtrado y viaja en `candidatos`, pero **no
> filtra**: es insumo que el motor usa en su objetivo. Por eso es parte del
> procesamiento aunque exprese una preferencia.

### 2.2 Reglas de ASIGNACIÓN (optimización — en el modelo)

Deciden, entre los pares posibles, a quién se asigna. Viven en el motor
(CP-SAT o MILP). El procesamiento NO las impone.

| Origen | Regla | CP-SAT | MILP |
|---|---|---|---|
| N4(parcial), ML3 | Máx. 2 proyectos simultáneos por persona | — (no modelado) | ML3 |
| CP3, N4 | Capacidad por persona ≤ 1 FTE | CP3 | implícito (1 plaza) |
| CP4, ML2 | 1 persona por plaza / 1 FTE por plaza | CP4 | ML1, ML2 |
| CP2 | FTE fraccionado en cuartos | CP2 | — (plaza indivisible) |
| N8(parcial), CP5, ML5 | 1 LT por equipo | CP5 | ML5 |
| N9, CP6, ML4 | Tope por mesa (≤7 base; +3 recomendaciones en MILP) | CP6 | ML4 |
| N8(parcial), CP7, ML6 | Maximizar mezcla interno/externo por mesa | CP7 | ML6 |
| N9 | Igual prioridad proporcional de cobertura entre grupos | objetivo | ML7 |
| CP8 | Cobertura parcial permitida | CP8 | (cobertura máx.) |
| N5, CP9, ML7, ML8 | **Objetivo / prioridad** (cobertura, continuidad, dominio, seniority, skills) | CP9 (fit ponderado) | ML7, ML8 (lexicográfico) |
| ML9 | Reporte de plaza vacante con causa | (en validación) | ML9 |

> Diferencia clave entre modelos: **CP-SAT** usa un objetivo *ponderado*
> (fit = 0.8·skills + 0.2·seniority + bonus) y permite FTE en cuartos; **MILP**
> usa un objetivo *lexicográfico* y plazas indivisibles. Ambos parten del mismo
> `candidatos` del golden set.

---

## Parte 3 · Mapa de cobertura (ninguna regla queda fuera)

Verificación de que cada regla del inventario está clasificada:

- **Negocio (N1–N10):** N1→filtrado · N2→filtrado · N3→filtrado · N4→ambas
  (capacidad/liberación=filtrado; 2 proyectos=asignación) · N5→score(filtrado) +
  objetivo(asignación) · N6→filtrado · N7→filtrado · N8→ambas (LT elegibilidad=filtrado;
  mezcla=asignación) · N9→asignación · N10→filtrado.
- **Diseño (D1–D12):** D1–D9 → filtrado (D10 es el score) · D11 → declara la
  frontera · D12 → infraestructura (no es regla de negocio).
- **CP-SAT (CP1–CP9):** todas asignación (el motor), salvo que CP5/CP7 tienen su
  parte de elegibilidad ya garantizada por el filtrado.
- **MILP (ML1–ML9):** todas asignación (el motor), salvo ML9 (reporte) que se
  solapa con la validación del procesamiento.

**Frontera (regla D11):** la elegibilidad se resuelve una sola vez en el
procesamiento; las reglas de composición/optimización son responsabilidad del
motor. Una regla puede tener una **parte de filtrado** y una **parte de
asignación** (p. ej. N4 y N8): en esos casos la parte dura de posibilidad va al
filtrado y la parte de optimización va al modelo.
