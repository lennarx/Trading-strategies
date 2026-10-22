import difflib
import re

from sqzlab import genpine

SYMS = {"BTC", "ETH", "SOL", "XRP", "DOGE", "LINK"}


def test_params_keys_are_exactly_the_pine_inputs():
    pine = set(genpine.pine_defaults(genpine.read_ref()))
    for tf in genpine.TFS:
        assert set(genpine.load_params(tf)) == pine


def test_one_set_per_timeframe_never_per_coin():
    for tf in genpine.TFS:
        assert not (set(genpine.load_params(tf)) & SYMS)
        assert not any(k.upper() in SYMS for k in genpine.load_params(tf))


def test_per_tf_script_only_changes_defaults_title_and_header():
    ref = genpine.read_ref()
    for tf, label in genpine.TFS.items():
        gen = (genpine.ROOT / "pine" / tf / f"sqz_rsi_strategy_{tf}.pine").read_text(encoding="utf-8").splitlines()
        changed = [l for l in difflib.unified_diff(ref, gen, lineterm="", n=0)
                   if l[0] in "+-" and not l.startswith(("+++", "---"))]
        for l in changed:
            assert l[1:].startswith("//") or "input." in l or l[1:].startswith("strategy("), l


def test_generated_files_are_up_to_date_with_params():
    lines, sets = genpine.read_ref(), {tf: genpine.load_params(tf) for tf in genpine.TFS}
    for tf, label in genpine.TFS.items():
        gen = (genpine.ROOT / "pine" / tf / f"sqz_rsi_strategy_{tf}.pine").read_text(encoding="utf-8")
        assert gen == genpine.per_tf(lines, sets[tf], label), "regenerar: python -m sqzlab.genpine"
    uni = (genpine.ROOT / "pine" / "sqz_rsi_strategy_unified.pine").read_text(encoding="utf-8")
    assert uni == genpine.unified(lines, sets)


def _uni():
    return (genpine.ROOT / "pine" / "sqz_rsi_strategy_unified.pine").read_text(encoding="utf-8")


def test_unified_uses_timeframe_in_seconds_and_keeps_not_compiled_header():
    uni = _uni()
    assert "timeframe.in_seconds()" in uni and "NO COMPILADO" in uni.splitlines()[1]


def test_unified_tunable_params_follow_the_preset_per_timeframe():
    uni = _uni()
    tunable = [n for n in genpine.pine_defaults(genpine.read_ref())
               if n not in genpine.WHAT_TO_TEST and n not in genpine.USER_ALWAYS]
    assert tunable
    for n in tunable:
        assert re.search(rf"^m_{n}\s*=\s*input\.", uni, re.M)
        assert re.search(rf"^{n} = presetIdx == 0 \? m_{n} : presetIdx == 1 \?", uni, re.M)


def test_unified_what_to_test_checkboxes_have_their_own_switch_default_off():
    uni = _uni()
    assert re.search(r'^useMine = input\.bool\(false, "Que probar: usar mis casillas \(en vez del preset\)"', uni, re.M)
    for n in genpine.WHAT_TO_TEST:
        assert re.search(rf"^m_{n}\s*=\s*input\.bool", uni, re.M)
        assert re.search(rf"^{n} = \(useMine or presetIdx == 0\) \? m_{n} :", uni, re.M), n


def test_unified_risk_and_leverage_are_always_user_inputs():
    uni = _uni()
    for n in genpine.USER_ALWAYS:
        assert re.search(rf"^{n}\s*=\s*input\.float\(", uni, re.M)
        assert f"m_{n}" not in uni and not re.search(rf"^{n} = presetIdx", uni, re.M)


# ---------------------------------------------------------------------------------------------------------------
# Indicador v8 unificado (Fase 6.5)
# ---------------------------------------------------------------------------------------------------------------
def _ind():
    return (genpine.ROOT / "pine" / "sqz_rsi_senales_unified.pine").read_text(encoding="utf-8")


def _v8():
    return genpine.REF_IND.read_text(encoding="utf-8").splitlines()


def test_indicator_unified_is_up_to_date():
    sets = {tf: genpine.load_params(tf) for tf in genpine.TFS}
    assert _ind() == genpine.indicator_unified(_v8(), sets), "regenerar: python -m sqzlab.genpine"


def test_indicator_unified_only_changes_inputs_toggles_title_and_adds_preset_blocks():
    ref, gen = _v8(), _ind().splitlines()
    patched_old = {old for old, _ in genpine.IND_PATCHES}
    for l in difflib.unified_diff(ref, gen, lineterm="", n=0):
        if l[0] not in "+-" or l.startswith(("+++", "---")):
            continue
        body = l[1:]
        if l[0] == "-":      # lo que sale del v8: inputs con otro nombre/default, el titulo y las 7 lineas con toggles
            assert (not body.strip() or genpine.INPUT_RE.match(body) or body.startswith("indicator(") or any(o in body for o in patched_old)), body
        else:                # lo que entra: inputs m_, toggles, comentarios, bloque de presets, cartel, lineas parcheadas
            assert (body.startswith(("//", "m_", "useMine", "presetSel", "tfSec", "autoIdx", "presetIdx", "presetName", "tfCalibrated",
                                     "var table", "if barstate.islast", "    table.cell", "indicator(")) or not body.strip()
                    or re.match(r"^\w+ = (\(useMine or presetIdx == 0\)|presetIdx == 0) \? m_\w+ : presetIdx == 1", body)
                    or any(n in body for _, n in genpine.IND_PATCHES)), body


def test_indicator_preset_literals_match_params_json_for_every_timeframe():
    ind = _ind()
    for key in genpine.load_params("d1"):
        if key in genpine.IND_NOT_APPLICABLE:
            continue
        name = genpine.IND_RENAME.get(key, key)
        vals = [genpine.pine_literal(genpine.load_params(tf)[key]) for tf in ("h4", "d1", "w1")]
        pat = rf"^{name} = .* \? m_{name} : presetIdx == 1 \? {re.escape(vals[0])} : presetIdx == 2 \? {re.escape(vals[1])} : {re.escape(vals[2])}$"
        assert re.search(pat, ind, re.M), f"{key} -> {name}"


def test_indicator_injected_side_toggles_default_true_and_gate_the_signals():
    ind = _ind()
    for n in genpine.IND_INJECT:
        assert re.search(rf'^m_{n} = input\.bool\(true,', ind, re.M)
    for _, new in genpine.IND_PATCHES:
        assert ind.count(new) == 1
    assert "timeframe.in_seconds()" in ind and "NO COMPILADO" in ind.splitlines()[1]
    assert re.search(r"^allowLong\s*= input\.bool\(true", ind, re.M) and re.search(r"^allowShort\s*= input\.bool\(true", ind, re.M)


def test_indicator_h4_preset_turns_off_what_the_h4_params_turn_off():
    h4 = genpine.load_params("h4")
    ind = _ind()
    for key in ("aShort", "cShort", "dLong", "dShort", "useC", "useD"):
        assert h4[key] is False
    assert re.search(r"^aShort = .* presetIdx == 1 \? false :", ind, re.M)
    assert re.search(r"^useDivSig = .* presetIdx == 1 \? false :", ind, re.M)


# ---------------------------------------------------------------------------------------------------------------
# Capa E fiel (Fase 8)
# ---------------------------------------------------------------------------------------------------------------
def test_e_layer_is_generated_from_r1fiel_params_and_places_no_orders():
    uni = _uni()
    ps = genpine.r1fiel_params()
    seg = uni[uni.index("Capa E fiel"):]
    assert not any(w in seg for w in ("strategy.entry", "strategy.exit", "strategy.order", "strategy.close"))
    for d in ps["lookbacks_days"]:
        assert f"fzN{d}  = math.max(2, int(math.floor({d} * fzBpd + 0.5)))" in seg
        assert f"fzHi{d} = ta.highest(close, fzN{d})[1]" in seg and f'"E stop N={d}d"' in seg
    assert f"math.min({float(ps['coin_cap'])}, {ps['vol_target']} / fzVol)" in seg
    assert f"fzVolN = math.max(2, int(math.floor({ps['vol_window_days']} * fzBpd + 0.5)))" in seg
    assert seg.count("var bool fzPos") == len(ps["lookbacks_days"]) == 9


def test_e_layer_pine_bar_counts_equal_the_python_lookbacks():
    import math
    from sqzlab import r1fiel
    for tf, sec in (("d1", 86400), ("h4", 14400)):
        bpd = 86400.0 / sec
        assert [max(2, int(math.floor(d * bpd + 0.5))) for d in r1fiel.params()["lookbacks_days"]] == r1fiel.lookbacks(tf)
