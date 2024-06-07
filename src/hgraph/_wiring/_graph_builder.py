import typing
from collections import defaultdict, deque

from hgraph._runtime._node import NodeTypeEnum
from hgraph._wiring._wiring_errors import CustomMessageWiringError
from hgraph._wiring._wiring_node_signature import WiringNodeType
from hgraph._wiring._wiring_port import WiringPort

if typing.TYPE_CHECKING:
    from hgraph._builder._graph_builder import GraphBuilder, GraphBuilderFactory
    from hgraph._wiring._wiring_node_instance import WiringNodeInstance

__all__ = ("wire_graph", "create_graph_builder")


def wire_graph(graph, *args, **kwargs) -> "GraphBuilder":
    """
    Evaluate the wiring graph and build a runtime graph.
    This graph is the actual graph objects that are used to be evaluated.
    """
    from hgraph._wiring._wiring_node_class._graph_wiring_node_class import WiringGraphContext

    from hgraph._builder._ts_builder import TimeSeriesBuilderFactory
    from hgraph._wiring._wiring_errors import WiringError

    if not TimeSeriesBuilderFactory.has_instance():
        TimeSeriesBuilderFactory.declare_default_factory()

    try:
        with WiringGraphContext(None) as context:
            out = graph(*args, **kwargs)
            # For now let's ensure that top level graphs do not return anything.
            # Later we can consider default behaviour for graphs with outputs.
            assert out is None, "Currently only graph with no return values are supported"

            context.build_services()

            # Build graph by walking from sink nodes to parent nodes.
            # Also eliminate duplicate nodes
            sink_nodes = context.sink_nodes
            return create_graph_builder(sink_nodes)
    except WiringError as e:
        e.print_error()
        raise e


def create_graph_builder(sink_nodes: tuple["WiringNodeInstance"], supports_push_nodes: bool = True) -> "GraphBuilder":
    """
    Create a graph builder instance. This is called with the sink_nodes created during the wiring of a graph.
    This is extracted to support nested graph construction, where the sink nodes are limited to the new nested graph,
    but we wish to keep the nesting to allow for better debug information to be accumulated.
    """
    from hgraph._wiring._wiring_node_class._wiring_node_class import WiringNodeInstance
    from hgraph._builder._graph_builder import Edge
    from hgraph._builder._node_builder import NodeBuilder
    from hgraph._builder._graph_builder import GraphBuilderFactory

    if not sink_nodes:
        raise RuntimeError("No sink nodes found in graph")

    ranked_nodes = toposort(sink_nodes, supports_push_nodes)

    # Now we can walk the tree in rank order and construct the nodes
    node_map: dict[WiringNodeInstance, int] = {}
    node_builders: [NodeBuilder] = []
    edges: set[Edge] = set[Edge]()
    for wiring_node in ranked_nodes:
        if wiring_node.is_stub:
            continue
        ndx = len(node_builders)
        node_builder, input_edges = wiring_node.create_node_builder_and_edges(node_map, node_builders)
        node_builders.append(node_builder)
        edges.update(input_edges)
        node_map[wiring_node] = ndx

    return GraphBuilderFactory.make(node_builders=tuple[NodeBuilder, ...](node_builders),
                                    edges=tuple[Edge, ...](
                                        sorted(edges,
                                               key=lambda e: (
                                                   e.src_node, e.dst_node, e.output_path, e.input_path))))


def toposort(nodes: typing.Sequence["WiringNodeInstance"],
             supports_push_nodes: bool = True) -> typing.Sequence["WiringNodeInstance"]:
    mapping: dict["WiringNodeInstance", set["WiringNodeInstance"]] = defaultdict(set)
    nodes_to_process: deque["WiringNodeInstance"] = deque(nodes)
    source_nodes = set()
    processed_nodes = dict["WiringNodeInstance", int]()
    # Build node adjacency matrix and collect source nodes.
    while len(nodes_to_process) > 0:
        to_node = nodes_to_process.popleft()
        if to_node in processed_nodes:  # This could be done better
            continue  # This node has already been processed
        else:
            processed_nodes[to_node] = 1
        ts_nodes = [n.node_instance for n in to_node.inputs.values() if isinstance(n, WiringPort)]
        ts_nodes.extend(n for n in to_node.rank_marker.values())
        for from_node in ts_nodes:
            mapping[from_node].add(to_node)
            if from_node.is_source_node:
                source_nodes.add(from_node)
                processed_nodes[from_node] = 1  # Since we are not going to add for processing
            else:
                nodes_to_process.append(from_node)
    # Rank nodes
    nodes_to_process.extend(source_nodes)
    max_rank = 0
    while len(nodes_to_process) > 0:
        from_node = nodes_to_process.pop()
        if not supports_push_nodes and from_node.resolved_signature.node_type is NodeTypeEnum.PUSH_SOURCE_NODE:
            raise CustomMessageWiringError(
                f'Node: {from_node.resolved_signature} is a push source node, '
                f'but this graph does not support push nodes.')
        if from_node.resolved_signature.node_type is WiringNodeType.PUSH_SOURCE_NODE:
            # We re-set to 0 if this is a push source node to ensure they all left-align
            processed_nodes[from_node] = 0
        for to_node in mapping[from_node]:
            processed_nodes[to_node] = max(processed_nodes[to_node], processed_nodes[from_node] + 1)  # increment
            nodes_to_process.append(to_node)
            max_rank = max(max_rank, processed_nodes[to_node])

    # Set sink nodes to be max rank
    for node in nodes:
        processed_nodes[node] = max_rank

    # Sort nodes by rank
    result = [node for _, node in sorted((rank, node) for node, rank in processed_nodes.items()) if not node.is_stub]
    # if not all(n.rank <= n_1.rank for n, n_1 in zip(result[:-1], result[1:])):
    #     raise RuntimeError("not correctly ranked")
    return result
