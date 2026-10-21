import pandas as pd

from sqzlab import forward as F


def tf_frame(rows):
    df = pd.DataFrame(rows, columns=["coin", "kind", "side", "entry_t", "exit_t", "R", "sd"])
    df["entry_t"], df["exit_t"] = pd.to_datetime(df["entry_t"]), pd.to_datetime(df["exit_t"])
    return df


def test_merge_saved_is_idempotent_and_keeps_saved_rows():
    a = tf_frame([("BTC", "A", 1, "2026-10-23", "2026-10-25", 1.5, 2.0)])
    b = tf_frame([("BTC", "A", 1, "2026-10-23", "2026-10-25", 1.5, 2.0), ("ETH", "B", -1, "2026-10-24", "2026-10-26", -1.0, 1.0)])
    once, w1 = F.merge_saved(a, b)
    twice, w2 = F.merge_saved(once, b)
    assert len(once) == 2 and once.equals(twice) and not w1 and not w2


def test_merge_saved_warns_when_a_saved_trade_changes():
    a = tf_frame([("BTC", "A", 1, "2026-10-23", "2026-10-25", 1.5, 2.0)])
    b = tf_frame([("BTC", "A", 1, "2026-10-23", "2026-10-25", 0.9, 2.0)])
    out, warns = F.merge_saved(a, b)
    assert len(out) == 1 and out["R"].iloc[0] == 1.5 and len(warns) == 1


def test_closed_only_drops_the_candle_in_progress():
    df = pd.DataFrame({"time_utc": pd.to_datetime(["2026-10-20 00:00", "2026-10-20 04:00", "2026-10-20 08:00"])})
    got = F.closed_only(df, "4h", now=pd.Timestamp("2026-10-20 09:00"))
    assert list(got["time_utc"]) == list(df["time_utc"][:2])
