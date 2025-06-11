import itertools

import networkx as nx
import numpy as np

from Core.NodeSolvers.NodeSolver import NodeSolver


class IngredientSolver(NodeSolver):

    def __init__(self, thisNode : str, graph : nx.DiGraph):
        """
        Logic for an Ingredient Node value calculation.
        :param thisNode: The name of this Node
        :param graph: The graph containing this node
        """
        self.type = "ingredient"
        self.thisNode = thisNode
        self.graph = graph
        self.predecessors = set(self.graph.predecessors(thisNode))

        # Since cycles are involved, we need to unambiguously get the weights and values of each incoming node and subnodes
        # We go from predecessors being a set of Item and Cycle nodes to Item only
        # Item to Ingredient edges holding no weight, self.predecessorsWeight is absent as the weight dict is undefined
        self.fullPredecessors, _, self.predecessorsValue = self.getTruePredecessors()

    def solver(self):
        """
        # Only Item and Cycle nodes connect to an Ingredient node
        """
        if self.arePredecessorsSolved():
            # The logic is Xi = {xi}
            candidates = set.union(*self.predecessorsValue.values())
            candidates = self.cutTooLow(candidates)
            self.graph.nodes[self.thisNode]["SCT"] = candidates
            self.graph.nodes[self.thisNode]["hasComputed"] = True