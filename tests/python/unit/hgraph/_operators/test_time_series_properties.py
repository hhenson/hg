from datetime import datetime

from hgraph import (
    TIME_SERIES_TYPE,
    TS,
    graph,
    compute_node,
    REF,
    MIN_ST,
    MIN_TD,
    valid,
    last_modified_time,
    modified, TimeSeriesReference,
)
from hgraph.test import eval_node


def test_valid():
    assert eval_node(valid[TIME_SERIES_TYPE : TS[int]], [None, 1]) == [False, True]


def test_modified():

    @graph
    def g(ts: TS[int]) -> TS[bool]:
        return modified(ts)

    assert eval_node(g, [None, 1, None, None, 2, None]) == [False, True, False, None, True, False]


def test_valid_1():
    @compute_node
    def make_ref(a: REF[TS[int]], b: REF[TS[int]], i: TS[int]) -> REF[TS[int]]:
        return [a.value, b.value, TimeSeriesReference.make()][i.value]

    @graph
    def g(a: TS[int], b: TS[int], i: TS[int]) -> TS[bool]:
        return valid[TIME_SERIES_TYPE : TS[int]](make_ref(a, b, i))

    assert eval_node(g, a=[None, None, None, None, 1], b=[None, None, 1, None, None], i=[2, 1, None, 0, None, 2]) == [
        False,
        False,
        True,
        False,
        True,
        False,
    ]


def test_last_modified_time():
    @graph
    def g(a: TS[int]) -> TS[datetime]:
        return last_modified_time(a)

    assert eval_node(g, [1, None, 2]) == [MIN_ST, None, MIN_ST + 2 * MIN_TD]
