"""signals: sin repintado, coincide con los trades de simulate, contrato del JSON, E coherente con donchian_subtrades."""
import json

import pandas as pd
import pytest

from sqzlab import universe as U
from sqzlab.donchian import donchian_subtrades
from sqzlab.genpine import load_params
from sqzlab.optimize import BASE
from sqzlab.signals import bar_events, e_state, last_signal
from sqzlab.strategy import simulate

KEYS = {"symbol", "tf", "bar_time_utc", "action", "kind", "entry_ref", "stop", "size_pct_equity", "params_hash", "position"}


def _df(sym="ETH", code="1d"):
    try:
        return U.load_coin(sym, code)
    except FileNotFoundError:
        pytest.skip("sin datos en data/")


def _strip(sig):
    return {k: v for k, v in sig.items() if k != "position"}


def test_no_repainting_signals_for_closed_bars():
    """Datos hasta t -> senal en t; datos hasta t+50 -> la senal de esa misma vela t es identica."""
    df = _df()
    p = {**BASE, **load_params("d1")}
    n = len(df)
    full_ev = bar_events(df, p)
    for t in range(n - 700, n - 60, 23):
        short = df.iloc[: t + 1].reset_index(drop=True)
        a = last_signal(short, "d1", "ETH", p)
        long_ = df.iloc[: t + 51].reset_index(drop=True)
        ev50 = bar_events(long_, p).get(t, {})
        b_expected = ev50.get("entry"), ev50.get("exit")
        ev_cut = bar_events(short, p).get(t, {})
        assert (ev_cut.get("entry"), ev_cut.get("exit")) == b_expected, f"repinto en la vela {t}"
        assert (full_ev.get(t, {}).get("entry"), full_ev.get(t, {}).get("exit")) == b_expected
        assert a["action"] in {"long", "short", "exit", "none"}


def test_signals_match_simulate_trades():
    df = _df()
    p = {**BASE, **load_params("d1")}
    res = simulate(df, **p)
    ev = bar_events(df, p)
    entries = {i: e["entry"] for i, e in ev.items() if i != "_open" and "entry" in e}
    exits = {i: e["exit"] for i, e in ev.items() if i != "_open" and "exit" in e}
    assert len(entries) == len(res.trades) + (res.open_trade is not None)
    for t in res.trades:
        assert entries[t.entry_i]["kind"] == t.kind and entries[t.entry_i]["stop"] == t.stop
        assert exits[t.exit_i]["reason"] == t.exit_reason
    # la ultima vela traducida a accion coincide con el evento
    idx = max(i for i in entries)
    short = df.iloc[: idx + 1].reset_index(drop=True)
    s = last_signal(short, "d1", "ETH", p)
    assert s["action"] in {"long", "short"} and s["kind"] == entries[idx]["kind"] and s["stop"] == entries[idx]["stop"]
    assert s["size_pct_equity"] <= p["maxLev"] * 100 + 1e-9


def test_contract_fields_and_none_signal():
    df = _df()
    p = {**BASE, **load_params("d1")}
    ev = bar_events(df, p)
    quiet = next(t for t in range(len(df) - 1, 0, -1) if not ev.get(t))
    s = last_signal(df.iloc[: quiet + 1].reset_index(drop=True), "d1", "ETH", p)
    assert KEYS <= set(s) and s["action"] == "none" and s["kind"] is None
    json.dumps(s)


def test_e_state_matches_donchian_subtrades():
    df = _df("BTC")
    days = [20, 60, 150, 250]
    sub = donchian_subtrades(df, "d1", days, "BTC")
    for cut in (900, 1500, 2200, len(df)):
        d = df.iloc[:cut].reset_index(drop=True)
        st = e_state(d, "d1", "BTC", days)
        sd = donchian_subtrades(d, "d1", days, "BTC")
        assert st["active_subsignals"] == int(sd["open"].sum())
        assert sorted(st["entering_days"]) == sorted(r.lb for r in sd.itertuples() if r.entry_i == cut - 1)
        assert st["action"] in {"long", "exit", "none"} and st["kind"] == "E"
    assert len(sub) > 0
