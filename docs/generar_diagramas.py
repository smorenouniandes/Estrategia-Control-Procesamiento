"""Genera los diagramas de arquitectura (funcional y técnico) como PNG.

Reproducible: `python docs/generar_diagramas.py` reescribe las dos imágenes en
docs/. Solo depende de matplotlib. No lee datos; dibuja la arquitectura descrita
en DOCUMENTACION_E2E.md.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

DOCS = Path(__file__).resolve().parent

# paleta
C_SRC = "#E8EEF7"; C_SRC_E = "#355C9E"      # fuentes
C_PROC = "#E9F5EC"; C_PROC_E = "#2E7D46"    # procesamiento
C_GOLD = "#FCF3D9"; C_GOLD_E = "#B8860B"    # golden set
C_MODEL = "#F3E9F5"; C_MODEL_E = "#7B3F9E"  # modelos
C_TXT = "#1A1A1A"


def _box(ax, x, y, w, h, text, fc, ec, fs=10, bold=False, round_=0.015):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={round_}",
        linewidth=1.6, edgecolor=ec, facecolor=fc, mutation_aspect=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=C_TXT, fontweight="bold" if bold else "normal",
            linespacing=1.35)


def _arrow(ax, p0, p1, ec="#555", lw=1.8, style="-|>"):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle=style, mutation_scale=16, linewidth=lw,
        color=ec, shrinkA=2, shrinkB=2))


def _band(ax, x, y, w, h, label, ec):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.002,rounding_size=0.01",
        linewidth=1.3, edgecolor=ec, facecolor="none", linestyle=(0, (6, 4))))
    # etiqueta sobre una cápsula blanca pegada al borde superior, para que ninguna
    # flecha ni caja la tape.
    tx, ty = x + 0.02, y + h + 0.004
    ax.text(tx, ty, label, ha="left", va="bottom", fontsize=9.5, color=ec,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=ec, lw=1.0))


# =========================================================================
# 1. ARQUITECTURA FUNCIONAL — qué hace cada etapa (lenguaje de negocio)
# =========================================================================
def diagrama_funcional():
    fig, ax = plt.subplots(figsize=(12.5, 8.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("Arquitectura funcional — Procesamiento inicial y Golden Set",
                 fontsize=14, fontweight="bold", pad=14)

    # --- banda 1: fuentes ---
    _band(ax, 0.03, 0.80, 0.94, 0.16, "1 · BASES DE ENTRADA", C_SRC_E)
    _box(ax, 0.06, 0.83, 0.26, 0.09,
         "DATA1 · Personas\n(skills por persona)", C_SRC, C_SRC_E, 9.5)
    _box(ax, 0.37, 0.83, 0.26, 0.09,
         "DATA2 · Demanda\n(plazas por proyecto)", C_SRC, C_SRC_E, 9.5)
    _box(ax, 0.68, 0.83, 0.26, 0.09,
         "DATA3 · Staff Q4\n(pool disponible)", C_SRC, C_SRC_E, 9.5)

    # --- banda 2: procesamiento ---
    _band(ax, 0.03, 0.30, 0.60, 0.44, "2 · PROCESAMIENTO (reglas de elegibilidad)", C_PROC_E)
    _box(ax, 0.07, 0.60, 0.52, 0.10,
         "Carga y normalización\nPool = Staff Q4 enriquecido con skills · un solo dominio",
         C_PROC, C_PROC_E, 9.5, bold=True)
    _box(ax, 0.07, 0.46, 0.52, 0.10,
         "Prefiltrado\nReglas DURAS: familia, LT, dominio, seniority, skills, liberación\n+ score de preferencia (blando)",
         C_PROC, C_PROC_E, 9, bold=True)
    _box(ax, 0.07, 0.33, 0.52, 0.09,
         "Validación\nMatriz de elegibilidad + cobertura y causa por plaza",
         C_PROC, C_PROC_E, 9.5, bold=True)

    # --- banda 3: golden set ---
    _band(ax, 0.66, 0.30, 0.31, 0.44, "3 · GOLDEN SET (fuente única)", C_GOLD_E)
    _box(ax, 0.68, 0.33, 0.27, 0.37,
         "personas · slots\ncandidatos (+score)\nmatriz elegibilidad\ncobertura · resumen\nrevisión · reporte",
         C_GOLD, C_GOLD_E, 9.5, bold=True)

    # --- banda 4: modelos ---
    _band(ax, 0.03, 0.03, 0.94, 0.22, "4 · MODELOS (reglas de asignación — fuera del procesamiento)", C_MODEL_E)
    _box(ax, 0.10, 0.07, 0.36, 0.11,
         "Modelo CP-SAT\n(Estrategia & Control)", C_MODEL, C_MODEL_E, 10, bold=True)
    _box(ax, 0.54, 0.07, 0.36, 0.11,
         "Modelo MILP\n(Optimización)", C_MODEL, C_MODEL_E, 10, bold=True)

    # flechas fuentes -> procesamiento
    _arrow(ax, (0.19, 0.83), (0.30, 0.705))
    _arrow(ax, (0.50, 0.83), (0.40, 0.705))
    _arrow(ax, (0.81, 0.83), (0.52, 0.705))
    # dentro del procesamiento (cascada)
    _arrow(ax, (0.33, 0.60), (0.33, 0.565))
    _arrow(ax, (0.33, 0.46), (0.33, 0.425))
    # procesamiento -> golden
    _arrow(ax, (0.59, 0.375), (0.68, 0.46), ec=C_GOLD_E, lw=2.2)
    # golden -> modelos
    _arrow(ax, (0.78, 0.33), (0.30, 0.185), ec=C_MODEL_E, lw=2.2)
    _arrow(ax, (0.84, 0.33), (0.70, 0.185), ec=C_MODEL_E, lw=2.2)

    ax.text(0.5, 0.004,
            "El procesamiento define QUIÉN PUEDE ir en cada plaza (elegibilidad). "
            "Los modelos deciden A QUIÉN se asigna (asignación).",
            ha="center", va="bottom", fontsize=8.5, style="italic", color="#444")

    out = DOCS / "arquitectura_funcional.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


# =========================================================================
# 2. ARQUITECTURA TÉCNICA — módulos, funciones, formatos, I/O
# =========================================================================
def diagrama_tecnico():
    fig, ax = plt.subplots(figsize=(13.2, 9.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("Arquitectura técnica — módulos, I/O y artefactos",
                 fontsize=14, fontweight="bold", pad=14)

    # --- entradas (.xlsx) ---
    _band(ax, 0.02, 0.82, 0.96, 0.15, "Entradas (.xlsx, raíz del workspace)", C_SRC_E)
    for i, (txt) in enumerate(["DATA1_personas.xlsx\nHoja 1 · 160 cols",
                               "DATA2_demanda.xlsx\nHoja 1",
                               "DATA3_staffq4.xlsx\n3 hojas"]):
        _box(ax, 0.05 + i * 0.31, 0.845, 0.27, 0.095, txt, C_SRC, C_SRC_E, 9)

    # --- módulos python ---
    _band(ax, 0.02, 0.40, 0.62, 0.38, "Paquete procesamiento/ (pandas)", C_PROC_E)
    mods = [
        (0.05, 0.66, "config.py\nflags · catálogo de roles · mapeos"),
        (0.05, 0.555, "carga.py\ncargar_staff · cargar_skills\nconstruir_pool · cargar_slots"),
        (0.05, 0.45, "prefiltrado.py\nes_elegible() · score()\nconstruir_candidatos()"),
        (0.345, 0.555, "tiempo.py\nparse_trimestre · parse_fecha"),
        (0.345, 0.45, "validacion.py\nmatriz_elegibilidad\nreporte_cobertura"),
        (0.345, 0.66, "run.py\norquestador 3 capas"),
    ]
    for x, y, t in mods:
        _box(ax, x, y, 0.27, 0.088, t, C_PROC, C_PROC_E, 8.3)
    _box(ax, 0.05, 0.415, 0.565, 0.025,
         "golden.py · escribir_golden_set() / cargar_golden_set()", C_PROC, C_PROC_E, 8.3, bold=True)

    # --- artefactos golden_set (CSV, en modelo/ y reportes/) ---
    _band(ax, 0.66, 0.335, 0.32, 0.445, "golden_set/ (solo CSV)", C_GOLD_E)
    # sub-bloque modelo/
    ax.text(0.675, 0.742, "modelo/  — entrada de los modelos",
            ha="left", va="center", fontsize=8.0, color=C_GOLD_E, fontweight="bold")
    y = 0.715
    for a in ["personas.csv", "slots.csv", "candidatos.csv  (principal)"]:
        _box(ax, 0.675, y - 0.030, 0.29, 0.030, a, C_GOLD, C_GOLD_E, 7.9)
        y -= 0.036
    # sub-bloque reportes/
    ax.text(0.675, y - 0.016, "reportes/  — auditoría (no entra al modelo)",
            ha="left", va="center", fontsize=8.0, color=C_GOLD_E, fontweight="bold")
    y -= 0.032
    for a in ["cobertura.csv", "resumen.json",
              "revision_personas.csv", "reporte_normalizacion.txt"]:
        _box(ax, 0.675, y - 0.030, 0.29, 0.030, a, "#FDF8E8", C_GOLD_E, 7.9)
        y -= 0.036

    # --- consumidores ---
    _band(ax, 0.02, 0.03, 0.96, 0.33, "Consumidores (modelos — fuera del alcance)", C_MODEL_E)
    _box(ax, 0.08, 0.14, 0.38, 0.14,
         "CP-SAT (OR-Tools)\n\nvariables x[p,s] sobre candidatos\n+ restricciones de composición\n+ objetivo con score",
         C_MODEL, C_MODEL_E, 8.6, bold=True)
    _box(ax, 0.54, 0.14, 0.38, 0.14,
         "MILP (SciPy/HiGHS)\n\nvariables x[p,s] sobre candidatos\n+ restricciones de composición\n+ objetivo con score",
         C_MODEL, C_MODEL_E, 8.6, bold=True)
    _box(ax, 0.30, 0.055, 0.40, 0.045,
         "cargar_golden_set()  →  gs.personas / gs.slots / gs.candidatos",
         C_GOLD, C_GOLD_E, 8.3, bold=True)

    # flechas
    for i in range(3):
        _arrow(ax, (0.185 + i * 0.31, 0.845), (0.30, 0.655))
    _arrow(ax, (0.33, 0.66), (0.33, 0.645))
    _arrow(ax, (0.33, 0.555), (0.33, 0.54))
    _arrow(ax, (0.19, 0.45), (0.19, 0.442))
    _arrow(ax, (0.62, 0.427), (0.675, 0.50), ec=C_GOLD_E, lw=2.2)
    _arrow(ax, (0.80, 0.335), (0.52, 0.105), ec=C_MODEL_E, lw=2.0)
    _arrow(ax, (0.50, 0.055), (0.27, 0.21), ec=C_MODEL_E, lw=1.6)
    _arrow(ax, (0.50, 0.055), (0.73, 0.21), ec=C_MODEL_E, lw=1.6)

    ax.text(0.5, 0.004,
            "Golden set solo en CSV, separado en modelo/ (entrada) y reportes/ (auditoría). "
            "Los modelos NO leen los .xlsx ni re-aplican reglas.",
            ha="center", va="bottom", fontsize=8.5, style="italic", color="#444")

    out = DOCS / "arquitectura_tecnica.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


if __name__ == "__main__":
    f = diagrama_funcional()
    t = diagrama_tecnico()
    print(f"Generados:\n  {f}\n  {t}")
