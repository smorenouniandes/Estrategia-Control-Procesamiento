"""Capa 2 · Prefiltrado: reglas duras (poda) + score blando (preferencia).

`es_elegible` aplica las reglas duras de §3.1 del proceso. `score` calcula la
preferencia según MODO_SCORE (§3.2). El prefiltrado reduce variables y adjunta
el score; no decide la asignación.
"""
from __future__ import annotations
import pandas as pd

from . import config as C


# =========================================================================
# helpers de skills / seniority
# =========================================================================
def _nivel_skill(persona_row, skill_nombre: str) -> int:
    col = f"skill::{skill_nombre}"
    if col in persona_row.index:
        v = persona_row[col]
        return int(v) if pd.notna(v) else 0
    return 0


def skills_cubiertas(persona_row, skills_obligatorias) -> int:
    """Nº de skills obligatorias que la persona posee (nivel >= 1)."""
    return sum(1 for s in skills_obligatorias if _nivel_skill(persona_row, s) >= 1)


def skills_faltantes(persona_row, skills_obligatorias) -> list[str]:
    return [s for s in skills_obligatorias if _nivel_skill(persona_row, s) == 0]


def seniority_match(seniority_persona, seniority_slot) -> str:
    sp = C.SENIORITY_ORDEN.get(str(seniority_persona).strip())
    ss = (C.SENIORITY_ORDEN.get(str(seniority_slot).strip())
          if pd.notna(seniority_slot) else None)
    if sp is None or ss is None:
        return "sin_dato"
    if sp == ss:
        return "coincide"
    return "por_encima" if sp > ss else "por_debajo"


# =========================================================================
# Reglas duras (§3.1)
# =========================================================================
def es_elegible(persona_row, slot_row) -> tuple[bool, str]:
    """(elegible, causa_de_rechazo). Causa vacía si elegible."""
    familia = slot_row["familia"]
    if pd.isna(familia):
        return False, "slot_sin_familia"

    # dominio único (duro): persona y slot deben coincidir en el dominio activo
    if slot_row.get("dominio") and persona_row.get("dominio") != slot_row["dominio"]:
        return False, "dominio"

    # familia de rol (UNA sola familia por persona: LT/DEV/QA)
    if familia == C.FAMILIA_LT:
        # LT = Lead + interno (no admite sustitución de tipo). La persona además
        # debe ser de familia LT (no se infiere LT por seniority).
        if persona_row.get("familia") != C.FAMILIA_LT:
            return False, "familia"
        if not (persona_row["seniority"] == "Lead" and bool(persona_row["es_interno"])):
            return False, "lt_requiere_lead_interno"
        if not bool(slot_row["requiere_interno"]):
            return False, "lt_requiere_interno"
    else:
        if persona_row.get("familia") != familia:
            return False, "familia"
        # interno/externo
        if bool(slot_row["requiere_interno"]) != bool(persona_row["es_interno"]):
            if not C.SUSTITUCION_INT_EXT:
                return False, "int_ext"
            # con sustitución permitida: pasa, se marca luego en el score/salida

    # seniority (duro si SENIORITY_DURA)
    if C.SENIORITY_DURA:
        estado = seniority_match(persona_row["seniority"], slot_row["seniority_req"])
        if estado == "sin_dato":
            return False, "seniority_sin_dato"
        sp = C.SENIORITY_ORDEN.get(persona_row["seniority"])
        ss = C.SENIORITY_ORDEN.get(str(slot_row["seniority_req"]).strip())
        if sp is None or ss is None or abs(sp - ss) > 1:
            return False, "seniority"

    # skills obligatorias (regla 6).
    #   - Si el slot declara skills: la persona debe cubrir >= SKILLS_MIN_OBLIGATORIAS
    #     (cualquier nivel positivo cuenta; no hay umbral de nivel por seniority).
    #   - Si el slot NO declara skills: es el "respaldo sin skills". Solo se admite
    #     para QA (si QA_SIN_SKILLS_OK) y SIEMPRE exige coincidencia de Dominio.
    oblig = slot_row["skills_obligatorias"]
    if len(oblig):
        if skills_cubiertas(persona_row, oblig) < C.SKILLS_MIN_OBLIGATORIAS:
            return False, "skills"
    else:
        if familia != C.FAMILIA_QA or not C.QA_SIN_SKILLS_OK:
            return False, "slot_sin_skills"
        # respaldo sin skills: exige dominio explícito (regla 6)
        if not slot_row.get("dominio") or persona_row.get("dominio") != slot_row["dominio"]:
            return False, "respaldo_sin_skills_sin_dominio"

    # fecha de liberación
    rel = persona_row.get("release_date")
    from .tiempo import parse_fecha, Q1_2027  # import local para evitar ciclo
    from datetime import date
    inicio = parse_fecha(slot_row.get("fecha_inicio_orig")) or date(2027, 1, 1)
    if rel is not None and rel >= inicio:
        return False, "liberacion"

    return True, ""


# =========================================================================
# Sustitución y continuidad
# =========================================================================
def es_sustitucion(persona_row, slot_row) -> bool:
    return bool(slot_row["requiere_interno"]) != bool(persona_row["es_interno"])


def _como_set(v):
    if isinstance(v, (set, frozenset)):
        return set(v)
    if isinstance(v, (list, tuple)):
        return set(v)
    return set()


def tiene_continuidad(persona_row, slot_row) -> bool:
    """Continuidad: la persona trae una SDA vigente 2027 que está en la lista
    consolidada de SDA del grupo Mesa+Foco del slot."""
    suyos = _como_set(persona_row.get("sdas_vigentes_2027"))
    grupo = _como_set(slot_row.get("sdas_grupo"))
    return len(suyos & grupo) > 0


def dominio_afin(persona_row, slot_row) -> bool:
    return bool(slot_row.get("dominio") and
                persona_row.get("dominio") == slot_row["dominio"])


# =========================================================================
# Score blando (§3.2)
# =========================================================================
def _fit_seniority(sp, ss) -> float:
    estado = seniority_match(sp, ss)
    if estado == "sin_dato":
        return C.FIT_SENIORITY_SIN_DATO
    if estado == "coincide":
        return C.FIT_SENIORITY_COINCIDE
    if estado == "por_encima":
        return C.FIT_SENIORITY_POR_ENCIMA
    dist = (C.SENIORITY_ORDEN[str(ss).strip()] - C.SENIORITY_ORDEN[str(sp).strip()])
    return max(0.0, 1.0 - C.FIT_SENIORITY_PASO_DEBAJO * dist)


def score(persona_row, slot_row) -> dict:
    """Devuelve componentes + score escalar según MODO_SCORE.

    Siempre expone las componentes crudas para que cualquier motor arme su
    propio criterio; `score` es el escalar listo para ordenar/maximizar.
    """
    oblig = slot_row["skills_obligatorias"]
    n_cubiertas = skills_cubiertas(persona_row, oblig)
    cont = int(tiene_continuidad(persona_row, slot_row))
    dom = int(dominio_afin(persona_row, slot_row))
    sen_estado = seniority_match(persona_row["seniority"], slot_row["seniority_req"])

    # regla 4 (Opción 1): el mínimo deseable es SKILLS_PREFERIDAS (=2). Quien cubre
    # ese mínimo NO se penaliza; quien cubre menos (p.ej. 1) sí. El fallback a 1
    # skill lo resuelve el modelo prefiriendo los de >=2 y cayendo a 1 solo si no
    # hay opción. La excepción QA sin skills obligatorias se trata aparte.
    cumple_pref_skills = int(len(oblig) == 0 or n_cubiertas >= C.SKILLS_PREFERIDAS)

    comp = {
        "continuidad": cont,
        "dominio": dom,
        "n_skills_cubiertas": n_cubiertas,
        "n_obligatorias": len(oblig),
        "cumple_pref_skills": cumple_pref_skills,   # 1 si cubre >=2 (sin castigo)
        "seniority_match": sen_estado,
        "sustitucion_int_ext": int(es_sustitucion(persona_row, slot_row)),
    }

    if C.MODO_SCORE == "ponderado":
        fs = (n_cubiertas / (len(oblig) * 1.0)) if oblig else 0.5
        fsen = _fit_seniority(persona_row["seniority"], slot_row["seniority_req"])
        base = C.W_FIT_SKILLS * fs + C.W_FIT_SENIORITY * fsen
        # castigo si no alcanza el mínimo preferido de skills (regla 4)
        castigo = 0.0 if cumple_pref_skills else C.PENALIZACION_SKILLS_PARCIAL
        comp["score"] = round(base + (C.BONUS_CONTINUIDAD if cont else 0.0) - castigo, 4)
    else:  # lexicográfico: continuidad > dominio > cumple_pref_skills > nº skills > seniority
        rango_sen = {"coincide": 3, "por_encima": 2, "por_debajo": 1, "sin_dato": 0}
        # 'cumple_pref_skills' pesa por encima del conteo lineal: así 2+ skills
        # siempre gana a 1 skill (castigo de la regla 4), sin mezclar niveles.
        comp["score"] = (cont * 10_000_000 + dom * 1_000_000
                         + cumple_pref_skills * 100_000
                         + n_cubiertas * 100 + rango_sen[sen_estado])
    return comp


# =========================================================================
# Construcción de candidatos
# =========================================================================
def construir_candidatos(personas: pd.DataFrame, slots: pd.DataFrame):
    """Lista de dicts candidatos viables + reporte de poda por slot."""
    candidatos = []
    por_slot = {s: 0 for s in slots["slot_id"]}
    causa_por_slot = {s: {} for s in slots["slot_id"]}

    personas_idx = personas.index.tolist()
    for _, slot in slots.iterrows():
        sid = slot["slot_id"]
        for i in personas_idx:
            p = personas.loc[i]
            ok, causa = es_elegible(p, slot)
            if ok:
                sc = score(p, slot)
                candidatos.append({
                    "idx_persona": i, "codigo": p["codigo"], "slot_id": sid,
                    **sc,
                })
                por_slot[sid] += 1
            else:
                causa_por_slot[sid][causa] = causa_por_slot[sid].get(causa, 0) + 1

    total = len(personas) * len(slots)
    reporte = {
        "combinaciones_posibles": total,
        "combinaciones_viables": len(candidatos),
        "reduccion_pct": 100.0 * (1 - len(candidatos) / total) if total else 0.0,
        "candidatos_por_slot": por_slot,
        "causa_por_slot": causa_por_slot,
        "slots_sin_candidato": [s for s, n in por_slot.items() if n == 0],
    }
    return candidatos, reporte
