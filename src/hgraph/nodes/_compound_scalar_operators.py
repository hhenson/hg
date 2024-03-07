from typing import Type

from hgraph import compute_node, COMPOUND_SCALAR, TS, SCALAR, HgTypeMetaData, IncorrectTypeBinding, MissingInputsError, \
    WiringContext, with_signature, TimeSeries
from hgraph._runtime._operators import getattr_


@compute_node(overloads=getattr_, resolvers={SCALAR: lambda mapping, scalars: mapping[COMPOUND_SCALAR].meta_data_schema[scalars['attr']].py_type})
def getattr_cs(ts: TS[COMPOUND_SCALAR], attr: str) -> TS[SCALAR]:
    return getattr(ts.value, attr, None)


def from_ts(cls: Type[COMPOUND_SCALAR], **kwargs) -> TS[SCALAR]:
    scalar_schema = cls.__meta_data_schema__
    kwargs_schema = {k: HgTypeMetaData.parse_value(v) for k, v in kwargs.items()}

    with WiringContext(current_signature=dict(signature=f"from_ts({cls.__name__}, ...)")):
        for k, t in scalar_schema.items():
            if (kt := kwargs_schema.get(k)) is None:
                if getattr(cls, k, None) is None:
                    raise MissingInputsError(kwargs)
            elif not t.matches(kt if kt.is_scalar else kt.scalar_type()):
                raise IncorrectTypeBinding(t, kwargs_schema[k])

        @compute_node
        @with_signature(kwargs=kwargs_schema, return_annotation=TS[cls])
        def from_ts_node(**kwargs):
            return cls(**{k: v if not isinstance(v, TimeSeries) else v.value for k, v in kwargs.items()})

        return from_ts_node(**kwargs)
