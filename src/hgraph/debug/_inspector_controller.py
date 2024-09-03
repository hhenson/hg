import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from _socket import gethostname
from perspective import Table

from hgraph import graph, compute_node, TS, STATE, register_adaptor, TSD, CompoundScalar, \
    TimeSeries, PythonNestedNodeImpl, SCHEDULER, Node, Graph, PythonTimeSeriesReference
from hgraph.adaptors.perspective import PerspectiveTablesManager
from hgraph.adaptors.tornado.http_server_adaptor import http_server_handler, HttpRequest, HttpResponse, \
    http_server_adaptor_impl
from hgraph.debug._inspector_observer import InspectionObserver
from hgraph.debug._inspector_util import node_id_from_str, str_node_id, format_value, format_timestamp, enum_items, \
    format_type, name, inspect_item


@graph
def inspector_controller(port: int = 8080):
    @dataclass
    class GraphInspectorData(CompoundScalar):
        id: str
        X: str = "+"
        name: str = None
        type: str = None
        value: str = None
        timestamp: datetime = None
        evals: int = None
        time: float = None
        of_graph: float = None
        of_total: float = None

    @dataclass
    class InspectorState(CompoundScalar):
        observer: InspectionObserver = None
        manager: PerspectiveTablesManager = None
        table: Table = None

        row_ids: dict = field(default_factory=dict)

        key_ids: dict = field(default_factory=dict)
        id_keys: dict = field(default_factory=dict)

        node_subscriptions: dict = field(default_factory=lambda: defaultdict(dict))  # node_id -> [(item path, row_id)]

        value_data: list = field(default_factory=list)
        perf_data: list = field(default_factory=list)
        last_publish_time: datetime = None

        def id_for_key(self, key):
            i = self.key_ids.setdefault(key, len(self.key_ids))
            self.id_keys[i] = key
            return i

        def key_for_id(self, i):
            return self.id_keys[i]

    INPUTS = "zzz001"
    OUTPUT = "zzz002"
    SUBGRAPHS = "zzz003"
    SCALARS = "zzz004"
    MORE = "zzy"
    MORE_ID = node_id_from_str(MORE)[0]

    def process_tick(state: STATE, node: Node):
        for row_id, path in state.node_subscriptions.get(node.node_id, {}).items():
            if row_id is not None:
                if path:
                    match path[0]:
                        case "inputs":
                            v = node.input
                        case "output":
                            v = node.output
                        case "nested":
                            v = node
                        case _:
                            continue

                    for item in path[1:]:
                        try:
                            v = inspect_item(v, item)
                        except:
                            v = "This value could not be retrieved"
                else:
                    v = node

                if isinstance(v, (TimeSeries, Node)):
                    state.value_data.append(dict(
                        id=row_id,
                        value=format_value(v),
                        timestamp=format_timestamp(v),
                    ))
                else:
                    state.value_data.append(dict(
                        id=row_id,
                        value=format_value(v),
                    ))

        if state.last_publish_time is None or (datetime.now() - state.last_publish_time).total_seconds() > 2:
            publish_stats(state)

    def process_graph(state: STATE, graph: Graph):
        root_graph = state.observer.get_graph_info(())
        for node_id, items in state.node_subscriptions.items():
            if node_row := items.get(None, None):
                gi = state.observer.get_graph_info(node_id[:-1])
                node_ndx = node_id[-1]
                state.perf_data.append(dict(
                    id=node_row,
                    evals=gi.node_eval_counts[node_ndx],
                    time=gi.node_eval_times[node_ndx] / 1_000_000_000,
                    of_graph=gi.node_eval_times[node_ndx] / gi.eval_time if gi.eval_time else None,
                    of_total=gi.node_eval_times[node_ndx] / root_graph.eval_time if root_graph.eval_time else None
                ))

        if state.last_publish_time is None or (datetime.now() - state.last_publish_time).total_seconds() > 2:
            publish_stats(state)

    def publish_stats(state: STATE):
        state.manager.update_table("inspector", state.value_data)
        state.value_data = []

        state.manager.update_table("inspector", state.perf_data)
        state.perf_data = []

        state.last_publish_time = datetime.now()

    @compute_node
    def inspector(request: TSD[int, TS[HttpRequest]], port: int = 8080, _state: STATE[InspectorState] = None, _sched: SCHEDULER = None) -> TSD[int, TS[HttpResponse]]:
        responses = {}  # for the HTTP queries
        data = []  # to be published to the table
        remove = set()  # to be removed from the table

        if _sched.is_scheduled_now:
            request.owning_graph.evaluation_engine.add_after_evaluation_notification(
                lambda: publish_stats(_state)
            )
            _sched.schedule(timedelta(seconds=1))
        elif not _sched.is_scheduled:
            _sched.schedule(timedelta(seconds=1))

        if _state.observer is None:
            _state.observer = InspectionObserver(
                request.owning_graph,
                callback_node=lambda n: process_tick(_state, n),
                callback_graph=lambda n: process_graph(_state, n)
            )
            _state.observer.on_before_node_evaluation(request.owning_node)
            _state.observer.subscribe(())
            request.owning_graph.evaluation_engine.add_life_cycle_observer(_state.observer)

        observer = _state.observer

        for r_i, r_r in request.modified_items():
            r: HttpRequest = r_r.value

            command = r.url_parsed_args[0]
            id_str = r.url_parsed_args[1]
            level = "graph"

            if id_str[-6:-3] == MORE:
                more = node_id_from_str(id_str[-3:])[0]
                id_str = id_str[:-6]
            else:
                more = None

            if id_str.endswith(INPUTS):
                level = "inputs"
                id_str_node = id_str[:-6]
            elif id_str.endswith(OUTPUT):
                level = "output"
                id_str_node = id_str[:-6]
            elif id_str.endswith(SUBGRAPHS):
                level = "nested"
                id_str_node = id_str[:-6]
            elif id_str.endswith(SCALARS):
                level = "scalars"
                id_str_node = id_str[:-6]
            else:
                id_str_node = id_str

            if id_str_node == '':
                graph_id = ()
                level = "graph"
                path = None
            else:
                graph_id = _state.row_ids[id_str_node]
                path = _state.node_subscriptions[graph_id][id_str]

            if (gi := observer.get_graph_info(graph_id)) is None:
                level = "node" if level == "graph" else level
                node_id = graph_id[-1]
                graph_id = graph_id[:-1]
                if (gi := observer.get_graph_info(graph_id)) is None:
                    responses[r_i] = HttpResponse(status_code=500, body=f"Graph {graph_id} was not found")
                    continue
                node = gi.graph.nodes[node_id]

            if path is not None:
                level = path[0]
                if len(path) == 2 and level == "nested":
                    try:
                        graph = inspect_item(node, path[1])
                        graph_id = graph.graph_id
                        gi = observer.get_graph_info(graph_id)
                        level = "graph"
                    except:
                        responses[r_i] = HttpResponse(status_code=500, body=f"Graph {graph_id}, {path[1]} was not found")
                        continue
                
            if level == "output":
                root_item = node.output
                level = "value"
            elif level == "inputs":
                root_item = node.input
                level = "value"
            elif level == "nested":
                root_item = node
                level = "value"
            elif level == "scalars":
                root_item = node.scalars
                level = "value"

            match command:
                case "expand":
                    tab = "\u00A0\u00A0" * (len(id_str) // 3)

                    if id_str:
                        data.append(dict(id=id_str, X="-"))

                    match level:
                        case "graph":
                            for i, n in enumerate(gi.graph.nodes):
                                row_id = id_str + str_node_id((i,))
                                data.append(dict(
                                    id=row_id,
                                    X="+",
                                    name=tab + name(gi.graph.nodes[i]),
                                    type=format_type(n),
                                    value=format_value(n),
                                    timestamp=format_timestamp(n)))

                                _state.node_subscriptions[n.node_id][row_id] = None
                                _state.node_subscriptions[n.node_id][None] = row_id
                                _state.observer.subscribe(n.node_id)
                                _state.row_ids[row_id] = n.node_id

                        case "node":
                            if node.input is not None:
                                row_id = id_str + INPUTS
                                data.append(dict(
                                    id=row_id,
                                    X="+",
                                    name=tab + "INPUTS",
                                    type=format_type(node.input),
                                    value=format_value(node.input),
                                    timestamp=format_timestamp(node.input)))

                                _state.node_subscriptions[node.node_id][row_id] = ["inputs"]
                                _state.row_ids[row_id] = node.node_id

                            if node.output is not None:
                                row_id = id_str + OUTPUT
                                data.append(dict(
                                    id=row_id,
                                    X="+",
                                    name=tab + "OUTPUT",
                                    type=format_type(node.output),
                                    value=format_value(node.output),
                                    timestamp=format_timestamp(node.output)))

                                _state.node_subscriptions[node.node_id][row_id] = ["output"]
                                _state.row_ids[row_id] = node.node_id

                            if isinstance(node, PythonNestedNodeImpl):
                                row_id = id_str + SUBGRAPHS
                                data.append(dict(
                                    id=row_id,
                                    X="+",
                                    name=tab + "GRAPHS",
                                    type="",
                                    value=format_value(node.input),
                                    timestamp=format_timestamp(node.input)))

                                _state.row_ids[row_id] = None
                                _state.node_subscriptions[node.node_id][row_id] = ["nested"]

                            if node.scalars:
                                row_id = id_str + SCALARS
                                data.append(dict(
                                    id=row_id,
                                    X="+",
                                    name=tab + "SCALARS",
                                    type="",
                                    value=format_value(node.scalars),
                                    timestamp=format_timestamp(node.scalars)))

                                _state.row_ids[row_id] = None
                                _state.node_subscriptions[node.node_id][row_id] = ["scalars"]

                        case "value":
                            start = 0
                            path = [] if path is None else path
                            for key in path[1:]:
                                try:
                                    root_item = inspect_item(root_item, key)
                                    path.append(key)
                                except:
                                    root_item = None
                                    responses[r_i] = HttpResponse(status_code=500, body=f"Item cannot be inspected")
                                    break

                            if more is not None:
                                start = more
                                remove.add(id_str + MORE + str_node_id((start,)))

                            if root_item:
                                for i, (k, v) in enumerate(enum_items(root_item)):
                                    if i < start:
                                        continue
                                    if i >= start + 10 and not 'all' in r.query:
                                        row_id = id_str + MORE + str_node_id((i,))
                                        data.append(dict(
                                            id=row_id,
                                            X="+",
                                            name=tab + "...",
                                            type="",
                                        ))
                                        _state.row_ids[row_id] = None
                                        break

                                    ts = isinstance(v, TimeSeries)
                                    row_id = id_str + str_node_id((_state._value.id_for_key(k),))
                                    data.append(dict(
                                        id=row_id,
                                        X="+",
                                        name=tab + str(k),
                                        type=format_type(v),
                                        value=format_value(v),
                                        timestamp=format_timestamp(v) if ts else "-"
                                    ))

                                    _state.node_subscriptions[node.node_id][row_id] = path + [k]
                                    _state.row_ids[row_id] = node.node_id

                                remove.add(id_str + MORE + str_node_id((start,)))

                case "collapse":
                    remove |= {i for i in _state.row_ids if i.startswith(id_str)} - {id_str}
                    for i in remove:
                        if node_id := _state.row_ids.get(i):
                            (subs := _state.node_subscriptions[node_id]).pop(i, None)
                            if len(subs) == 0:
                                _state.observer.unsubscribe(node_id)

                    data.append(dict(id=id_str, X="+"))

                case "ref":
                    path = [] if path is None else path
                    for key in path[1:]:
                        try:
                            root_item = inspect_item(root_item, key)
                            path.append(key)
                        except:
                            root_item = None
                            responses[r_i] = HttpResponse(status_code=500, body=f"Item cannot be inspected")
                            break

                    if isinstance(root_item, PythonTimeSeriesReference):
                        if (o := root_item.output) is not None:
                            ref_node = o.owning_node
                            path = []
                            while o.parent_output:
                                path.append(o.parent_output.key_from_value(o))
                                o = o.parent_output

                            for i in range(ref_node.node_id):
                                graph_id = ref_node.node_id[:i]
                                if (gi := observer.get_graph_info(graph_id)) is None:
                                    responses[r_i] = HttpResponse(status_code=500, body=f"Graph {graph_id} was not found")
                                    continue


            if data or remove:
                _state.manager.update_table("inspector", data, remove)
                [_state.row_ids.pop(i, None) for i in remove]

            responses[r_i] = HttpResponse(status_code=200, body=id_str)

        return responses

    @inspector.start
    def start_inspector(port: int, _state: STATE[InspectorState]):
        from hgraph.adaptors.perspective import PerspectiveTablesManager
        from hgraph.adaptors.tornado._tornado_web import TornadoWeb
        from hgraph.adaptors.perspective._perspective import IndexPageHandler
        from perspective import Table

        _state.manager = PerspectiveTablesManager.current()
        _state.table = Table({"id": str, **{k: v.py_type for k, v in GraphInspectorData.__meta_data_schema__.items()}}, index="id")
        _state.manager.add_table("inspector", _state.table)

        tempfile.gettempdir()
        layouts_dir = os.path.join(tempfile.tempdir, "inspector_layouts")

        app = TornadoWeb.instance(port)
        app.add_handlers(
            [
                (
                    r"/inspector/(.*)",
                    IndexPageHandler,
                    {
                        "mgr": _state.manager,
                        "layouts_path": layouts_dir,
                        "index_template": os.path.join(os.path.dirname(__file__), "inspector_template.html"),
                        "host": gethostname(),
                        "port": port,
                    },
                ),
            ]
        )

    http_server_handler(inspector, url=f"/inspect(?:/([^/]*))?(?:/([^/]*))?(/([^/]*))?")

    register_adaptor("http_server_adaptor", http_server_adaptor_impl, port=port)