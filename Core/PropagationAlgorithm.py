import networkx as nx


class GraphSolver:

    def __init__(self, graph : nx.DiGraph, thisNode : str):
        self.graph = graph
        self.thisNode = thisNode