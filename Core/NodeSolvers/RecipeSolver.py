import itertools

import networkx as nx
import numpy as np

from Core.NodeSolvers.NodeSolver import NodeSolver


class RecipeSolver(NodeSolver):

    def __init__(self, thisNode : str, graph : nx.DiGraph):
        """
        Logic for a Recipe Node value calculation.
        :param thisNode: The name of this Node
        :param graph: The graph containing this node
        """
        self.type = "recipe"
        self.thisNode = thisNode
        self.graph = graph
        self.predecessors = set(self.graph.predecessors(thisNode))

        # Since cycles are involved, we need to unambiguously get the weights and values of each incoming node and subnodes
        # We go from predecessors being a set of Ingredient and Cycle nodes to Ingredient only
        self.fullPredecessors, self.predecessorsWeight, self.predecessorsValue = self.getTruePredecessors()

    def solver(self):
        """
        # Only Ingredient and Cycle nodes connect to a Recipe node
        """
        if self.arePredecessorsSolved():
            # The logic is r = sum(Xi * ci)
            # For a given node i, there is only one ci but multiple Xi
            # Since there are multiple Xi for each i, we must compute every configuration of Xi
            keys = list(self.predecessorsValue.keys())
            values = [np.array(list(self.predecessorsValue[k]), dtype=np.float64) for k in keys]
            weights = np.array([self.predecessorsWeight[k] for k in keys], dtype=np.float64)

            # Cartesian product via itertools, results in list of tuples
            combos = np.array(list(itertools.product(*values)), dtype=np.float64)  # shape: (n_combos, n_keys)

            # Weighted sum along axis 1 (dot product with weights)
            candidates = self.cutTooLow(combos @ weights)
            self.graph.nodes[self.thisNode]["SCT"] = candidates
            self.graph.nodes[self.thisNode]["hasComputed"] = True

