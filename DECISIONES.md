# Decisiones de diseño

Registro de las decisiones tomadas sobre el procesamiento, con su justificación.
Cada decisión es **conmutable por un flag** en `procesamiento/config.py` salvo que
se indique lo contrario; ninguna se eliminó del código, solo se fijó su valor.

Referencia conceptual: `docs/PROCESO_ESTANDAR_PREMODELO.md`.

---

## D1 · Base del pool = Staff Q4
El universo de personas asignables es el **Staff Q4 (DATA3)**, enriquecido con las
skills de DATA1 por `Código`. No al revés.
**Por qué:** el staff define disponibilidad real (capacidad, tipo interno/externo,
fechas). DATA1 trae ~1.680 perfiles, muchos no asignables. Partir del staff evita
arrastrar gente que no está en juego.

## D2 · Interno/externo autoritativo = Staff Q4
El tipo interno/externo lo manda el staff. La discrepancia con DATA1 se **reporta**,
no se resuelve en silencio.

## D3 · Familia de rol única: LT / DEV / QA
Cada persona y cada slot se homologan a **una sola** familia (no un conjunto).
**No se infiere LT por seniority Lead**: solo roles de liderazgo explícitos son LT.
Un rol que no cae en LT/DEV/QA **no se descarta en silencio**: se reporta en
`revision_personas.csv` con el rol crudo.
**Flags:** `FAMILIAS_VALIDAS`, catálogos `ROL_SLOT_A_FAMILIA` / `ROL_PERSONA_A_FAMILIA`.

## D4 · Dominio único por corrida, con coincidencia oferta↔demanda
Un solo dominio por ejecución (no multidominio). El dominio de la **oferta** se lee
del dato real del staff (DATA3); el de la **demanda** es `DOMINIO_ASIGNACION`. El
pipeline exige que coincidan y **aborta** si no.
**Flag:** `DOMINIO_ASIGNACION`.

## D5 · Excepción QA sin skills
Un slot QA puede no declarar skills obligatorias y aun así tener candidatos (entra
por rol + seniority). Si declara skills, se exigen. El respaldo sin skills exige
coincidencia de dominio.
**Flag:** `QA_SIN_SKILLS_OK`.

## D6 · SDA consolidada por grupo Mesa + Foco
La continuidad se evalúa contra la **lista deduplicada de SDA del grupo
(Mesa, Fábrica)**, no contra la SDA individual del slot.
(No es flag; es parte de la normalización de la demanda.)

## D7 · Seniority como filtro duro
Seniority dentro de **±1 nivel** es regla dura; además puntúa en el score.
**Flag:** `SENIORITY_DURA`.

## D8 · Skills obligatorias ≥ 1 como filtro duro
La persona debe cubrir al menos 1 skill obligatoria del slot (salvo excepción QA,
D5). Cualquier nivel positivo cuenta; no hay umbral de nivel por seniority.
**Flag:** `SKILLS_MIN_OBLIGATORIAS`.

## D9 · Sustitución interno/externo salvo LT
Si falta el tipo pedido, se admite el opuesto y se marca la sustitución. **LT nunca**
admite sustitución (siempre interno).
**Flag:** `SUSTITUCION_INT_EXT`.

## D10 · Score lexicográfico
Preferencia por orden: continuidad > dominio > nº skills cubiertas > ajuste de
seniority. Alternativa disponible: fit continuo ponderado.
**Flag:** `MODO_SCORE` (`"lexicografico"` | `"ponderado"`).

## D11 · Reglas de asignación fuera del procesamiento
Composición de equipo (1 LT, ≤7 FTE por mesa), máx. 2 proyectos simultáneos,
maximización de cobertura y mezcla int/ext **no** están en el procesamiento: son del
motor (CP-SAT / MILP). El procesamiento solo decide **elegibilidad**.

## D12 · Insumos en `Data/`, salida en `golden_set/`
Los tres Excel van en `Data/` (ignorados por git). El golden set se genera en
`golden_set/` en la raíz del repo (también ignorado). El código se busca los Excel
por patrón de nombre (`DATA1*`, `DATA2*`, `DATA3*`).

---

## Pendiente real
- **Capacidad**: hoy uniforme al 100% (`CAPACIDAD_UNIFORME=True`). Cambiar a
  capacidad real cuando se valide la calidad de DATA3.
- **Nueva data de personas** con roles ya normalizados a LT/DEV/QA: al subirla,
  el reporte "rol fuera de LT/DEV/QA" debe quedar vacío.
