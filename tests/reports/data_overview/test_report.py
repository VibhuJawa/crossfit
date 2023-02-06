import pandas as pd
import numpy as np
import dask.dataframe as dd

import crossfit as cf
from crossfit.reports.data_overview.report import (
    ContinuousMetrics,
    CategoricalMetrics,
    data_overview_report,
    DataOverviewReport,
)
from crossfit.reports.data_overview.visualization.facets import FacetsOverview
from crossfit.backends.dask.aggregate import aggregate

from tests.utils import sample_df


@sample_df({"a": [1, 2] * 2000, "b": range(1000, 5000)})
def test_continuous_aggregators(df, npartitions=2):
    ddf = dd.from_pandas(df, npartitions=npartitions)

    metrics = cf.Aggregator(ContinuousMetrics(), per_column=True)

    result = aggregate(ddf, metrics, to_frame=True)

    assert isinstance(result, pd.DataFrame)
    assert len(result.columns) == 7


@sample_df(
    {
        "a": np.random.choice(list("abcdefgh"), size=1000),
        "country": np.random.choice(["US", "UK", "NL"], size=1000),
    }
)
def test_categorical_aggregator(df, npartitions=2):
    ddf = dd.from_pandas(df, npartitions=npartitions)

    metrics = cf.Aggregator(CategoricalMetrics(), per_column=True)

    result = aggregate(ddf, metrics, to_frame=True)

    assert isinstance(result, pd.DataFrame)
    assert len(result.columns) == 6


@sample_df(
    {
        "con": [1, 2] * 500,
        "country": np.random.choice(["US", "UK", "NL"], size=1000),
    }
)
def test_data_overview_report(df, npartitions=2):
    ddf = dd.from_pandas(df, npartitions=npartitions)

    report = data_overview_report(ddf)

    assert isinstance(report, DataOverviewReport)

    visualization = report.visualize()
    assert isinstance(visualization, FacetsOverview)


@sample_df(
    {
        "con": [1, 2] * 500,
        "cat": ["a", "b"] * 500,
        "country": np.random.choice(["US", "UK", "NL"], size=1000),
    }
)
def test_data_overview_report_grouped(df, npartitions=2):
    ddf = dd.from_pandas(df, npartitions=npartitions)

    report = data_overview_report(ddf, groupby="country")

    assert isinstance(report, DataOverviewReport)

    visualization = report.visualize()
    assert isinstance(visualization, FacetsOverview)