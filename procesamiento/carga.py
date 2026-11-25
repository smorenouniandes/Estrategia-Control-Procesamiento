"""Capa 1 · Carga y normalización.

Produce `personas` (pool = staff Q4 ⨝ skills de DATA1) y `slots` (demanda DATA2),
según §2 del proceso estándar. Toda transformación se acumula en un reporte.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
import pandas as pd

from . import config as C
from .tiempo import (trimestres_2027_de, parse_trimestre, parse_fecha,
                     Q1_2027, Q4_2027)


# =========================================================================
# Reporte de normalización
# =========================================================================
@dataclass
class Reporte:
    notas: list[str] = field(default_factory=list)
    revision: list[dict] = field(default_factory=list)   # personas excluidas/BACKLOG

    def add(self, msg: str):
        self.notas.append(msg)

    def excluir(self, codigo, nombre, motivo, estado="EXCLUIDA"):
        self.revision.append({"codigo": codigo, "nombre": nombre,
                              "estado": estado, "motivo": motivo})

    def dump(self) -> str:
        return "\n".join(f"  - {n}" for n in self.notas)


# =========================================================================
# Normalizadores atómicos
# =========================================================================
def _parse_skill(valor) -> int:
    if pd.isna(valor):
        return 0
    if isinstance(valor, (int, float)):
        v = int(valor)
        return v if C.SKILL_MIN <= v <= C.SKILL_MAX else 0
    s = str(valor).strip().lower()
    return C.SKILL_LABEL_TO_INT.get(s, 0)


def _norm_seniority(valor) -> str:
    if pd.isna(valor):
        return C.SENIORITY_DESCONOCIDO
    s = str(valor).strip().lower()
    return C.SENIORITY_VALIDOS.get(s, C.SENIORITY_DESCONOCIDO)


def familia_persona(rol) -> str | None:
    """Familia ÚNICA que cubre la persona (LT/DEV/QA). None si no mapea.

    No se infiere LT por seniority. Un rol que ya venga normalizado a LT/DEV/QA
    se respeta tal cual.
    """
    if pd.isna(rol):
        return None
    s = str(rol).strip().lower()
    if s == "" or s.startswith(C.ROL_PERSONA_BASURA):
        return None
    if s.upper() in C.FAMILIAS_VALIDAS:          # rol ya normalizado
        return s.upper()
    for prefijo, fam in C.ROL_PERSONA_A_FAMILIA:
        if s.startswith(prefijo):
            return fam
    return None  # rol fuera de LT/DEV/QA -> se reporta, no se asume


# =========================================================================
# 1a. Skills (DATA1) como tabla de consulta por Código
# =========================================================================
def cargar_skills(rep: Reporte) -> pd.DataFrame:
    raw = pd.read_excel(C.DATA1_PATH, sheet_name="Hoja 1", header=None)
    nombres = raw.iloc[1].tolist()
    data = raw.iloc[2:].reset_index(drop=True)
    data.columns = nombres

    id_cols = nombres[:6]
    skill_cols = [c for i, c in enumerate(nombres)
                  if 6 <= i <= 158 and isinstance(c, str)]

    df = pd.DataFrame()
    df["codigo"] = data[id_cols[0]].astype("string").str.strip()
    df["nombre"] = data[id_cols[1]].astype("string").str.strip()
    df["tipo_recurso_d1"] = data[id_cols[2]].astype("string").str.strip()
    df["rol_principal"] = data[id_cols[4]]
    df["seniority"] = data[id_cols[5]].map(_norm_seniority)
    df["familia"] = df["rol_principal"].map(familia_persona)

    skill_matrix = {c: data[c].map(_parse_skill).values for c in skill_cols}
    skills_df = pd.DataFrame(skill_matrix, index=df.index)

    n0 = len(df)
    dup = df["codigo"].duplicated(keep="first")
    df = df[~dup].reset_index(drop=True)
    skills_df = skills_df.loc[~dup.values].reset_index(drop=True)
    rep.add(f"Skills (DATA1): {n0} filas; {int(dup.sum())} códigos duplicados "
            f"eliminados -> {len(df)} perfiles únicos.")

    df.attrs["skill_cols"] = skill_cols
    return df.join(skills_df.add_prefix("skill::"))


# =========================================================================
# 1a. Staff Q4 (DATA3) = POOL
# =========================================================================
def _libre_por_hoja(df, modo, col) -> pd.Series:
    val = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    tmp = pd.DataFrame({"cod": df["_cod"], "val": val})
    if modo == "compromiso":
        comprometido = tmp.groupby("cod")["val"].sum()
        return (1.0 - comprometido).clip(lower=0.0, upper=1.0)
    return tmp.groupby("cod")["val"].min().clip(lower=0.0, upper=1.0)


def _sdas_vigentes_por_persona(rep: Reporte) -> dict:
    """SDA que CONTINÚAN en el periodo de asignación (2027), por persona.

    Una SDA está vigente si su intervalo [inicio, fin] del staff se SOLAPA con
    2027 (Q1–Q4). Se recolecta, por persona, la lista de (sda, dedicación) de sus
    SDA vigentes, más su release_date. La MESA y la CAPACIDAD final se calculan
    después cruzando con la demanda (ver asignar_mesa_continuidad), porque:
      - la mesa de la SDA no está en el staff (columna vacía): sale de la demanda;
      - una SDA que no aparece en la demanda se ignora por completo [regla b].

    Devuelve dict[cod] = {"sdas_ded": {sda: dedicación}, "release_date": date}.
    """
    por_persona: dict[str, dict] = {}
    release: dict[str, object] = {}
    for hoja in C.HOJAS_ACTIVAS:
        m = C.STAFF_HOJAS[hoja]
        if not all(k in m for k in ("sda", "fecha_fin")):
            rep.add(f"[continuidad] hoja '{hoja}' sin sda/fecha_fin; omitida.")
            continue
        tiene_inicio = "Fecha Inicio" in pd.read_excel(
            C.DATA3_PATH, sheet_name=hoja, header=None, nrows=1).iloc[0].tolist()
        raw = pd.read_excel(C.DATA3_PATH, sheet_name=hoja, header=None)
        hdr = raw.iloc[0].tolist()
        df = raw.iloc[1:].copy(); df.columns = hdr
        df = df[df[m["codigo"]].notna()]
        _, cap_col = m["capacidad"]
        for _, r in df.iterrows():
            cod = str(r[m["codigo"]]).strip()
            ini_ord = parse_trimestre(r.get("Fecha Inicio")) if tiene_inicio else None
            fin_ord = parse_trimestre(r.get(m["fecha_fin"]))
            fin_date = parse_fecha(r.get(m["fecha_fin"]), fin_trimestre=True)
            if fin_date is not None and (release.get(cod) is None
                                         or fin_date > release[cod]):
                release[cod] = fin_date
            mt = re.search(r"(?i)\b(SDATOOL-\d+)\b", str(r.get(m["sda"], "")))
            sda = mt.group(1).upper() if mt else None
            if sda is None:
                continue
            # vigencia = solapamiento [inicio, fin] ∩ [Q1_2027, Q4_2027]
            lo = ini_ord if ini_ord is not None else Q1_2027  # sin inicio: conservador
            hi = fin_ord if fin_ord is not None else Q4_2027   # sin fin: conservador
            vigente = lo <= Q4_2027 and hi >= Q1_2027
            if not vigente:
                continue
            ded = pd.to_numeric(pd.Series([r.get(cap_col)]),
                                errors="coerce").fillna(0.0).iloc[0]
            info = por_persona.setdefault(cod, {"sdas_ded": {}, "release_date": None})
            # si la SDA se repite, acumula dedicación
            info["sdas_ded"][sda] = info["sdas_ded"].get(sda, 0.0) + float(ded)
    for cod in por_persona:
        por_persona[cod]["release_date"] = release.get(cod)
    rep.add(f"Continuidad: {len(por_persona)} personas con >=1 SDA vigente en 2027 "
            f"(solapamiento inicio–fin).")
    return por_persona


def cargar_staff(rep: Reporte) -> pd.DataFrame:
    piezas, peso_dir = [], []
    for hoja in C.HOJAS_ACTIVAS:
        m = C.STAFF_HOJAS[hoja]
        raw = pd.read_excel(C.DATA3_PATH, sheet_name=hoja, header=None)
        hdr = raw.iloc[0].tolist()
        df = raw.iloc[1:].copy(); df.columns = hdr
        df = df[df[m["codigo"]].notna()].copy()
        df["_cod"] = df[m["codigo"]].astype(str).str.strip()

        modo, col = m["capacidad"]
        val = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        dom_col = m.get("dominio")
        dom_vals = (df[dom_col].astype(str).str.strip().str.upper().values
                    if dom_col and dom_col in df.columns
                    else [""] * len(df))
        tmp = pd.DataFrame({
            "cod": df["_cod"].values,
            "direccion": df[m["direccion"]].astype(str).str.strip().values,
            "empresa": df[m["empresa"]].astype(str).str.strip().values,
            "interno": df[m["interno"]].astype(str).str.strip().values,
            "rol": df[m["rol"]].astype(str).str.strip().values,
            "dominio": dom_vals,
            "peso": val.values,
        })
        attrs = tmp.groupby("cod").agg(empresa=("empresa", "first"),
                                       interno=("interno", "first"),
                                       rol=("rol", "first"),
                                       dominio=("dominio", "first"))
        piezas.append(attrs.reset_index())
        peso_dir.append(tmp.groupby(["cod", "direccion"])["peso"].sum().reset_index())
        rep.add(f"[{hoja}] filas={len(df)} personas={df['_cod'].nunique()} "
                f"modo='{modo}'.")

    allp = pd.concat(piezas, ignore_index=True)
    pesos = pd.concat(peso_dir, ignore_index=True)
    pesos_g = pesos.groupby(["cod", "direccion"])["peso"].sum().reset_index()
    idx = pesos_g.groupby("cod")["peso"].idxmax()
    dir_final = pesos_g.loc[idx].set_index("cod")["direccion"]
    attrs_final = allp.drop_duplicates("cod", keep="first").set_index("cod")

    pool = pd.DataFrame({"codigo": attrs_final.index})
    pool["direccion"] = pool["codigo"].map(dir_final)
    pool["empresa"] = pool["codigo"].map(attrs_final["empresa"])
    pool["rol_staff"] = pool["codigo"].map(attrs_final["rol"])
    tipo = pool["codigo"].map(attrs_final["interno"]).str.lower()
    pool["es_interno"] = tipo == C.STAFF_INTERNO_VALOR

    # --- dominio REAL de la OFERTA (staff): debe ser único ---
    pool["dominio"] = pool["codigo"].map(attrs_final["dominio"]).fillna("")
    presentes = sorted(d for d in pool["dominio"].unique() if d)
    rep.add(f"Dominio(s) reales en el staff (oferta): {presentes or ['(vacío)']}.")
    if len(presentes) > 1:
        raise ValueError(
            f"La OFERTA (staff) trae más de un dominio {presentes}. Este pipeline "
            f"asigna un único dominio por corrida. Revisa la carga de DATA3 o "
            f"separa la data por dominio.")
    # el dominio de la corrida lo FIJA el dato de oferta (no la config)
    dominio_oferta = presentes[0] if presentes else C.DOMINIO_ASIGNACION
    pool.attrs["dominio_oferta"] = dominio_oferta
    sin_dom = int((pool["dominio"] == "").sum())
    if sin_dom:
        rep.add(f"[dominio] {sin_dom} personas sin dominio en el staff "
                f"(no coincidirán; se reportarán en el prefiltrado).")

    # --- SDA vigentes por persona (mesa + capacidad se calculan tras los slots) ---
    vig = _sdas_vigentes_por_persona(rep)
    # sdas_vigentes_2027 = conjunto de SDA vigentes (todas, antes de cruzar demanda)
    pool["sdas_vigentes_2027"] = pool["codigo"].map(
        lambda c: frozenset(vig.get(c, {}).get("sdas_ded", {}).keys()))
    pool["release_date"] = pool["codigo"].map(
        lambda c: vig.get(c, {}).get("release_date"))
    # dedicación por SDA vigente (dict), insumo para capacidad tras cruzar demanda
    pool["_sdas_ded"] = pool["codigo"].map(
        lambda c: vig.get(c, {}).get("sdas_ded", {}))
    # placeholders; se completan en asignar_mesa_continuidad()
    pool["mesa_continuidad"] = None
    pool["capacidad_comprometida"] = 0.0
    pool["capacidad_libre"] = 1.0

    rep.add(f"Pool staff Q4: {len(pool)} personas únicas.")
    rep.add(f"Interno/externo: "
            f"{pool['es_interno'].map({True:'int',False:'ext'}).value_counts().to_dict()}.")
    return pool


# =========================================================================
# 1a. Construir el pool (staff ⨝ skills) con validación cruzada int/ext
# =========================================================================
def construir_pool(staff: pd.DataFrame, skills: pd.DataFrame,
                   rep: Reporte) -> pd.DataFrame:
    dominio_oferta = staff.attrs.get("dominio_oferta", C.DOMINIO_ASIGNACION)
    pool = staff.merge(skills, on="codigo", how="left", suffixes=("", "_d1"))

    # staff sin perfil en DATA1 -> excluir (no hay skills -> inservible)
    sin_skills = pool["seniority"].isna()
    for _, r in pool[sin_skills].iterrows():
        rep.excluir(r["codigo"], r.get("nombre"), "Sin perfil de skills en DATA1")
    if int(sin_skills.sum()):
        rep.add(f"Excluidas {int(sin_skills.sum())} personas del staff sin skills "
                f"en DATA1.")
        pool = pool[~sin_skills].reset_index(drop=True)

    # validación cruzada int/ext (staff = autoritativo; se reporta discrepancia)
    d1 = pool["tipo_recurso_d1"].astype("string").str.strip().str.lower()
    d1_interno = d1.eq("interno")
    discrepa = pool["tipo_recurso_d1"].notna() & (d1_interno != pool["es_interno"])
    if int(discrepa.sum()):
        rep.add(f"[int/ext] {int(discrepa.sum())} discrepancias staff vs DATA1 "
                f"(prevalece staff Q4).")

    # sin familia LT/DEV/QA -> no asignable. Se REPORTA con el rol crudo para que
    # se corrija en origen; no se descarta en silencio.
    sin_fam = pool["familia"].isna()
    for _, r in pool[sin_fam].iterrows():
        rep.excluir(r["codigo"], r.get("nombre"),
                    f"Rol fuera de LT/DEV/QA: '{r.get('rol_principal')}'",
                    estado="EXCLUIDA")
    if int(sin_fam.sum()):
        rep.add(f"Excluidas {int(sin_fam.sum())} personas con rol fuera de "
                f"LT/DEV/QA (ver revision_personas.csv).")
        pool = pool[~sin_fam].reset_index(drop=True)

    rep.add(f"Pool final (staff ⨝ skills, familia LT/DEV/QA): {len(pool)}.")
    rep.add(f"Familias del pool: {pool['familia'].value_counts().to_dict()}.")
    pool.attrs["dominio_oferta"] = dominio_oferta
    return pool


# =========================================================================
# 1b. Demanda / slots (DATA2)
# =========================================================================
def cargar_slots(rep: Reporte, dominio_oferta: str | None = None) -> pd.DataFrame:
    raw = pd.read_excel(C.DATA2_PATH, sheet_name="Hoja 1", header=None)
    hdr = raw.iloc[1].tolist()
    d2 = raw.iloc[2:].reset_index(drop=True)
    d2.columns = hdr

    proj_cols = ["Mesa", "Foco estratégico (Fábrica)", "SDATOOL", "Nombre Proyecto",
                 "Fecha Inicio", "Fecha Fin", "Dirección", "Estado"]
    for c in proj_cols:
        if c in d2.columns:
            d2[c] = d2[c].ffill()
    d2 = d2[d2["Rol"].notna()].reset_index(drop=True)

    base = pd.DataFrame()
    base["mesa"] = d2["Mesa"].astype("string").str.strip()
    base["direccion"] = d2["Dirección"].astype("string").str.strip()
    base["fabrica"] = d2["Foco estratégico (Fábrica)"].astype("string").str.strip()
    base["proyecto"] = d2["Nombre Proyecto"].astype("string").str.strip()
    base["rol_slot"] = d2["Rol"].astype("string").str.strip()
    base["seniority_req"] = d2["Seniority"].astype("string").str.strip()
    base["equipo"] = (base["mesa"].fillna("?") + " | " + base["direccion"].fillna("?")
                      + " | " + base["fabrica"].fillna("?"))

    est = d2["Estado"].astype("string").str.strip()
    base["estado"] = est.where(est.isin(["Stock", "Flow"]), other="Flow")
    sda = d2["SDATOOL"].astype("string").str.strip()
    valida = sda.str.match(r"(?i)^SDATOOL-\d+$", na=False)
    base["sda"] = sda.where(valida, other=pd.NA)

    base["fecha_inicio_orig"] = d2["Fecha Inicio"].astype("string").str.strip()
    base["fecha_fin_orig"] = d2["Fecha Fin"].astype("string").str.strip()
    base["trimestres"] = [trimestres_2027_de(i, f)
                          for i, f in zip(base["fecha_inicio_orig"],
                                          base["fecha_fin_orig"])]
    base["familia"] = base["rol_slot"].str.lower().map(C.ROL_SLOT_A_FAMILIA)

    # --- dominio único por corrida, desde el DATO REAL de la demanda ---
    # Si DATA2 trae columna de dominio, se usa (debe ser un único valor). Si no,
    # se deriva de la Dirección, y si tampoco, se cae a DOMINIO_ASIGNACION.
    # Luego se EXIGE que coincida con el dominio de la oferta (staff): si no
    # coincide, aborta (protege ante fallo humano al cargar la data).
    col_dom = C.DOMINIO_COL_DEMANDA
    if col_dom in d2.columns:
        doms = (d2[col_dom].astype("string").str.strip().str.upper()
                .dropna().unique().tolist())
        doms = [d for d in doms if d]
        if len(doms) > 1:
            raise ValueError(
                f"La DEMANDA trae más de un dominio {doms}; este pipeline asigna "
                f"un solo dominio por corrida. Separa la data por dominio.")
        dominio_demanda = doms[0] if doms else None
        fuente = f"columna '{col_dom}'"
    else:
        dominio_demanda = None
        fuente = "(sin columna de dominio)"

    if dominio_demanda is None:
        # sin dato explícito en la demanda: usa el de la oferta si existe, o config
        dominio_demanda = (dominio_oferta or C.DOMINIO_ASIGNACION)
        fuente += " -> se toma el de la oferta/config"

    # validación de coincidencia oferta ↔ demanda
    if dominio_oferta and dominio_demanda and dominio_oferta != dominio_demanda:
        raise ValueError(
            f"DISCREPANCIA DE DOMINIO: oferta (staff)='{dominio_oferta}' vs "
            f"demanda (DATA2)='{dominio_demanda}'. Deben coincidir. Revisa la "
            f"carga de datos (posible error humano al subir la información).")

    dominio = dominio_demanda
    base["dominio"] = dominio
    rep.add(f"Dominio de la demanda: {dominio} [{fuente}].")
    if dominio_oferta:
        rep.add(f"[dominio] coincidencia oferta↔demanda OK: '{dominio}'.")

    # --- SDA consolidada por grupo Mesa + Foco estratégico (Fábrica) ---
    # Cada fila conserva su SDA individual en 'sda', pero 'sdas_grupo' lleva la
    # lista deduplicada de todas las SDA válidas del grupo (Mesa, Fábrica), que es
    # la base de la continuidad (decisión del 24-nov con Optimizacion).
    base["grupo_mesa_foco"] = (base["mesa"].fillna("?") + " | "
                               + base["fabrica"].fillna("?"))
    sdas_por_grupo = (base[base["sda"].notna()]
                      .groupby("grupo_mesa_foco")["sda"]
                      .agg(lambda s: frozenset(s.dropna())).to_dict())
    base["sdas_grupo"] = base["grupo_mesa_foco"].map(
        lambda g: sdas_por_grupo.get(g, frozenset()))

    internal = pd.to_numeric(d2["Internal"], errors="coerce").fillna(0)
    external = pd.to_numeric(d2["External"], errors="coerce").fillna(0)

    hab_cols = [c for c in d2.columns if isinstance(c, str)
                and "Habilidad" in c and "sugerida" not in c.lower()]

    def _skills_slot(row):
        return [str(row[c]).strip() for c in hab_cols
                if pd.notna(row[c]) and isinstance(row[c], str) and row[c].strip()]
    base["skills_obligatorias"] = d2.apply(_skills_slot, axis=1)

    # expansión a plazas de 1 FTE (una por unidad Internal/External)
    filas = []
    sid = 0
    for i, row in base.iterrows():
        n_int = int(internal.iloc[i])
        n_ext = int(external.iloc[i])
        for requiere_interno, n in ((True, n_int), (False, n_ext)):
            for _ in range(max(0, n)):
                r = row.to_dict()
                r["slot_id"] = f"S{sid:03d}"
                r["requiere_interno"] = requiere_interno
                filas.append(r)
                sid += 1
    slots = pd.DataFrame(filas)

    n_fam_na = int(slots["familia"].isna().sum()) if len(slots) else 0
    rep.add(f"Demanda: {len(base)} filas -> {len(slots)} plazas (1 FTE c/u).")
    rep.add(f"Equipos (Mesa,Dir,Fábrica): {slots['equipo'].nunique() if len(slots) else 0}.")
    rep.add(f"Familias de slot: "
            f"{slots['familia'].value_counts(dropna=False).to_dict() if len(slots) else {}}"
            + (f" | AVISO {n_fam_na} sin familia" if n_fam_na else ""))
    if len(slots):
        rep.add(f"Requieren interno: {int(slots['requiere_interno'].sum())}; "
                f"externo: {int((~slots['requiere_interno']).sum())}.")

    slots.attrs["hab_cols"] = hab_cols
    # 'sdas_grupo' (consolidada por Mesa+Foco) viaja en cada plaza desde 'base'
    # y es la base de la continuidad en el prefiltrado.
    return slots


# =========================================================================
# 1c. Mesa de continuidad + capacidad real (cruza SDA de la persona con la demanda)
# =========================================================================
def asignar_mesa_continuidad(personas: pd.DataFrame, slots: pd.DataFrame,
                             rep: Reporte) -> pd.DataFrame:
    """Determina, por persona, su mesa de continuidad y su capacidad libre.

    La relación SDA->mesa NO está en el staff (columna vacía): se toma de la
    DEMANDA. Para cada SDA vigente de la persona (de `_sdas_ded`), se busca en qué
    grupo Mesa+Foco de la demanda aparece esa SDA (`sdas_grupo`).

    Regla (24-nov):
      1. agrupa las SDA vigentes de la persona por grupo Mesa+Foco de la demanda;
      2. una SDA que NO está en ninguna mesa de la demanda se IGNORA (ni mesa ni
         capacidad) [regla b];
      3. elige la mesa con MÁS SDA de continuidad; empate -> mayor SUMA de dedicación;
      4. capacidad_comprometida = suma de dedicación de las SDA de esa mesa;
         capacidad_libre = 1 - comprometida (piso 0);
      5. mesa_continuidad = ese grupo (el modelo la respeta como asignación fija).
    Sin SDA de continuidad presente en la demanda -> libre = 1.0, sin mesa.
    """
    if C.CAPACIDAD_UNIFORME:
        personas["capacidad_libre"] = 1.0
        personas = personas.drop(columns=["_sdas_ded"], errors="ignore")
        rep.add("[CAPACIDAD_UNIFORME] capacidad real ignorada; todas al 100%.")
        return personas

    # mapa SDA -> grupo(s) Mesa+Foco de la demanda
    sda_a_grupos: dict[str, set] = {}
    if len(slots):
        for _, s in slots.drop_duplicates("grupo_mesa_foco").iterrows():
            for sda in _como_set_sdas(s.get("sdas_grupo")):
                sda_a_grupos.setdefault(sda, set()).add(s["grupo_mesa_foco"])

    mesas, comprometidas, libres = [], [], []
    n_con = 0
    for _, p in personas.iterrows():
        sdas_ded = p.get("_sdas_ded") or {}
        # agrupa dedicación por grupo de la demanda; SDA no presente -> ignorada
        por_grupo: dict[str, list] = {}
        for sda, ded in sdas_ded.items():
            for g in sda_a_grupos.get(sda, ()):   # vacío si la SDA no está en demanda
                e = por_grupo.setdefault(g, [set(), 0.0])
                e[0].add(sda); e[1] += ded
        if por_grupo:
            mesa_sel = max(por_grupo.items(),
                           key=lambda kv: (len(kv[1][0]), kv[1][1]))[0]
            comp = min(1.0, por_grupo[mesa_sel][1])
            mesas.append(mesa_sel)
            comprometidas.append(round(comp, 4))
            libres.append(round(max(0.0, 1.0 - comp), 4))
            n_con += 1
        else:
            mesas.append(None); comprometidas.append(0.0); libres.append(1.0)

    personas = personas.copy()
    personas["mesa_continuidad"] = mesas
    personas["capacidad_comprometida"] = comprometidas
    personas["capacidad_libre"] = libres
    personas = personas.drop(columns=["_sdas_ded"], errors="ignore")
    libre_media = sum(libres) / max(1, len(libres))
    rep.add(f"[capacidad real] {n_con} personas con continuidad en una mesa de la "
            f"demanda (mesa fija + capacidad reducida); resto al 100%.")
    rep.add(f"[capacidad real] capacidad libre media del pool: {libre_media:.2f} FTE.")
    return personas


def _como_set_sdas(v):
    """Normaliza sdas_grupo (lista/frozenset/str JSON) a set."""
    if isinstance(v, (set, frozenset)):
        return set(v)
    if isinstance(v, (list, tuple)):
        return set(v)
    if isinstance(v, str) and v.strip():
        import json
        try:
            return set(json.loads(v))
        except Exception:
            return set()
    return set()
