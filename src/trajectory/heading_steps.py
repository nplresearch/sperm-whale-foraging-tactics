"""Heading-based movement steps and discrete step-duration models.

The production step lengths (`analysis.step_lengths`) use 30-degree changes
between consecutive 25-Hz displacement vectors. In the released tracks those
"turns" are flips of the vertical angle caused by centimetre-scale depth
wobble against an assumed horizontal speed, not changes of heading. This
module defines steps from *heading* only, averaged over behavioural time
blocks, and measures them as *durations* (blocks between turns), so neither
depth wobble nor the assumed speed enters.

Models for step durations k (integer blocks, k >= kmin):
discrete power law (Lévy-like), geometric (Brownian-like / exponential), and a
two-component geometric mixture (composite random walk: intensive and
extensive search modes).
"""

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import zeta


def block_headings(xyz, fs_hz, block_s):
    """Mean horizontal heading (rad) and mean resultant length per time block."""
    d = np.diff(np.asarray(xyz, float)[:, :2], axis=0)
    norm = np.hypot(d[:, 0], d[:, 1])
    unit = np.where(norm[:, None] > 0, d / np.where(norm > 0, norm, 1)[:, None], np.nan)
    b = int(round(block_s * fs_hz))
    n = len(unit) // b
    blocks = unit[: n * b].reshape(n, b, 2)
    mean = np.nanmean(blocks, axis=1)
    return np.arctan2(mean[:, 0], mean[:, 1]), np.hypot(mean[:, 0], mean[:, 1])


def turn_runs(headings, threshold_rad):
    """(first block, length) of each run between successive heading turns.

    A turn between blocks i and i+1 is a heading change above the threshold.
    Runs before the first and after the last turn are censored and dropped, as
    are runs that cross a block with no heading.
    """
    h = np.asarray(headings, float)
    dtheta = np.angle(np.exp(1j * (h[1:] - h[:-1])))
    runs, last_turn = [], None
    for i, d in enumerate(dtheta):
        if not np.isfinite(d):
            last_turn = None
            continue
        if abs(d) > threshold_rad:
            if last_turn is not None:
                runs.append((last_turn + 1, i - last_turn))
            last_turn = i
    return np.array(runs, dtype=int).reshape(-1, 2)


def turn_run_lengths(headings, threshold_rad):
    """Blocks between successive heading turns."""
    return turn_runs(headings, threshold_rad)[:, 1]


def _tail(k, kmin):
    k = np.asarray(k)
    return k[k >= kmin].astype(float)


def fit_discrete_powerlaw(k, kmin):
    x = _tail(k, kmin)
    s = np.log(x).sum()
    nll = lambda mu: mu * s + len(x) * np.log(zeta(mu, kmin))
    mu = minimize_scalar(nll, bounds=(1.0001, 8.0), method="bounded").x
    ll = -nll(mu)
    return {"mu": float(mu), "ll": float(ll), "aic": float(2 - 2 * ll), "n": len(x)}


def fit_geometric(k, kmin):
    x = _tail(k, kmin) - kmin
    m = x.mean()
    q = m / (1 + m)
    ll = len(x) * np.log(1 - q) + (x.sum() * np.log(q) if q > 0 else 0.0)
    return {"q": float(q), "ll": float(ll), "aic": float(2 - 2 * ll), "n": len(x)}


def fit_geometric_mixture(k, kmin, n_iter=2000, tol=1e-10):
    """Two-component geometric mixture by EM (best of three starts)."""
    x = _tail(k, kmin) - kmin
    best = None
    for split in (0.5, 0.75, 0.9):
        cut = np.quantile(x, split)
        lo, hi = x[x <= cut], x[x > cut]
        if len(hi) == 0:
            continue
        q = np.array([lo.mean() / (1 + lo.mean()), hi.mean() / (1 + hi.mean())])
        w = np.array([len(lo), len(hi)], float) / len(x)
        prev = -np.inf
        for _ in range(n_iter):
            q = np.clip(q, 1e-9, 1 - 1e-9)
            logf = np.log(w)[None, :] + np.log(1 - q)[None, :] + x[:, None] * np.log(q)[None, :]
            top = logf.max(axis=1, keepdims=True)
            ll = float((top[:, 0] + np.log(np.exp(logf - top).sum(axis=1))).sum())
            r = np.exp(logf - top)
            r /= r.sum(axis=1, keepdims=True)
            w = r.mean(axis=0)
            m = (r * x[:, None]).sum(axis=0) / r.sum(axis=0)
            q = m / (1 + m)
            if ll - prev < tol:
                break
            prev = ll
        if best is None or ll > best["ll"]:
            best = {"ll": ll, "q_fast": float(q.min()), "q_slow": float(q.max()),
                    "w_slow": float(w[np.argmax(q)])}
    best.update({"aic": float(6 - 2 * best["ll"]), "n": len(x)})
    return best


def choose_kmin(k, min_tail=30):
    """Clauset-style cutoff: the kmin minimising the power-law KS distance."""
    k = np.asarray(k)
    best = (np.inf, 1)
    for kmin in np.unique(k[k <= np.percentile(k, 80)]):
        x = _tail(k, kmin)
        if len(x) < min_tail:
            continue
        mu = fit_discrete_powerlaw(k, kmin)["mu"]
        support = np.arange(kmin, x.max() + 1)
        cdf = np.cumsum(support ** -mu) / zeta(mu, kmin)
        emp = np.searchsorted(np.sort(x), support, side="right") / len(x)
        ks = np.max(np.abs(emp - cdf))
        if ks < best[0]:
            best = (ks, int(kmin))
    return best[1]
