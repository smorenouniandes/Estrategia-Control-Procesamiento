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

    # Layout en 4 franjas verticales con un flujo descendente claro:
    #   Entradas  →  Pipeline (carga→prefiltrado→validación→golden)  →
    #   golden_set  →  Consumidores.  Las flechas no cruzan cajas.

    # --- franja 1: entradas (.xlsx) ---
    _band(ax, 0.02, 0.85, 0.96, 0.12, "1 · Entradas (.xlsx en Data/)", C_SRC_E)
    entradas_x = [0.06, 0.37, 0.68]
    for x, txt in zip(entradas_x, ["DATA1_personas.xlsx\nHoja 1 · 160 cols",
                                   "DATA2_demanda.xlsx\nHoja 1",
                                   "DATA3_staffq4.xlsx\n3 hojas"]):
        _box(ax, x, 0.865, 0.26, 0.075, txt, C_SRC, C_SRC_E, 8.6)

    # --- franja 2: pipeline (columna izquierda, flujo vertical lineal) ---
    _band(ax, 0.02, 0.30, 0.52, 0.49, "2 · Paquete procesamiento/ (pandas)", C_PROC_E)
    # run.py orquesta (a la derecha, apunta a cada capa)
    _box(ax, 0.40, 0.56, 0.12, 0.17,
         "run.py\n\norquesta\nlas 3\ncapas", C_PROC, C_PROC_E, 8.0, bold=True)
    # las 3 capas en cascada vertical
    _box(ax, 0.05, 0.665, 0.31, 0.075,
         "carga.py  (Capa 1)\nnormaliza · pool = staff + skills · slots", C_PROC, C_PROC_E, 8.0)
    _box(ax, 0.05, 0.555, 0.31, 0.075,
         "prefiltrado.py  (Capa 2)\nes_elegible() + score()", C_PROC, C_PROC_E, 8.0)
    _box(ax, 0.05, 0.445, 0.31, 0.075,
         "validacion.py  (Capa 3)\nmatriz elegibilidad + cobertura", C_PROC, C_PROC_E, 8.0)
    # soporte (config, tiempo) a la derecha abajo
    _box(ax, 0.40, 0.445, 0.12, 0.085,
         "config.py\ntiempo.py\n(soporte)", C_PROC, C_PROC_E, 7.6)
    # golden.py cierra el paquete (escribe el golden set)
    _box(ax, 0.05, 0.315, 0.47, 0.055,
         "golden.py · escribir_golden_set()", C_PROC, C_PROC_E, 8.2, bold=True)

    # --- franja 3: golden_set (columna derecha) ---
    _band(ax, 0.58, 0.30, 0.40, 0.49, "3 · golden_set/ (solo CSV)", C_GOLD_E)
    ax.text(0.60, 0.752, "modelo/  — entrada de los modelos",
            ha="left", va="center", fontsize=8.2, color=C_GOLD_E, fontweight="bold")
    y = 0.725
    for a in ["personas.csv", "slots.csv", "candidatos.csv  (principal)"]:
        _box(ax, 0.60, y - 0.032, 0.36, 0.032, a, C_GOLD, C_GOLD_E, 8.0)
        y -= 0.04
    ax.text(0.60, y - 0.012, "reportes/  — auditoría (no entra al modelo)",
            ha="left", va="center", fontsize=8.2, color=C_GOLD_E, fontweight="bold")
    y -= 0.03
    for a in ["cobertura.csv", "resumen.json",
              "revision_personas.csv", "reporte_normalizacion.txt"]:
        _box(ax, 0.60, y - 0.032, 0.36, 0.032, a, "#FDF8E8", C_GOLD_E, 8.0)
        y -= 0.04

    # --- franja 4: consumidores ---
    _band(ax, 0.02, 0.03, 0.96, 0.22, "4 · Consumidores (modelos — fuera del alcance)", C_MODEL_E)
    _box(ax, 0.30, 0.185, 0.40, 0.045,
         "cargar_golden_set()  →  gs.candidatos / gs.slots / gs.personas",
         C_GOLD, C_GOLD_E, 8.2, bold=True)
    _box(ax, 0.07, 0.065, 0.40, 0.10,
         "CP-SAT (OR-Tools)\nvariables x[p,s] sobre candidatos\n+ restricciones de composición · objetivo con score",
         C_MODEL, C_MODEL_E, 8.2, bold=True)
    _box(ax, 0.53, 0.065, 0.40, 0.10,
         "MILP (SciPy/HiGHS)\nvariables x[p,s] sobre candidatos\n+ restricciones de composición · objetivo con score",
         C_MODEL, C_MODEL_E, 8.2, bold=True)

    # ===================== FLECHAS (flujo sin cruces) =====================
    # 1) cada entrada baja recta a la Capa 1 (carga.py)
    for x in [0.19, 0.50, 0.81]:
        _arrow(ax, (x, 0.865), (x if x < 0.36 else 0.205, 0.742), ec=C_SRC_E, lw=1.6)
    # 2) cascada vertical entre capas (izquierda)
    _arrow(ax, (0.205, 0.665), (0.205, 0.632))      # carga -> prefiltrado
    _arrow(ax, (0.205, 0.555), (0.205, 0.522))      # prefiltrado -> validación
    _arrow(ax, (0.205, 0.445), (0.205, 0.372))      # validación -> golden.py
    # 3) run.py orquesta (líneas finas a cada capa)
    for yv in (0.702, 0.592, 0.482):
        _arrow(ax, (0.40, 0.60), (0.363, yv), ec="#9BB9A6", lw=1.0, style="-|>")
    # 4) golden.py escribe el golden_set (cruza a la franja 3, sin tocar cajas)
    _arrow(ax, (0.52, 0.343), (0.58, 0.40), ec=C_GOLD_E, lw=2.4)
    # 5) golden_set se carga en los consumidores (baja recto)
    _arrow(ax, (0.70, 0.30), (0.55, 0.232), ec=C_MODEL_E, lw=2.0)
    # 6) cargar_golden_set alimenta a cada modelo
    _arrow(ax, (0.42, 0.185), (0.27, 0.167), ec=C_MODEL_E, lw=1.6)
    _arrow(ax, (0.58, 0.185), (0.73, 0.167), ec=C_MODEL_E, lw=1.6)

    ax.text(0.5, 0.004,
            "Flujo: Entradas → carga → prefiltrado → validación → golden.py → golden_set → modelos. "
            "Los modelos NO leen los .xlsx ni re-aplican reglas.",
            ha="center", va="bottom", fontsize=8.3, style="italic", color="#444")

    out = DOCS / "arquitectura_tecnica.png"
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)
    return out


if __name__ == "__main__":
    f = diagrama_funcional()
    t = diagrama_tecnico()
    print(f"Generados:\n  {f}\n  {t}")
