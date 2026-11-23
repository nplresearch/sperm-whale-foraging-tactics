"""M3: re-derive the converged-BIC claim and the label reproduction independently."""

import numpy as np
import pandas as pd
import pytest
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import QuantileTransformer

from common import PKG
from dswp.classification import FEATURES, classify_gmm

LABELLED = PKG / "results/dswp/buzz_events_labelled.csv"


def _x(frame):
    x = frame.dropna(subset=list(FEATURES))[list(FEATURES)].to_numpy()
    return QuantileTransformer(n_quantiles=len(x), output_distribution="normal",
                               random_state=0).fit_transform(x)


def _bic(x, k, tol):
    return GaussianMixture(k, covariance_type="full", n_init=10, init_params="kmeans",
                           random_state=1234, tol=tol, max_iter=2000).fit(x).bic(x)


@pytest.fixture(scope="module")
def ev():
    return pd.read_csv(LABELLED)


def test_registered_labels_are_reproduced_from_features(ev):
    assert (classify_gmm(ev, features=FEATURES) == ev.buzz_type).all()


def test_converged_em_changes_the_bic_picture(ev):
    """The SI used default tolerance. Converged k=2 vs k=1 is far stronger (~ -43)."""
    x = _x(ev)
    converged = _bic(x, 2, 1e-7) - _bic(x, 1, 1e-7)
    default = _bic(x, 2, 1e-3) - _bic(x, 1, 1e-3)
    assert converged < -35
    assert converged < default - 10    # under-converged EM understates the evidence


def test_k3_is_not_clearly_worse_than_k2(ev):
    """SI says 'minimum at k = 2'; converged fits give k=3 a ~2-point edge (tie)."""
    x = _x(ev)
    assert abs(_bic(x, 3, 1e-7) - _bic(x, 2, 1e-7)) < 5


def test_posterior_overlap_share_is_large(ev):
    assert 0.27 < (ev.buzz_type == "?").mean() < 0.34
