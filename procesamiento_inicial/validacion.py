"""Capa 3 · Validación: matriz de elegibilidad + cobertura con causa por slot."""
from __future__ import annotations
import pandas as pd


def matriz_elegibilidad(candidatos, personas, slots) -> pd.DataFrame:
    """DataFrame booleano [codigo persona x slot_id]. True = viable."""
    M = pd.DataFrame(False, index=personas["codigo"].tolist(),
                     columns=list(slots["slot_id"]))
    for c in candidatos:
        M.at[c["codigo"], c["slot_id"]] = True
    return M


def _causa_principal(causas: dict) -> str:
    """Causa dominante (la más frecuente) por la que un slot no tiene candidato."""
    if not causas:
        return ""
    return max(causas.items(), key=lambda kv: kv[1])[0]


def reporte_cobertura(slots: pd.DataFrame, pref: dict) -> pd.DataFrame:
    por_slot = pref["candidatos_por_slot"]
    causa = pref["causa_por_slot"]
    df = slots[["slot_id", "equipo", "mesa", "proyecto", "rol_slot", "familia",
                "seniority_req", "requiere_interno"]].copy()
    df["n_candidatos"] = df["slot_id"].map(por_slot)
    df["cubrible"] = df["n_candidatos"] > 0
    df["causa_sin_candidato"] = df.apply(
        lambda r: "" if r["cubrible"] else _causa_principal(causa.get(r["slot_id"], {})),
        axis=1)
    return df


def resumen_cobertura(cob: pd.DataFrame) -> dict:
    sin = cob.loc[~cob["cubrible"]]
    return {
        "slots_totales": int(len(cob)),
        "slots_cubribles": int(cob["cubrible"].sum()),
        "slots_sin_candidato": int((~cob["cubrible"]).sum()),
        "causas_sin_candidato": sin["causa_sin_candidato"].value_counts().to_dict(),
        "detalle_sin_candidato": sin[["slot_id", "mesa", "rol_slot",
                                      "requiere_interno",
                                      "causa_sin_candidato"]].to_dict("records"),
    }
