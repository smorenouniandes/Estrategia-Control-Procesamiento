"""Utilidades de tiempo: trimestres, recorte a 2027 y parseo de fechas.

Las fechas vienen como trimestres en texto, con formato inconsistente
('1Q 2027', 'Q2 2027', ...) o como fechas/serial Excel. Se normalizan a un
entero ordinal = año*4 + (trimestre-1) para comparar y recortar. El modelo
trabaja sobre los 4 trimestres de 2027.
"""
from __future__ import annotations
import re
from datetime import date, datetime, timedelta
import pandas as pd

from . import config as C

Q1_2027 = 2027 * 4 + 0
Q4_2027 = 2027 * 4 + 3


def parse_trimestre(txt) -> int | None:
    """'1Q 2027' o 'Q1 2027' -> ordinal (año*4 + q-1). None si no parsea."""
    if pd.isna(txt):
        return None
    s = str(txt).strip().upper()
    q = re.search(r"\b([1-4])\s*Q\b|\bQ\s*([1-4])\b", s)
    y = re.search(r"(20\d{2})", s)
    if not q or not y:
        return None
    qn = int(q.group(1) or q.group(2))
    yr = int(y.group(1))
    return yr * 4 + (qn - 1)


def trimestres_2027_de(inicio, fin) -> list[str]:
    """Trimestres de 2027 que cubre [inicio, fin], recortados a 2027.

    Sin fechas válidas -> los 4 trimestres de 2027 (caso conservador).
    """
    a = parse_trimestre(inicio)
    b = parse_trimestre(fin)
    if a is None or b is None:
        return list(C.TRIMESTRES_2027)
    lo = max(a, Q1_2027)
    hi = min(b, Q4_2027)
    if lo > hi:
        return []
    out = []
    for ordv in range(lo, hi + 1):
        yr, q = divmod(ordv, 4)
        out.append(f"{q + 1}Q {yr}")
    return out


def parse_fecha(valor, *, fin_trimestre: bool = False) -> date | None:
    """Parsea fecha desde trimestre textual, formatos comunes o serial Excel.

    fin_trimestre=True -> para un trimestre devuelve su último día.
    """
    s = str(valor or "").strip()
    if not s:
        return None
    m = re.search(r"(?i)([1-4])\s*Q\s*(\d{4})|Q\s*([1-4])\s*(\d{4})", s)
    if m:
        q = int(m.group(1) or m.group(3))
        yr = int(m.group(2) or m.group(4))
        if fin_trimestre:
            mes = q * 3
            nxt_m, nxt_y = (1, yr + 1) if mes == 12 else (mes + 1, yr)
            return date(nxt_y, nxt_m, 1) - timedelta(days=1)
        return date(yr, (q - 1) * 3 + 1, 1)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    try:
        serial = float(s)
        if 20000 <= serial <= 80000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
    except ValueError:
        pass
    return None
