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


def test_unified_has_preset_per_input_and_uses_timeframe_in_seconds():
    uni = (genpine.ROOT / "pine" / "sqz_rsi_strategy_unified.pine").read_text(encoding="utf-8")
    assert "timeframe.in_seconds()" in uni
    for n in genpine.pine_defaults(genpine.read_ref()):
        assert re.search(rf"^m_{n}\s*=\s*input\.", uni, re.M) and re.search(rf"^{n} = presetIdx == 0 \? m_{n}", uni, re.M)
