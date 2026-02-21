import logging

import networkx as nx
import numpy as np

from core.solver.NodeSolver import NodeSolver


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
        self.logger = self._logInit()

    def solve(self):
        """
        # Only Recipes nodes connect to an Item node
        """
        if self.graph.nodes[self.thisNode]["hasComputed"]:
            self.log(f"{self.thisNode} already has a value. Skipping.")
            return
        if self.arePredecessorsSolved():
            # The logic is x = rk / ck
            # For a given node k, there is only one ck but multiple rk
            candidates = dict()
            for p in self.predecessors:
                candidates[p] = self.cutTooLow(np.array(list(self.graph.nodes[p]["SCT"])) / self.graph[p][self.thisNode].get("weight", np.nan))
            if len(candidates) == 0:
                self.log(f"{self.thisNode} has no value. Skipping.")
            self.graph.nodes[self.thisNode]["SCT"] = set().union(*candidates.values())
            self.graph.nodes[self.thisNode]["SCTMap"] = candidates
            self.graph.nodes[self.thisNode]["hasComputed"] = True
            self.log(f"{self.thisNode} has values {candidates}")
        else:
            self.log(f"{self.thisNode} predecessors aren't all Computed", level=logging.WARNING)