from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Generic

from hg._impl._types._input import PythonBoundTimeSeriesInput
from hg._impl._types._output import PythonTimeSeriesOutput
from hg._types._time_series_types import TimeSeriesOutput, TimeSeriesInput
from hg._types._tsb_type import TimeSeriesBundleInput, TS_SCHEMA, TimeSeriesBundleOutput

__all__ = ("PythonTimeSeriesBundleOutput", "PythonTimeSeriesBundleInput")

# With Bundles there are two implementation types, namely bound and un-bound.
# Bound bundles are those that are bound to a specific output, and un-bound bundles are those that are not.
# A bound bundle has a peer output of the same shape that this bundle can map directly to. A bound bundle
# has a higher performance characteristic, as it does not need to loop over all the inputs to determine
# things such as active, modified, etc.


@dataclass
class PythonTimeSeriesBundleOutput(PythonTimeSeriesOutput, TimeSeriesBundleOutput[TS_SCHEMA], Generic[TS_SCHEMA]):

    def __init__(self, schema: TS_SCHEMA,*args, **kwargs):
        Generic.__init__(self)
        TimeSeriesBundleOutput.__init__(self, schema)
        PythonTimeSeriesOutput.__init__(self, *args, **kwargs)

    @property
    def value(self):
        return {k: ts.value for k, ts in self.items() if ts.valid}

    @property
    def delta_value(self):
        return {k: ts.delta_value for k, ts in self.items() if ts.modified}

    def apply_result(self, value: Mapping[str, Any]):
        for k, v in value.items():
            self[k].apply_result(v)

    def copy_from_output(self, output: TimeSeriesOutput):
        if not isinstance(output, PythonTimeSeriesBundleOutput):
            raise TypeError(f"Expected {PythonTimeSeriesBundleOutput}, got {type(output)}")
        # TODO: Put in some validation that the signatures are compatible?
        for k, v in output.items():
            self[k].copy_from_output(v)

    def copy_from_input(self, input: TimeSeriesInput):
        if not isinstance(input, TimeSeriesBundleInput):
            raise TypeError(f"Expected {TimeSeriesBundleInput}, got {type(input)}")
        for k, v in input.items():
            self[k].copy_from_input(v)

    def mark_invalid(self):
        if self.valid:
            for v in self._ts_value.values():
                v.mark_invalid()
            super().mark_invalid()

    @property
    def all_valid(self) -> bool:
        return all(ts.valid for ts in self._ts_value.values())


class PythonTimeSeriesBundleInput(PythonBoundTimeSeriesInput, TimeSeriesBundleInput[TS_SCHEMA], Generic[TS_SCHEMA]):
    """
    The bound TSB has a corresponding peer output that it is bound to.
    This means most all methods can be delegated to the output. This is slightly more efficient than the unbound version.
    """

    def __init__(self, schema: TS_SCHEMA, owning_node: "Node" = None, parent_input: "TimeSeriesInput" = None):
        Generic.__init__(self)
        TimeSeriesBundleInput.__init__(self, schema)
        PythonBoundTimeSeriesInput.__init__(self, _owning_node=owning_node, _parent_input=parent_input)

    @property
    def all_valid(self) -> bool:
        return all(ts.valid for ts in self.values())

    @property
    def has_peer(self) -> bool:
        return super().bound

    @property
    def bound(self) -> bool:
        return super().bound or any(ts.bound for ts in self.values())

    def bind_output(self, output: TimeSeriesOutput):
        output: PythonTimeSeriesBundleOutput
        super().bind_output(output)
        for k, ts in self.items():
            ts.bind_output(output[k])

    @property
    def value(self) -> Any:
        if self.has_peer:
            return super().value
        else:
            return {K: ts.value for K, ts in self.items() if ts.valid}

    @property
    def delta_value(self) -> Mapping[str, Any]:
        if self.has_peer:
            return super().delta_value
        else:
            return {k: ts.delta_value for k, ts in self.items() if ts.modified}

    @property
    def active(self) -> bool:
        """
        For UnBound TS, if any of the elements are active we report the input as active,
        Note, that make active / make passive will make ALL instances active / passive.
        Thus, just because the input returns True for active, it does not mean that make_active is a no-op.
        """
        if self.has_peer:
            return super().active
        else:
            return any(ts.active for ts in self.values())

    def make_active(self):
        if self.has_peer:
            super().make_active()
        else:
            for ts in self.values():
                ts.make_active()

    def make_passive(self):
        if self.has_peer:
            super().make_passive()
        else:
            for ts in self.values():
                ts.make_passive()

    @property
    def modified(self) -> bool:
        if self.has_peer:
            return super().modified
        else:
            return any(ts.modified for ts in self.values())

    @property
    def valid(self) -> bool:
        if self.has_peer:
            return super().valid
        else:
            return any(ts.valid for ts in self.values())

    @property
    def last_modified_time(self) -> datetime:
        if self.has_peer:
            return super().last_modified_time
        else:
            return max(ts.last_modified_time for ts in self.values())
