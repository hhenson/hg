from hgraph import TS, graph, TSL, Size, SCALAR, compute_node, SIZE
from hgraph.nodes import flatten_tsl_values, const
from hgraph.test import eval_node


@compute_node
def my_tsl_maker(ts1: TS[int], ts2: TS[int]) -> TSL[TS[int], Size[2]]:
    out = {}
    if ts1.modified:
        out[0] =ts1.delta_value
    if ts2.modified:
        out[1] = ts2.delta_value
    return out


def test_fixed_tsl_non_peered_input():
    @graph
    def my_tsl(ts1: TS[int], ts2: TS[int]) -> TS[tuple[int, ...]]:
        tsl = TSL.from_ts(ts1, ts2)
        return flatten_tsl_values[SCALAR: int](tsl)

    assert eval_node(my_tsl, ts1=[1, 2], ts2=[3, 4]) == [(1,3), (2, 4)]


def test_fixed_tsl_peered():
    @graph
    def my_tsl(ts1: TS[int], ts2: TS[int]) -> TS[int]:
        tsl = my_tsl_maker(ts1, ts2)
        return tsl[0]

    assert eval_node(my_tsl, ts1=[1, 2], ts2=[3, 4]) == [1, 2]


def test_peered_to_peered_tsl():
    @graph
    def my_tsl(ts1: TS[int], ts2: TS[int]) -> TS[tuple[int, ...]]:
        tsl = my_tsl_maker(ts1, ts2)
        return flatten_tsl_values[SCALAR: int](tsl)

    assert eval_node(my_tsl, ts1=[1, 2], ts2=[3, 4]) == [(1,3), (2, 4)]


def test_len():

    @graph
    def l_test(tsl: TSL[TS[int], SIZE]) -> TS[int]:
        return const(len(tsl))

    assert eval_node(l_test, tsl=[None], resolution_dict={"tsl": TSL[TS[int], Size[5]]}) == [5]
