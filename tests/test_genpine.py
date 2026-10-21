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
