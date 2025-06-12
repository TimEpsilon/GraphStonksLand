import networkx as nx
import numpy as np

from Core.NodeSolvers.NodeSolver import NodeSolver


class CycleSolver(NodeSolver):

    def __init__(self, thisNode : str, graph : nx.DiGraph):
        """
        Logic for a Cycle Node values calculations.
        :param thisNode: The name of this Node
        :param graph: The graph containing this node
        """
        self.type = "cycle"
        self.thisNode = thisNode
        self.graph = graph
        self.predecessors = set(self.graph.predecessors(thisNode))
        self.subgraph = self.graph[self.thisNode]["subgraph"]

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

    def getTruePredecessors(self) -> tuple[set[str], dict[str, float], dict[str, set[float]]]:
        """
        Since the graph has collapsed cycles, but a SCT value is assigned to either a Recipe, an Item or an Ingredient,
        this method gets the SCT and weight values of the "true" predecessors,
        in the sense that this also includes subnodes within a cycle.

        Since we are working with a cycle node, incoming edges can either come from a normal node, or from a Cycle node.
        The logic of this is already decide by the base method.
        However, these edges point to subnodes within this cycle. We thus need to keep track of the targets of each predecessor.
        The edges will hold "to_subnode" which will target one of the subnodes within the cycle.

        :returns:
        (**predecessors** - the set of incoming nodes
        ; **edgeWeight** - the dictionary of weight values for those nodes (1 per node)
        ; **nodeValue** - the dictionary of SCT values for those nodes (multiple per node))
        ; **targets** - the set of target nodes
        """
        predecessors = set()
        edgeWeight = {}
        nodeValue = {}
        targets = {}
        for p in predecessors:
            if p["type"] != "cycle":
                predecessors.add(p)
                edgeWeight[p] = self.graph.edges()[p][self.thisNode].get("weight",np.nan)
                nodeValue[p] = self.graph[p]["SCT"]
                targets[p] = self.graph.edges()[p][self.thisNode]["to_subnode"]
            else:
                edge = self.graph[p][self.thisNode]
                for e,w,t in zip(edge["from_subnode"], edge["weight"], edge["to_subnode"]):
                    predecessors.add(e)
                    edgeWeight[e] = w
                    nodeValue[e] = self.graph[p]["subgraph"][e]["SCT"]
                    targets[e] = t

        return predecessors, edgeWeight, nodeValue