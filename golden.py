"""Golden set: serialización y carga del dataset estandarizado compartido.

`escribir_golden_set` emite los artefactos; `cargar_golden_set` los reconstruye
para que CP-SAT y MILP partan de la misma base. Ver README.md.

Organización (solo CSV):
  golden_set/
    modelo/      -> entrada directa de los modelos (personas, slots, candidatos)
    reportes/    -> auditoría para humanos (cobertura, resumen, revisión, traza)
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

# subcarpetas
SUBDIR_MODELO = "modelo"
SUBDIR_REPORTES = "reportes"

# columnas cuyo contenido es lista/set y se serializa como JSON dentro de la celda.
# 'familia' y 'dominio' son escalares (una sola familia LT/DEV/QA, un solo dominio).
_COLS_LISTA_PERSONAS = ["sdas_vigentes_2027"]
_COLS_LISTA_SLOTS = ["skills_obligatorias", "trimestres", "sdas_grupo"]


def _jsonify(v):
    if isinstance(v, (set, frozenset)):
        return json.dumps(sorted(v), ensure_ascii=False)
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False)
    return v


def _csv_friendly(df: pd.DataFrame, cols_lista) -> pd.DataFrame:
    out = df.copy()
    for c in cols_lista:
        if c in out.columns:
            out[c] = out[c].map(_jsonify)
    return out


def escribir_golden_set(out_dir, personas, slots, candidatos_df,
                        cobertura, resumen, revision_df, reporte_txt):
    """Escribe el golden set en CSV, separado en modelo/ y reportes/."""
    out = Path(out_dir)
    modelo = out / SUBDIR_MODELO
    reportes = out / SUBDIR_REPORTES
    modelo.mkdir(parents=True, exist_ok=True)
    reportes.mkdir(parents=True, exist_ok=True)

    # --- ENTRADA DE LOS MODELOS (modelo/) ---
    _csv_friendly(personas, _COLS_LISTA_PERSONAS).to_csv(
        modelo / "personas.csv", index=False)
    _csv_friendly(slots, _COLS_LISTA_SLOTS).to_csv(
        modelo / "slots.csv", index=False)
    candidatos_df.to_csv(modelo / "candidatos.csv", index=False)

    # --- REPORTES DE AUDITORÍA (reportes/) ---
    cobertura.to_csv(reportes / "cobertura.csv", index=False)
    revision_df.to_csv(reportes / "revision_personas.csv", index=False)
    (reportes / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    (reportes / "reporte_normalizacion.txt").write_text(
        reporte_txt, encoding="utf-8")


# =========================================================================
# Carga para consumo por los modelos
# =========================================================================
@dataclass
class GoldenSet:
    personas: pd.DataFrame
    slots: pd.DataFrame
    candidatos: pd.DataFrame
    cobertura: pd.DataFrame
    resumen: dict


def _parse_listas(df: pd.DataFrame, cols_lista) -> pd.DataFrame:
    out = df.copy()
    for c in cols_lista:
        if c in out.columns:
            out[c] = out[c].map(
                lambda v: json.loads(v) if isinstance(v, str) and v.strip() else [])
    return out


def cargar_golden_set(golden_dir) -> GoldenSet:
    """Reconstruye el golden set desde los CSV (modelo/ + reportes/)."""
    d = Path(golden_dir)
    modelo = d / SUBDIR_MODELO
    reportes = d / SUBDIR_REPORTES

    personas = _parse_listas(pd.read_csv(modelo / "personas.csv"),
                             _COLS_LISTA_PERSONAS)
    slots = _parse_listas(pd.read_csv(modelo / "slots.csv"), _COLS_LISTA_SLOTS)
    candidatos = pd.read_csv(modelo / "candidatos.csv")
    cobertura = pd.read_csv(reportes / "cobertura.csv")
    resumen = json.loads((reportes / "resumen.json").read_text(encoding="utf-8"))
    return GoldenSet(personas, slots, candidatos, cobertura, resumen)
