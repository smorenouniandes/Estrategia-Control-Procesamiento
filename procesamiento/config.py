"""Configuración única del procesamiento inicial.

Centraliza rutas, vocabularios controlados, el catálogo de roles y los parámetros
de las decisiones [A CONFIRMAR] del proceso estándar (ver §7 de
PROCESO_ESTANDAR_PREMODELO.md). Cambiar una decisión de negocio = cambiar un flag
aquí, sin tocar la lógica.
"""
from __future__ import annotations
from pathlib import Path

# --- rutas ---------------------------------------------------------------
# Los insumos van en la carpeta Data/ en la raíz del repo. Se buscan por patrón
# de nombre (insensible a mayúsculas) para tolerar variaciones como
# 'DATA1_personas.xlsx', 'DATA1.xlsx', 'data1_v2.xlsx'... Si hay varios que
# coincidan, se toma el más reciente. Si no hay ninguno, el pipeline avisa con
# un mensaje claro indicando dónde dejar el archivo.
ROOT = Path(__file__).resolve().parent.parent      # raíz del repo
DATA_DIR = ROOT / "Data"                            # insumos
OUT_DIR = ROOT / "golden_set"                       # salida en la raíz del repo


def _buscar_insumo(patron: str, etiqueta: str) -> Path:
    """Devuelve el Excel que empieza por `patron` en Data/ (el más reciente)."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"No existe la carpeta de insumos: {DATA_DIR}\n"
            f"Crea la carpeta 'Data/' en la raíz del repo y deja ahí los 3 Excel.")
    candidatos = sorted(
        [p for p in DATA_DIR.glob("*.xls*")
         if p.name.lower().startswith(patron.lower())],
        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise FileNotFoundError(
            f"No encuentro el insumo de {etiqueta} en {DATA_DIR}\n"
            f"Esperaba un .xlsx cuyo nombre empiece por '{patron}' "
            f"(p.ej. '{patron}_....xlsx').")
    return candidatos[0]


def rutas_insumos() -> tuple[Path, Path, Path]:
    """(DATA1 personas, DATA2 demanda, DATA3 staff). Resuelve en tiempo de uso."""
    return (_buscar_insumo("DATA1", "personas (skills)"),
            _buscar_insumo("DATA2", "demanda"),
            _buscar_insumo("DATA3", "staff Q4"))


# Rutas concretas, resueltas al importar. Si falta un insumo, el error claro de
# _buscar_insumo se lanza aquí, antes de empezar a procesar.
DATA1_PATH, DATA2_PATH, DATA3_PATH = rutas_insumos()

# =========================================================================
# PARÁMETROS [A CONFIRMAR] — línea base propuesta. Ver §7 del proceso.
# =========================================================================
SENIORITY_DURA = True            # (1) seniority como filtro duro, máx. 1 nivel
SKILLS_MIN_OBLIGATORIAS = 1      # (2) nº mínimo de skills obligatorias registradas
MODO_SCORE = "lexicografico"     # (3) "lexicografico" | "ponderado"
CAPACIDAD_UNIFORME = True        # (4) True = ignora capacidad real, todos al 100%
SUSTITUCION_INT_EXT = True       # (5) permite tipo opuesto salvo LT (se marca)
# Un ÚNICO dominio por corrida, configurable (no fijo a ENG). Si se sube data de
# otro dominio, basta cambiar este valor. El pipeline valida que la demanda traiga
# un solo dominio y falla si detecta más de uno.
DOMINIO_ASIGNACION = "ENG"
QA_SIN_SKILLS_OK = True          # (6) QA puede no declarar skills obligatorias
# =========================================================================

# --- escala de skills [BA1/BA2] -----------------------------------------
SKILL_MIN, SKILL_MAX = 0, 4
SKILL_LABEL_TO_INT = {
    "0 - nulo": 0, "1 - básico": 1, "2 - intermedio": 2,
    "3 - avanzado": 3, "4 - experto": 4,
}

# --- seniority [BC1] -----------------------------------------------------
SENIORITY_VALIDOS = {"lead": "Lead", "senior": "Senior",
                     "mid-level": "Mid-Level", "mid level": "Mid-Level",
                     "junior": "Junior"}
SENIORITY_DESCONOCIDO = "DESCONOCIDO"
SENIORITY_ORDEN = {"Junior": 1, "Mid-Level": 2, "Senior": 3, "Lead": 4}

# --- familias de rol -----------------------------------------------------
FAMILIA_LT, FAMILIA_DEV, FAMILIA_QA = "LT", "DEV", "QA"

# --- catálogo único de roles (§4 del proceso) ---------------------------
# Las familias de asignación son EXACTAMENTE tres: LT, DEV, QA. Tanto la persona
# como el slot se homologan a UNA sola familia (decisión del 24-nov con el equipo
# de Optimizacion). No se infiere LT por seniority Lead.
FAMILIAS_VALIDAS = {FAMILIA_LT, FAMILIA_DEV, FAMILIA_QA}

# Rol del SLOT (demanda) -> familia única
ROL_SLOT_A_FAMILIA = {
    "lt": FAMILIA_LT,
    "product engineer (lt - ia)": FAMILIA_LT,
    "lider tecnico": FAMILIA_LT, "líder técnico": FAMILIA_LT,
    "po": FAMILIA_LT,
    "dev": FAMILIA_DEV, "dev int": FAMILIA_DEV, "dev ext": FAMILIA_DEV,
    "desarrollador": FAMILIA_DEV, "data ing": FAMILIA_DEV, "ux": FAMILIA_DEV,
    "arquitecto": FAMILIA_DEV, "despliegues": FAMILIA_DEV,
    "qa": FAMILIA_QA, "quality & context": FAMILIA_QA, "testing": FAMILIA_QA,
}

# Rol de la PERSONA -> familia única (match por startswith del prefijo).
# La nueva data de personas debería traer el rol ya normalizado a LT/DEV/QA; este
# mapeo tolera roles sueltos conocidos. Un rol que NO caiga en LT/DEV/QA NO se
# excluye en silencio: se reporta en revision_personas.csv como "rol fuera de
# LT/DEV/QA" para que se corrija en origen.
ROL_PERSONA_A_FAMILIA = [
    ("lt", FAMILIA_LT),
    ("lider tecnico", FAMILIA_LT), ("líder técnico", FAMILIA_LT),
    ("tech manager", FAMILIA_LT),
    ("service reliability lead", FAMILIA_LT),
    ("lider primera linea", FAMILIA_LT), ("líder primera línea", FAMILIA_LT),
    ("ptl", FAMILIA_LT),
    ("qa", FAMILIA_QA), ("testing", FAMILIA_QA), ("tester", FAMILIA_QA),
    ("dev", FAMILIA_DEV), ("desarrollador", FAMILIA_DEV),
    ("developer", FAMILIA_DEV), ("arquitecto", FAMILIA_DEV),
    ("arquitectura", FAMILIA_DEV), ("despliegues", FAMILIA_DEV),
    ("data ing", FAMILIA_DEV),
]
ROL_PERSONA_BASURA = ("na ", "na", "cod eliminado")

# --- staff Q4 (DATA3): 3 hojas -> esquema común --------------------------
STAFF_INTERNO_VALOR = "interno"
STAFF_HOJAS = {
    "Staff System": {
        "codigo": "Código", "nombre": "Nombre", "direccion": "Dirección",
        "empresa": "Empresa", "interno": "Interno", "rol": "Rol",
        "dominio": "Dominio",
        "capacidad": ("compromiso", "% Dedicación"),
        "proyecto": "Proyecto", "fecha_fin": "Fecha Fin Actual",
    },
    "Staff Data": {
        "codigo": "Codigo", "nombre": "Nombre", "direccion": "Dirección",
        "empresa": "Empresa", "interno": "Interno/ Externo", "rol": "Rol",
        "dominio": "Dominio",
        "capacidad": ("disponible", "% Total x usuario"),
    },
    "Staff Arquitectura": {
        "codigo": "Código", "nombre": "Nombre", "direccion": "Dirección",
        "empresa": "Empresa", "interno": "Interno", "rol": "Rol",
        "dominio": "Dominio",
        "capacidad": ("compromiso", "% Dedicación"),
    },
}

# --- dominio -------------------------------------------------------------
# UN solo dominio por corrida. El dominio de la OFERTA (personas) se lee del dato
# REAL del staff (DATA3, columna 'Dominio'). El dominio de la DEMANDA (slots) es
# DOMINIO_ASIGNACION (DATA2 no trae dominio, solo Dirección). El pipeline EXIGE
# que el dominio del staff sea único y COINCIDA con DOMINIO_ASIGNACION; si no,
# aborta en vez de pasar en silencio. El filtro de dominio en el prefiltrado
# descarta (y reporta) a quien no coincida. No es multidominio.

# --- tiempo --------------------------------------------------------------
TRIMESTRES_2027 = ["1Q 2027", "2Q 2027", "3Q 2027", "4Q 2027"]

# --- composición (referencia; la impone el motor, no esta capa) ----------
TOPE_LT = 1
TOPE_FTE_PROYECTO = 7

# --- score ponderado (solo si MODO_SCORE == "ponderado") ----------------
W_FIT_SKILLS = 0.8
W_FIT_SENIORITY = 0.2
FIT_SENIORITY_COINCIDE = 1.0
FIT_SENIORITY_POR_ENCIMA = 0.75
FIT_SENIORITY_PASO_DEBAJO = 0.25
FIT_SENIORITY_SIN_DATO = 0.5
BONUS_CONTINUIDAD = 0.15
