import networkx as nx
import numpy as np

from Core.NodeSolvers.NodeSolver import NodeSolver


class ItemSolver(NodeSolver):

    def __init__(self, thisNode : str, graph : nx.DiGraph):
        """
        Logic for an Item Node value calculation.
        :param thisNode: The name of this Node
        :param graph: The graph containing this node
        """
        self.type = "item"
        self.thisNode = thisNode
        self.graph = graph
        self.predecessors = set(self.graph.predecessors(thisNode))

    def solver(self):
        """
        # Only Recipes nodes connect to an Item node
        """
        if self.arePredecessorsSolved():
            # The logic is x = rk / ck
            # For a given node k, there is only one ck but multiple rk
            candidates = [np.array(self.graph.nodes[p]["SCT"]) / self.graph[p][self.thisNode].get("weight", np.nan) for p in self.predecessors]
            candidates = np.concatenate(candidates)
            candidates = self.cutTooLow(candidates)
            self.graph.nodes[self.thisNode]["SCT"] = candidates
            self.graph.nodes[self.thisNode]["hasComputed"] = True