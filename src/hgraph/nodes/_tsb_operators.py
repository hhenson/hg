from typing import Type

from hgraph import compute_node, REF, TSB, TS_SCHEMA, TIME_SERIES_TYPE, PythonTimeSeriesReference, AUTO_RESOLVE, \
    SCALAR, operator, add_, graph, sub_, mul_, div_, floordiv_, pow_, lshift_, rshift_, bit_and, bit_xor, bit_or, \
    eq_, TS, not_, ne_, neg_, pos_, invert_, abs_, TSL, str_, SIZE, all_, min_, max_, sum_, mean, std, var
from hgraph._types._ref_type import TimeSeriesReference

__all__ = ("tsb_get_item", "tsb_get_item_by_name", "tsb_get_item_by_index")


@graph(overloads=add_)
def add_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise addition of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(add_, lhs, rhs)


@graph(overloads=sub_)
def sub_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise subtraction of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(sub_, lhs, rhs)


@graph(overloads=mul_)
def mul_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise multiplication of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(mul_, lhs, rhs)


@graph(overloads=div_)
def div_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise division of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(div_, lhs, rhs)


@graph(overloads=floordiv_)
def floordiv_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise floor division of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(floordiv_, lhs, rhs)


@graph(overloads=pow_)
def floordiv_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise lhs ** rhs of TSB elements.  A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(pow_, lhs, rhs)


@graph(overloads=lshift_)
def lshift_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise left shift of LHS TSB elements by RHS TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(lshift_, lhs, rhs)


@graph(overloads=rshift_)
def rshift_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise right shift of LHS TSB elements by RHS TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(rshift_, lhs, rhs)


@graph(overloads=bit_and)
def rshift_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise bitwise AND of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(bit_and, lhs, rhs)


@graph(overloads=bit_or)
def rshift_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise bitwise OR of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(bit_or, lhs, rhs)


@graph(overloads=bit_xor)
def rshift_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    """
    Item-wise bitwise XOR of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_binary_op(bit_xor, lhs, rhs)


@graph(overloads=min_)
def min_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[SCALAR]:
    """
    Minimum of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return min_(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=min_)
def min_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise min() of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(min_, tsbs)


@graph(overloads=max_)
def max_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[SCALAR]:
    """
    Maximum of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return max_(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=max_)
def max_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise max() of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(max_, tsbs)


@graph(overloads=sum_)
def sum_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[SCALAR]:
    """
    Sum of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return sum_(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=sum_)
def sum_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise sum of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(sum_, tsbs)


@graph(overloads=mean)
def mean_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[float]:
    """
    Mean of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return mean(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=mean)
def mean_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise mean of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(mean, tsbs)


@graph(overloads=std)
def std_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[float]:
    """
    Standard deviation of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return std(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=std)
def std_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise standard deviation of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(std, tsbs)


@graph(overloads=var)
def var_tsb_unary(ts: TSB[TS_SCHEMA]) -> TS[float]:
    """
    Variance of all the values in the TSB.  Note that all elements in the TSB must be of the same type
    """
    return std(*(ts[attribute] for attribute in ts.__schema__.__meta_data_schema__))


@graph(overloads=var)
def var_tsbs_multi(*tsbs: TSL[TSB[TS_SCHEMA], SIZE]) -> TSB[TS_SCHEMA]:
    """
    Item-wise variance of TSB elements.
    A missing value on either lhs or rhs causes a gap on the output
    """
    return _itemwise_multi_op(var, tsbs)


@graph(overloads=eq_)
def eq_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TS[bool]:
    """
    Equality of TSBs.
    An asymmetric missing value causes False to be returned
    """
    return all_(*(eq_(lhs[attribute], rhs[attribute])
                  for attribute in lhs.__schema__.__meta_data_schema__))


@graph(overloads=eq_)
def eq_tsbs_different_schemas(lhs: TSB[TS_SCHEMA], rhs: TIME_SERIES_TYPE) -> TS[bool]:
    return False


@graph(overloads=ne_)
def ne_tsbs(lhs: TSB[TS_SCHEMA], rhs: TSB[TS_SCHEMA]) -> TS[bool]:
    return not_(eq_(lhs, rhs))


@graph(overloads=ne_)
def ne_tsbs_different_schemas(lhs: TSB[TS_SCHEMA], rhs: TIME_SERIES_TYPE) -> TS[bool]:
    return False


@graph(overloads=neg_)
def neg_tsb(tsb: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    return _itemwise_unary_op(neg_, tsb)


@graph(overloads=pos_)
def pos_tsb(tsb: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    return _itemwise_unary_op(pos_, tsb)


@graph(overloads=invert_)
def invert_tsb(tsb: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    return _itemwise_unary_op(invert_, tsb)


@graph(overloads=abs_)
def abs_tsb(tsb: TSB[TS_SCHEMA]) -> TSB[TS_SCHEMA]:
    return _itemwise_unary_op(abs_, tsb)


@operator
def tsb_get_item(tsb: TSB[TS_SCHEMA], key: SCALAR) -> TIME_SERIES_TYPE:
    """
    return the item from the tsb that matches the key provided.
    """


@compute_node(overloads=tsb_get_item, resolvers={TIME_SERIES_TYPE: lambda mapping, scalars: mapping[TS_SCHEMA][scalars['key']]})
def tsb_get_item_by_name(tsb: REF[TSB[TS_SCHEMA]], key: str, _schema: Type[TS_SCHEMA] = AUTO_RESOLVE) -> REF[TIME_SERIES_TYPE]:
    """
    Return a reference to an item in the TSB referenced, by its name
    """
    if tsb.value.valid:
        if tsb.value.has_peer:
            return PythonTimeSeriesReference(tsb.value.output[key])
        else:
            item = tsb.value.items[_schema._schema_index_of(key)]
            return item if isinstance(item, TimeSeriesReference) else PythonTimeSeriesReference(item)
    else:
        return PythonTimeSeriesReference()


@compute_node(overloads=tsb_get_item, resolvers={TIME_SERIES_TYPE: lambda mapping, scalars: mapping[TS_SCHEMA][scalars['key']]})
def tsb_get_item_by_index(tsb: REF[TSB[TS_SCHEMA]], key: int, _schema: Type[TS_SCHEMA] = AUTO_RESOLVE) -> REF[TIME_SERIES_TYPE]:
    """
    Return a reference to an item in the TSB referenced, by its name
    """
    if tsb.value.valid:
        if tsb.value.has_peer:
            return PythonTimeSeriesReference(tsb.value.output[key])
        else:
            return PythonTimeSeriesReference(tsb.value[key])
    else:
        return PythonTimeSeriesReference()


@compute_node(overloads=str_)
def str_tsb(tsb: TSB[TS_SCHEMA]) -> TS[str]:
    return str(tsb.value)


def _itemwise_binary_op(op_, lhs, rhs):
    return {attribute: op_(lhs[attribute], rhs[attribute])
            for attribute in lhs.__schema__.__meta_data_schema__}


def _itemwise_unary_op(op_, tsb):
    attributes = tsb.__schema__.__meta_data_schema__
    if len(attributes) == 1:
        return tsb
    else:
        return {attribute: op_(tsb[attribute]) for attribute in attributes}


def _itemwise_multi_op(op_, tsbs):
    return {attribute: op_(*(tsb[attribute] for tsb in tsbs))
            for attribute in tsbs[0].__schema__.__meta_data_schema__}
