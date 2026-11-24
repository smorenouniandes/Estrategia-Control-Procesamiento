"""Orquestador del procesamiento inicial -> golden set.

Pipeline:  Carga/Normalización -> Prefiltrado -> Validación -> golden_set/

Ejecuta sobre la data real (DATA1/2/3 en la raíz del workspace) aplicando las
decisiones de PROCESO_ESTANDAR_PREMODELO.md. Produce el dataset único que
consumen el modelo CP-SAT y el modelo MILP.
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
import pandas as pd

# permite 'python run.py' (directo) y 'python -m procesamiento_inicial.run'
if __package__ in (None, ""):
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from procesamiento_inicial import config as C
from procesamiento_inicial.carga import (Reporte, cargar_skills, cargar_staff,
                                         construir_pool, cargar_slots)
from procesamiento_inicial.prefiltrado import construir_candidatos
from procesamiento_inicial.validacion import (matriz_elegibilidad,
                                              reporte_cobertura, resumen_cobertura)
from procesamiento_inicial.golden import escribir_golden_set


def linea(c="="):
    print(c * 78)


def main():
    linea()
    print("PROCESAMIENTO INICIAL — Golden Set compartido (CP-SAT / MILP)")
    print(f"Modo score={C.MODO_SCORE} | seniority_dura={C.SENIORITY_DURA} | "
          f"skills_min={C.SKILLS_MIN_OBLIGATORIAS} | "
          f"capacidad_uniforme={C.CAPACIDAD_UNIFORME} | "
          f"sustitucion_int_ext={C.SUSTITUCION_INT_EXT}")
    linea()

    rep = Reporte()

    # ---------- Capa 1: carga + normalización ----------
    staff = cargar_staff(rep)
    skills = cargar_skills(rep)
    personas = construir_pool(staff, skills, rep)
    slots = cargar_slots(rep)
    print("\n[1] CARGA Y NORMALIZACIÓN")
    print(rep.dump())

    # ---------- Capa 2: prefiltrado ----------
    candidatos, pref = construir_candidatos(personas, slots)
    print("\n[2] PREFILTRADO")
    print(f"  - Combinaciones posibles: {pref['combinaciones_posibles']:,}")
    print(f"  - Combinaciones viables:  {pref['combinaciones_viables']:,}")
    print(f"  - Reducción:              {pref['reduccion_pct']:.1f}%")

    # ---------- Capa 3: validación ----------
    M = matriz_elegibilidad(candidatos, personas, slots)
    cob = reporte_cobertura(slots, pref)
    res_cob = resumen_cobertura(cob)
    print("\n[3] VALIDACIÓN")
    print(f"  - Matriz: {M.shape[0]} personas x {M.shape[1]} slots, "
          f"{int(M.values.sum()):,} celdas viables.")
    print(f"  - Slots cubribles: {res_cob['slots_cubribles']}/"
          f"{res_cob['slots_totales']}")
    if res_cob["slots_sin_candidato"]:
        print(f"  - Sin candidato ({res_cob['slots_sin_candidato']}), causas: "
              f"{res_cob['causas_sin_candidato']}")

    # ---------- golden set ----------
    candidatos_df = pd.DataFrame(candidatos)
    revision_df = pd.DataFrame(rep.revision) if rep.revision else pd.DataFrame(
        columns=["codigo", "nombre", "estado", "motivo"])
    resumen = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "parametros": {
            "MODO_SCORE": C.MODO_SCORE,
            "SENIORITY_DURA": C.SENIORITY_DURA,
            "SKILLS_MIN_OBLIGATORIAS": C.SKILLS_MIN_OBLIGATORIAS,
            "CAPACIDAD_UNIFORME": C.CAPACIDAD_UNIFORME,
            "SUSTITUCION_INT_EXT": C.SUSTITUCION_INT_EXT,
            "DOMINIO_ASIGNACION": C.DOMINIO_ASIGNACION,
            "QA_SIN_SKILLS_OK": C.QA_SIN_SKILLS_OK,
        },
        "conteos": {
            "personas": int(len(personas)),
            "slots": int(len(slots)),
            "candidatos": int(len(candidatos)),
            "personas_revision": int(len(revision_df)),
        },
        "prefiltrado": {k: v for k, v in pref.items()
                        if k not in ("candidatos_por_slot", "causa_por_slot",
                                     "slots_sin_candidato")},
        "cobertura": res_cob,
    }

    escribir_golden_set(C.OUT_DIR, personas, slots, candidatos_df, cob,
                        resumen, revision_df, rep.dump())
    print(f"\n[OK] Golden set -> {C.OUT_DIR}")
    print("     modelo/   (entrada de los modelos):  personas.csv · slots.csv · candidatos.csv")
    print("     reportes/ (auditoría):               cobertura.csv · resumen.json ·")
    print("                                          revision_personas.csv · reporte_normalizacion.txt")
    linea()


if __name__ == "__main__":
    main()
