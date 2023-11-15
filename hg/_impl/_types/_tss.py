from dataclasses import dataclass, field
from typing import Generic, Iterable, Any, Set

from hg._impl._types._input import PythonBoundTimeSeriesInput
from hg._types._scalar_types import SCALAR
from hg._impl._types._output import PythonTimeSeriesOutput
from hg._types._tss_type import SetDelta, TimeSeriesSetOutput, TimeSeriesSetInput


__all__ = ("PythonSetDelta", "PythonTimeSeriesSetOutput", "PythonTimeSeriesSetInput")


@dataclass(frozen=True)
class PythonSetDelta(SetDelta[SCALAR], Generic[SCALAR]):

    added: frozenset[SCALAR]
    removed: frozenset[SCALAR]

    @property
    def added_elements(self) -> Iterable[SCALAR]:
        return self.added

    @property
    def removed_elements(self) -> Iterable[SCALAR]:
        return self.removed


@dataclass
class PythonTimeSeriesSetOutput(PythonTimeSeriesOutput, TimeSeriesSetOutput[SCALAR], Generic[SCALAR]):

    _tp: type = None
    _value: set[SCALAR] = field(default_factory=set)
    _added: frozenset[SCALAR] | None = None
    _removed: frozenset[SCALAR] | None = None

    @property
    def value(self) -> Set[SCALAR]:
        return self._value

    @property
    def delta_value(self) -> SetDelta[SCALAR]:
        return PythonSetDelta(frozenset(self._added), frozenset(self._removed))

    def apply_result(self, result: Any):
        if result is None:
            return
        if isinstance(result, SetDelta):
            self._added = frozenset(e for e in result.added_elements if e not in self._value)
            self._removed = frozenset(e for e in result.removed_elements if e in self._value)
            if self._removed.intersection(self._added):
                raise ValueError("Cannot remove and add the same element")
            self._value.update(self._added)
            self._value.difference_update(self._removed)
        else:
            # Assume that the result is a set, and then we are adding all the elements
            self._added = frozenset(result)
            self._removed = frozenset()
            self._value.update(self._added)
        if self._added or self._removed or not self.valid:
            self.mark_modified()

    def mark_modified(self):
        super().mark_modified()
        self.owning_graph.context.add_after_evaluation_notification(self._reset)

    def _reset(self):
        self._added = None
        self._removed = None

    def copy_from_output(self, output: "TimeSeriesOutput"):
        self._added = frozenset(output.value.difference(self._value))
        self._removed = frozenset()
        if self._added:
            self._value.update(self._added)
            self.mark_modified()

    def copy_from_input(self, input: "TimeSeriesInput"):
        self._added = frozenset(input.value.difference(self._value))
        self._removed = frozenset()
        if self._added:
            self._value.update(self._added)
            self.mark_modified()

    def __contains__(self, item: SCALAR) -> bool:
        return item in self._value

    def values(self) -> Iterable[SCALAR]:
        return self._value

    def added(self) -> Iterable[SCALAR]:
        return self._added

    def was_added(self, item: SCALAR) -> bool:
        return item in self._added

    def removed(self) -> Iterable[SCALAR]:
        return self._removed

    def was_removed(self, item: SCALAR) -> bool:
        return item in self._removed


class PythonTimeSeriesSetInput(PythonBoundTimeSeriesInput, TimeSeriesSetInput[SCALAR], Generic[SCALAR]):

    output: TimeSeriesSetOutput[SCALAR]

    def __contains__(self, item: SCALAR) -> bool:
        return self.output.__contains__(item)

    def values(self) -> Iterable[SCALAR]:
        return self.output.values()

    def added(self) -> Iterable[SCALAR]:
        return self.output.added()

    def was_added(self, item: SCALAR) -> bool:
        return self.output.was_added(item)

    def removed(self) -> Iterable[SCALAR]:
        return self.output.removed()

    def was_removed(self, item: SCALAR) -> bool:
        return self.was_removed(item)