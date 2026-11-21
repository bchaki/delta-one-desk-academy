"""OTC initial margin: schedule-based and a SIMM-style equity delta. Parameters are ILLUSTRATIVE
(``config/simm_illustrative.yaml``), not the official ISDA calibration.

Notation: s_k sensitivity (PV change per 1% move), RW_k risk weight, WS_k = RW_k x s_k.
Within bucket b:  K_b = sqrt(sum_k WS_k^2 + sum_{k != l} rho WS_k WS_l)
Across buckets:   IM = sqrt(sum_b K_b^2 + sum_{b != c} gamma S_b S_c), S_b = max(min(sum WS, K_b), -K_b)
The residual bucket is added without diversification.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from core import config
from core.margin import MarginResult


def weighted_sensitivity(risk_weight: float, sensitivity: float) -> float:
    """WS = RW x s."""
    return risk_weight * sensitivity


def bucket_margin(ws: Sequence[float], rho: float) -> float:
    """K_b = sqrt(max(sum WS^2 + rho x sum_{k != l} WS_k WS_l, 0)), a single rho for all pairs."""
    sq = sum(w * w for w in ws)
    total = sum(ws)
    cross = total * total - sq
    return math.sqrt(max(sq + rho * cross, 0.0))


def equity_delta_margin(
    sens_by_bucket: Mapping[int, Sequence[float]],
    rho: float | None = None,
    gamma: float | None = None,
) -> MarginResult:
    """SIMM-style equity delta margin from sensitivities (per 1% move) grouped by bucket.

    ``gross`` is the sum of standalone bucket margins; ``credits`` the diversification between
    buckets, so ``net`` is the SIMM-style margin. ``rho`` and ``gamma`` default to config.
    """
    cfg = config.simm().equity_delta
    rho_ = cfg.rho_intra if rho is None else rho
    gam = cfg.gamma if gamma is None else gamma

    k: dict[int, float] = {}
    s: dict[int, float] = {}
    for b, sens in sens_by_bucket.items():
        ws = [weighted_sensitivity(cfg.risk_weight[b], x) for x in sens]
        k[b] = bucket_margin(ws, rho_)
        s[b] = max(min(sum(ws), k[b]), -k[b])

    regular = [b for b in k if b != cfg.residual_bucket]
    diversified_sq = sum(k[b] ** 2 for b in regular)
    for i, b in enumerate(regular):
        for c in regular[i + 1 :]:
            diversified_sq += 2.0 * gam * s[b] * s[c]
    diversified = math.sqrt(max(diversified_sq, 0.0))
    residual = k.get(cfg.residual_bucket, 0.0)

    gross = sum(k.values())
    net = diversified + residual
    return MarginResult(
        gross=gross,
        credits=max(gross - net, 0.0),
        detail={
            **{f"K:{b}": v for b, v in k.items()},
            "diversified": diversified,
            "residual": residual,
        },
    )


def schedule_im(
    gross_notional: float,
    net_notional: float,
    pct: float | None = None,
    gross_weight: float | None = None,
) -> MarginResult:
    """Schedule-based IM: gross IM = pct x gross notional; net IM = gross IM x (w + (1 - w) x NGR),
    NGR = |net| / gross. Credits are the netting benefit. Illustrative grid from config."""
    cfg = config.simm().schedule
    p = cfg.equity_swap_pct if pct is None else pct
    w = cfg.gross_weight if gross_weight is None else gross_weight
    gross_im = p * gross_notional
    ngr = abs(net_notional) / gross_notional if gross_notional else 0.0
    net_im = gross_im * (w + (1.0 - w) * ngr)
    return MarginResult(gross=gross_im, credits=gross_im - net_im, detail={"ngr": ngr})
