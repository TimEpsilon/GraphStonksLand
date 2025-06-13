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

        self.fullPredecessors, self.subTargets, self.predecessorsWeight, self.predecessorsValue = self.getTruePredecessors()

    def solver(self):
        """
        - Init the cycle nodes with only the incoming values
        - Propagate those init values to the whole cycle
        - Do this N times or until convergence.
        """
        if self.arePredecessorsSolved():
            # The logic is Xi = {xi}
            candidates = set.union(*self.predecessorsValue.values())
            candidates = self.cutTooLow(candidates)
            self.graph.nodes[self.thisNode]["SCT"] = candidates
            self.graph.nodes[self.thisNode]["hasComputed"] = True

    def getTruePredecessors(self) -> tuple[set[str], set[str], dict[str, dict[str, float]], dict[str, dict[str, set[float]]]]:
        """
        Since this node is a cycle node, but a SCT value is assigned to either a Recipe, an Item or an Ingredient,
        this method gets the SCT and weight values of the "true" predecessors,
        in the sense that this also includes subnodes within a cycle, and to which subnode they point to.

        To do this, we simply iterate over the "inEdges" attribute. The targeting node serves as a first key to each dict.
        The value is then a dict of the incoming nodes as keys and their weights / SCT values as values.

        :returns:
        (**predecessors** - the set of incoming nodes
        ; **targets** - the set of targets
        ; **edgeWeight** - the dictionary of weight values for those nodes (1 per node)
        ; **nodeValue** - the dictionary of SCT values for those nodes (multiple per node))
        """
        predecessors = set()
        targets = set()
        edgeWeight = {}
        nodeValue = {}
        for e in self.graph.nodes[self.thisNode]["inEdges"]:
            targets.add(e[1])
            predecessors.add(e[0])
            if e[1] not in edgeWeight:
                edgeWeight[e[1]] = {}
                nodeValue[e[1]] = {}
            edgeWeight[e[1]] = {**edgeWeight[e[1]], **{e[0] : e[2]["weight"]}}
            nodeValue[e[1]] = {**nodeValue[e[1]], **{e[0]: self._getSCTofNode(e[0])}}

        return predecessors, targets, edgeWeight, nodeValue

    def _getSCTofNode(self, node : str) -> set[float]:
        if node in self.predecessors:
            return self.graph.nodes[node]["SCT"]
        else:
            for p in self.predecessors:
                if self.graph.nodes[p]["type"] == "cycle" and node in self.graph.nodes[p]["subgraph"].nodes:
                    return self.graph.nodes[p]["subgraph"].nodes[node]["SCT"]
        return {np.nan}

