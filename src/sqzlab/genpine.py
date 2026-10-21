"""Genera los Pine a partir de params/{h4,d1,w1}.json (fuente de verdad de los parametros).

  pine/h4/sqz_rsi_strategy_h4.pine, pine/d1/..._d1.pine, pine/w1/..._w1.pine : un script por temporalidad
  pine/sqz_rsi_strategy_unified.pine : un solo script con los 3 presets, elegidos solos con timeframe.in_seconds()
  pine/sqz_rsi_senales_unified.pine : el indicador v8 (ref/sqz_rsi_senales_v8.pine) con los mismos presets (Fase 6.5)

Regla del proyecto: UN set de parametros por temporalidad, NUNCA por moneda. Los .pine generados no se editan a mano:
se cambia el JSON y se regenera. Base: ref/sqz_rsi_strategy_v2.pine (solo lectura; solo cambian los defaults de los
inputs, el titulo y, en el unificado, el bloque de presets).

Uso:  python -m sqzlab.genpine [--init-params]
  --init-params  crea params/*.json con los defaults de la v2 SOLO si no existen (nunca pisa).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "ref" / "sqz_rsi_strategy_v2.pine"
REF_IND = ROOT / "ref" / "sqz_rsi_senales_v8.pine"
TFS = {"h4": "H4", "d1": "D1", "w1": "W1"}
INPUT_RE = re.compile(r'^(?P<name>\w+)(?P<eq>\s*=\s*)input\.(?P<typ>bool|int|float|string)\((?P<default>[^,]+),(?P<rest>.*)$')
TITLE_RE = re.compile(r'strategy\("SQZ\+RSI A\+B\+C\+D Backtest", shorttitle="SQZ\+RSI BT"')
# Casillas de "Que probar": en el unificado NO las pisa el preset (salvo que el usuario no marque su interruptor);
# riesgo y apalancamiento: siempre son inputs del usuario, el preset no los toca.
WHAT_TO_TEST = ["useA", "useB", "useC", "aLong", "aShort", "bLong", "bShort", "cLong", "cShort", "useD", "dLong", "dShort"]
USER_ALWAYS = ["riskPct", "maxLev"]
MINE_INPUT = ('useMine = input.bool(false, "Que probar: usar mis casillas (en vez del preset)", group="Que probar", '
              'tooltip="Apagado: las casillas de Que probar siguen al preset de la temporalidad. Prendido: valen las que tildes abajo, '
              'para aislar senales o lados.")')
PRESET_NOTE = "Auto: <1d -> H4, 1d a <1w -> D1, >=1w -> W1. Solo 4h, 1D y 1W estan calibrados."


def read_ref() -> list[str]:
    return REF.read_text(encoding="utf-8").splitlines()


def pine_defaults(lines: list[str]) -> dict:
    out = {}
    for ln in lines:
        m = INPUT_RE.match(ln)
        if m:
            out[m["name"]] = parse_literal(m["default"].strip(), m["typ"])
    return out


def parse_literal(tok: str, typ: str):
    if typ == "bool":
        return tok == "true"
    if typ == "int":
        return int(tok)
    if typ == "float":
        return float(tok)
    return tok.strip('"')


def pine_literal(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return repr(v)


def load_params(tf: str) -> dict:
    d = json.loads((ROOT / "params" / f"{tf}.json").read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def init_params() -> None:
    defaults = pine_defaults(read_ref())
    (ROOT / "params").mkdir(exist_ok=True)
    for tf, label in TFS.items():
        p = ROOT / "params" / f"{tf}.json"
        if p.exists():
            print(f"{p.name}: ya existe, no se pisa")
            continue
        doc = {"_meta": {"timeframe": label, "status": "SIN OPTIMIZAR: defaults de ref/sqz_rsi_strategy_v2.pine",
                         "scope": "un set por temporalidad, nunca por moneda",
                         "keys": "nombres EXACTOS de las variables de input del Pine"}, **defaults}
        p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{p.name}: creado")


def per_tf(lines: list[str], params: dict, label: str) -> str:
    out = []
    for ln in lines:
        m = INPUT_RE.match(ln)
        if m and m["name"] in params:
            ln = f'{m["name"]}{m["eq"]}input.{m["typ"]}({pine_literal(params[m["name"]])},{m["rest"]}'
        elif TITLE_RE.search(ln):
            ln = TITLE_RE.sub(f'strategy("SQZ+RSI A+B+C+D Backtest {label}", shorttitle="SQZ+RSI BT {label}"', ln)
        out.append(ln)
    hdr = [f"// GENERADO por src/sqzlab/genpine.py desde params/{label.lower()}.json. NO editar a mano.",
           f"// Set de parametros de la temporalidad {label} (el mismo para todas las monedas). NO COMPILADO en TradingView."]
    return "\n".join(out[:1] + hdr + out[1:]) + "\n"


def unified(lines: list[str], sets: dict[str, dict]) -> str:
    out, names = [], []
    for ln in lines:
        m = INPUT_RE.match(ln)
        if m and m["name"] in sets["d1"]:
            n = m["name"]
            lit = pine_literal(sets["d1"][n])
            if n in USER_ALWAYS:       # siempre del usuario: mismo nombre, sin preset
                ln = f'{n}{m["eq"]}input.{m["typ"]}({lit},{m["rest"]}'
            else:
                names.append(n)
                if n == WHAT_TO_TEST[0]:
                    out.append(MINE_INPUT)
                ln = f'm_{n}{m["eq"]}input.{m["typ"]}({lit},{m["rest"]}'
        elif TITLE_RE.search(ln):
            ln = TITLE_RE.sub('strategy("SQZ+RSI A+B+C+D Backtest UNIFICADO", shorttitle="SQZ+RSI BT AUTO"', ln)
        out.append(ln)
    # el bloque de presets va justo antes de "// ===== Squeeze y momentum =====" (despues de todos los inputs)
    at = next(i for i, ln in enumerate(out) if ln.startswith("// ===== Squeeze y momentum"))
    blk = [
        "// ===== Presets por temporalidad (GENERADO por src/sqzlab/genpine.py desde params/*.json; NO editar a mano) =====",
        "// Un set por temporalidad, nunca por moneda. " + PRESET_NOTE,
        "// Los parametros optimizables siguen al preset. Las casillas de Que probar siguen al preset solo si NO tildas",
        "// 'usar mis casillas'. Riesgo por trade y apalancamiento maximo son siempre tuyos (el preset no los toca).",
        "// Manual = todo sale de los campos de las pestanas de arriba (sus defaults son los de D1).",
        'presetSel = input.string("Auto (por temporalidad)", "Preset", options=["Auto (por temporalidad)", "H4", "D1", "W1", "Manual"], group="Preset")',
        "tfSec    = timeframe.in_seconds()",
        "autoIdx  = tfSec < 86400 ? 1 : tfSec < 604800 ? 2 : 3",
        'presetIdx = presetSel == "H4" ? 1 : presetSel == "D1" ? 2 : presetSel == "W1" ? 3 : presetSel == "Manual" ? 0 : autoIdx',
        "",
    ]
    for n in names:
        a_, b_, c_ = (pine_literal(sets[t][n]) for t in ("h4", "d1", "w1"))
        cond = "(useMine or presetIdx == 0)" if n in WHAT_TO_TEST else "presetIdx == 0"
        blk.append(f"{n} = {cond} ? m_{n} : presetIdx == 1 ? {a_} : presetIdx == 2 ? {b_} : {c_}")
    blk.append("")
    out[at:at] = blk
    out += [
        "",
        "// ===== Cartel con el preset en uso =====",
        'presetName = presetIdx == 0 ? "Manual" : presetIdx == 1 ? "H4" : presetIdx == 2 ? "D1" : "W1"',
        "tfCalibrated = tfSec == 14400 or tfSec == 86400 or tfSec == 604800",
        "var table infoTbl = table.new(position.top_right, 1, 1)",
        "if barstate.islast",
        '    table.cell(infoTbl, 0, 0, "Preset: " + presetName + (useMine ? " | casillas propias" : "") + (presetIdx == 0 or tfCalibrated ? "" : " (TF no calibrado)"), text_color=color.white, bgcolor=color.new(color.gray, 30))',
    ]
    hdr = ["// GENERADO por src/sqzlab/genpine.py desde params/{h4,d1,w1}.json. NO editar a mano. NO COMPILADO en TradingView."]
    return "\n".join(out[:1] + hdr + out[1:]) + "\n"


# ----------------------------------------------------------------------------------------------------------------
# Indicador v8 unificado (Fase 6.5): mismo esquema de preset que el unificado de la strategy
# ----------------------------------------------------------------------------------------------------------------
IND_RENAME = {"useD": "useDivSig", "cLong": "cAllowLong"}     # nombre en params/*.json -> nombre en el v8
IND_INJECT = ["useA", "aLong", "aShort", "bLong", "bShort", "cShort", "dLong", "dShort"]   # toggles que el v8 no tiene
IND_INJECT_LABEL = {"useA": "Senal A (pullback)", "aLong": "A: COMPRAS", "aShort": "A: VENTAS", "bLong": "B: COMPRAS (squeeze)",
                    "bShort": "B: VENTAS (squeeze)", "cShort": "C: VENTAS (techo)", "dLong": "D: COMPRAS (divergencia alcista)",
                    "dShort": "D: VENTAS (divergencia bajista)"}
IND_NOT_APPLICABLE = ["riskPct", "maxLev"]                       # son de la strategy: el indicador no abre posiciones
# (texto exacto del v8, texto nuevo): inyeccion minima de los toggles por lado. Si el v8 cambia, falla fuerte.
IND_PATCHES = [
    ("allowLong and upTrend", "allowLong and useA and aLong and upTrend"),
    ("allowShort and downTrend", "allowShort and useA and aShort and downTrend"),
    ("allowLong and bLongRaw", "allowLong and bLong and bLongRaw"),
    ("allowShort and bShortRaw", "allowShort and bShort and bShortRaw"),
    ("allowShort and cShortRaw", "allowShort and cShort and cShortRaw"),
    ("allowLong and useDivSig and bullDiv", "allowLong and useDivSig and dLong and bullDiv"),
    ("allowShort and useDivSig and bearDiv", "allowShort and useDivSig and dShort and bearDiv"),
]
IND_TITLE_RE = re.compile(r'indicator\("Squeeze \+ RSI \+ Senales A\+B\+C", shorttitle="SQZ\+RSI\+SIG"')


def indicator_unified(lines: list[str], sets: dict[str, dict]) -> str:
    """Indicador v8 con los presets H4/D1/W1 (elegidos solos con timeframe.in_seconds()) y los toggles por senal y lado
    de la strategy v2 (default true: sin preset el v8 se comporta igual). Los parametros compartidos se mapean por nombre
    (useD -> useDivSig, cLong -> cAllowLong)."""
    src = "\n".join(lines)
    for old, _ in IND_PATCHES:
        assert src.count(old) == 1, f"el v8 cambio: no encuentro una sola vez {old!r}"
    for old, new in IND_PATCHES:
        src = src.replace(old, new)
    lines = src.split("\n")
    v8 = {m["name"] for m in map(INPUT_RE.match, lines) if m}
    d1 = sets["d1"]
    skip = set(IND_NOT_APPLICABLE) | set(IND_INJECT)
    missing = [k for k in d1 if k not in skip and IND_RENAME.get(k, k) not in v8]
    assert not missing, f"parametros de params/*.json sin equivalente en el v8: {missing}"
    inv = {IND_RENAME.get(k, k): k for k in d1 if k not in skip}      # nombre en el v8 -> clave en params
    out, names = [], []
    for ln in lines:
        m = INPUT_RE.match(ln)
        if m and m["name"] in inv:
            key = inv[m["name"]]
            v = d1[key]
            lit = pine_literal(int(v) if m["typ"] == "int" else float(v) if m["typ"] == "float" else v)
            names.append((m["name"], key))
            ln = f'm_{m["name"]}{m["eq"]}input.{m["typ"]}({lit},{m["rest"]}'
        elif IND_TITLE_RE.search(ln):
            ln = IND_TITLE_RE.sub('indicator("Squeeze + RSI + Senales AUTO (presets H4/D1/W1)", shorttitle="SQZ+RSI+SIG AUTO"', ln)
        out.append(ln)
    # casillas de Que probar que el v8 no tiene (default true) + el interruptor, justo despues de la linea indicator(...)
    inject = ["", "// ===== Inputs: Que probar (toggles por senal y lado, como la strategy; default true = el v8 de siempre) =====", MINE_INPUT]
    for n in IND_INJECT:
        inject.append(f'm_{n} = input.bool(true, "{IND_INJECT_LABEL[n]}", group="Que probar")')
    out[2:2] = inject
    at = next(i for i, ln in enumerate(out) if ln.startswith("// ===== Squeeze ====="))
    blk = [
        "// ===== Presets por temporalidad (GENERADO por src/sqzlab/genpine.py desde params/*.json; NO editar a mano) =====",
        "// Un set por temporalidad, nunca por moneda. " + PRESET_NOTE,
        "// Los parametros optimizables siguen al preset. Las casillas de Que probar siguen al preset solo si NO tildas",
        "// 'usar mis casillas'. HABILITAR COMPRAS / VENTAS (master) y todo lo visual son siempre tuyos.",
        "// Manual = todo sale de los campos de las pestanas de arriba (sus defaults son los de D1 = v2).",
        'presetSel = input.string("Auto (por temporalidad)", "Preset", options=["Auto (por temporalidad)", "H4", "D1", "W1", "Manual"], group="Preset")',
        "tfSec    = timeframe.in_seconds()",
        "autoIdx  = tfSec < 86400 ? 1 : tfSec < 604800 ? 2 : 3",
        'presetIdx = presetSel == "H4" ? 1 : presetSel == "D1" ? 2 : presetSel == "W1" ? 3 : presetSel == "Manual" ? 0 : autoIdx',
        "",
    ]
    for n in IND_INJECT:
        a_, b_, c_ = (pine_literal(sets[t][n]) for t in ("h4", "d1", "w1"))
        blk.append(f"{n} = (useMine or presetIdx == 0) ? m_{n} : presetIdx == 1 ? {a_} : presetIdx == 2 ? {b_} : {c_}")
    for vname, key in names:
        a_, b_, c_ = (pine_literal(sets[t][key]) for t in ("h4", "d1", "w1"))
        cond = "(useMine or presetIdx == 0)" if key in WHAT_TO_TEST else "presetIdx == 0"
        blk.append(f"{vname} = {cond} ? m_{vname} : presetIdx == 1 ? {a_} : presetIdx == 2 ? {b_} : {c_}")
    blk.append("")
    out[at:at] = blk
    out += [
        "",
        "// ===== Cartel con el preset en uso =====",
        'presetName = presetIdx == 0 ? "Manual" : presetIdx == 1 ? "H4" : presetIdx == 2 ? "D1" : "W1"',
        "tfCalibrated = tfSec == 14400 or tfSec == 86400 or tfSec == 604800",
        "var table infoTbl = table.new(position.top_right, 1, 1)",
        "if barstate.islast",
        '    table.cell(infoTbl, 0, 0, "Preset: " + presetName + (useMine ? " | casillas propias" : "") + (presetIdx == 0 or tfCalibrated ? "" : " (TF no calibrado)"), text_color=color.white, bgcolor=color.new(color.gray, 30))',
    ]
    hdr = ["// GENERADO por src/sqzlab/genpine.py desde ref/sqz_rsi_senales_v8.pine + params/{h4,d1,w1}.json. NO editar a mano. NO COMPILADO en TradingView.",
           "// El indicador marca SENALES: la strategy ademas filtra por posicion abierta (y tiene el quirk de B), asi que toda entrada de la strategy coincide con una senal de aca, no al reves."]
    return "\n".join(out[:1] + hdr + out[1:]) + "\n"


def generate() -> list[Path]:
    lines = read_ref()
    sets = {tf: load_params(tf) for tf in TFS}
    written = []
    for tf, label in TFS.items():
        d = ROOT / "pine" / tf
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"sqz_rsi_strategy_{tf}.pine"
        p.write_text(per_tf(lines, sets[tf], label), encoding="utf-8")
        written.append(p)
    p = ROOT / "pine" / "sqz_rsi_strategy_unified.pine"
    p.write_text(unified(lines, sets), encoding="utf-8")
    written.append(p)
    p = ROOT / "pine" / "sqz_rsi_senales_unified.pine"
    p.write_text(indicator_unified(REF_IND.read_text(encoding="utf-8").splitlines(), sets), encoding="utf-8")
    written.append(p)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-params", action="store_true")
    a = ap.parse_args()
    if a.init_params:
        init_params()
    for p in generate():
        print("escrito", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
