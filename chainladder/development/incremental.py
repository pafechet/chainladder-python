"""
Incremental Additive Development
================================
"""

from chainladder.development.base import Development, DevelopmentBase
import numpy as np
import copy


class IncrementalAdditive(DevelopmentBase):
    """ The Incremental Additive Method.

    Parameters
    ----------
    trend : float (default=0.0)
        A multiplicative trend amount used to trend each development period to
        a common level.
    n_periods : integer, optional (default=-1)
        number of origin periods to be used in the ldf average calculation. For
        all origin periods, set n_periods=-1
    average: str optional (default='volume')
        type of averaging to use for ldf average calculation.  Options include
        'volume' and 'simple'.

    Attributes
    ----------
    ldf_ : Triangle
        The estimated loss development patterns
    cdf_ : Triangle
        The estimated cumulative development patterns
    incremental_ : Triangle
        A triangle of full incremental values.


    """
    def __init__(self, trend=0.0, n_periods=-1, average='volume'):
        self.trend = trend
        self.n_periods = n_periods
        self.average = average

    def fit(self, X, y=None, sample_weight=None):
        """Fit the model with X.

        Parameters
        ----------
        X : Triangle-like
            Triangle to which the incremental method is applied.  Triangle must
            be cumulative.
        y : Ignored
        sample_weight : Exposure used in the method.

        Returns
        -------
        self : object
            Returns the instance itself.
        """
        obj = X.cum_to_incr()/sample_weight
        x = obj.trend(self.trend, axis='origin')
        w_ = Development(n_periods=self.n_periods-1).fit(x).w_
        w_[w_ == 0] = np.nan
        w_ = np.concatenate((w_, (w_[..., -1:]*x.nan_triangle())[..., -1:]),
                            axis=-1)
        if self.average == 'simple':
            y_ = np.nanmean(w_*x.triangle, axis=-2)
        if self.average == 'volume':
            y_ = np.nansum(w_*x.triangle*sample_weight.triangle, axis=-2)
            y_ = y_ / np.nansum(w_*sample_weight.triangle, axis=-2)
        y_ = np.repeat(np.expand_dims(y_, -2), len(x.odims), -2)
        obj = copy.deepcopy(x)
        keeps = 1-np.nan_to_num(x.nan_triangle()) + \
            np.nan_to_num(x.get_latest_diagonal(compress=False).triangle[0,0,...]*0+1)

        obj.triangle = (1+self.trend)**np.flip((np.abs(np.expand_dims(np.arange(obj.shape[-2]), 0).T -
                     np.expand_dims(np.arange(obj.shape[-2]), 0))),0)*y_*keeps
        obj.triangle = obj.triangle*(x.expand_dims(1-np.nan_to_num(x.nan_triangle()))) + \
            np.nan_to_num((X.cum_to_incr()/sample_weight).triangle)
        obj.triangle[obj.triangle == 0] = np.nan
        obj.nan_override = True
        self.incremental_ = obj*sample_weight
        self.ldf_ = obj.incr_to_cum().link_ratio
        return self

    def transform(self, X):
        """ If X and self are of different shapes, align self to X, else
        return self.

        Parameters
        ----------
        X : Triangle
            The triangle to be transformed

        Returns
        -------
            X_new : New triangle with transformed attributes.
        """
        X.cdf_ = self.cdf_
        X.ldf_ = self.ldf_
        X.sigma_ = self.cdf_*0
        X.std_err_ = self.cdf_*0
        X.incremental_ = self.incremental_
        return X
