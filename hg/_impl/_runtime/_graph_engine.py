from dataclasses import dataclass, field
from datetime import datetime, timedelta

from hg._runtime._constants import MIN_DT, MAX_DT
from hg._runtime._graph_engine import GraphEngine, RunMode, GraphExecutorLifeCycleObserver
from hg._runtime._lifecycle import start_stop_context
from hg._runtime import Graph, ExecutionContext


class BackTestExecutionContext(ExecutionContext):

    def __init__(self, current_time: datetime):
        self.current_engine_time = current_time
        self._proposed_next_engine_time: datetime = MAX_DT

    def wait_until_proposed_engine_time(self, proposed_engine_time: datetime) -> datetime:
        self._current_time = proposed_engine_time
        return proposed_engine_time

    @property
    def proposed_next_engine_time(self) -> datetime:
        return self._proposed_next_engine_time

    @property
    def current_engine_time(self) -> datetime:
        return self._current_time

    @current_engine_time.setter
    def current_engine_time(self, value: datetime):
        self._current_time = value
        self._wall_clock_time_at_current_time = datetime.now()

    @property
    def wall_clock_time(self) -> datetime:
        return self._current_time + self.engine_lag

    @property
    def engine_lag(self) -> timedelta:
        return datetime.now() - self._wall_clock_time_at_current_time

    @property
    def push_has_pending_values(self) -> bool:
        return False

    def reset_push_has_pending_values(self):
        pass  # Nothing to do


@dataclass
class PythonGraphEngine(GraphEngine):
    """
    A graph engine that runs the graph in python.
    """

    graph: "Graph"
    is_started: bool = False
    _stop_requested: bool = False
    _start_time: datetime = None
    _end_time: datetime = None
    _scheduler: [datetime] = None
    _execution_context: ExecutionContext = None
    _run_mode: RunMode = None
    _life_cycle_observers: [GraphExecutorLifeCycleObserver] = field(default_factory=list)
    _before_evaluation_notification: [callable] = field(default_factory=list)
    _after_evaluation_notification: [callable] = field(default_factory=list)

    def __init__(self, graph: Graph, run_mode: RunMode):
        self._graph = graph
        self._run_mode = run_mode

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def run_mode(self) -> RunMode:
        return self._run_mode

    def initialise(self):
        self._scheduler = [MIN_DT] * len(self.graph.nodes)

    def start(self):
        if not self.is_started:
            self.is_started = True
            self._stop_requested = False
            match self._run_mode:
                case RunMode.REAL_TIME:
                    raise NotImplementedError()
                case RunMode.BACK_TEST:
                    self._execution_context = BackTestExecutionContext(self._start_time)
            self.notify_before_start()
            for node in self.graph.nodes:
                self.notify_before_start_node(node)
                node.start()
                self.notify_after_start_node(node)
            self.notify_after_start()

    def stop(self):
        if self.is_started:
            self.is_started = False
            self.notify_before_stop()
            for node in self.graph.nodes:
                self.notify_before_stop_node(node)
                node.stop()
                self.notify_before_start_node(node)
            self.notify_after_stop()
            self._execution_context = None

    def request_stop(self):
        self._stop_requested = True

    def dispose(self):
        ...

    def advance_engine_time(self):
        if self._stop_requested:
            self._execution_context.current_engine_time = self._end_time
            return

        proposed_next_engine_time = self._execution_context.proposed_next_engine_time
        wall_clock_time = self._execution_context.wall_clock_time
        if wall_clock_time >= proposed_next_engine_time:
            self._execution_context.current_engine_time = proposed_next_engine_time
            return

        if self._execution_context.push_has_pending_values:
            self._execution_context.current_engine_time = wall_clock_time
            return

        # We have nothing to do just yet, wait until the next proposed engine time (or a push node is scheduled)
        self._execution_context.wait_until_proposed_engine_time(proposed_next_engine_time)

    def evaluate_graph(self):
        self.notify_before_evaluation()
        now = self._execution_context.current_engine_time
        nodes = self.graph.nodes

        if self._execution_context.push_has_pending_values:
            self._execution_context.reset_push_has_pending_values()
            for i in range(self.graph.push_source_nodes_end):
                nodes[i].eval() # This is only to move nodes on, won't call the before and after node eval here

        for i in range(self.graph.push_source_nodes_end, len(nodes)):
            scheduled_time, node = nodes[i]
            if scheduled_time == now:
                self.notify_before_node_evaluation(node)
                node.eval()
                self.notify_after_node_evaluation(node)

        self.notify_after_evaluation()

    def run(self, start_time: datetime, end_time: datetime):
        self._start_time = start_time
        self._end_time = end_time

        if end_time < start_time:
            raise ValueError("End time cannot be before the start time")

        with start_stop_context(self):
            while self._execution_context.current_engine_time <= end_time:
                self.evaluate_graph()
                self.advance_engine_time()

    def add_life_cycle_observer(self, observer: GraphExecutorLifeCycleObserver):
        self._life_cycle_observers.append(observer)

    def remove_life_cycle_observer(self, observer: GraphExecutorLifeCycleObserver):
        self._life_cycle_observers.remove(observer)

    def notify_before_evaluation(self):
        for notification_receiver in self._before_evaluation_notification:
            notification_receiver()
        self._before_evaluation_notification.clear()
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_evaluation(self.graph)

    def notify_after_evaluation(self):
        for notification_receiver in self._after_evaluation_notification:
            notification_receiver()
        self._after_evaluation_notification.clear()
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_evaluation(self.graph)

    def notify_before_node_evaluation(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_node_evaluation(node)

    def notify_after_node_evaluation(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_node_evaluation(node)

    def notify_before_start(self):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_start(self.graph)

    def notify_after_start(self):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_start(self.graph)

    def notify_before_stop(self):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_stop(self.graph)

    def notify_after_stop(self):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_stop(self.graph)

    def notify_before_start_node(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_start_node(node)

    def notify_after_start_node(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_start_node(node)

    def notify_before_stop_node(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_before_stop_node(node)

    def notify_after_stop_node(self, node):
        for life_cycle_observer in self._life_cycle_observers:
            life_cycle_observer.on_after_stop_node(node)
