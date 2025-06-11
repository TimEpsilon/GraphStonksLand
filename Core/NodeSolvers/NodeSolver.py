from abc import ABC, abstractmethod

import networkx as nx
import numpy as np


class NodeSolver(ABC):
    """
    Abstract class onto which each node specific solver is built.
    """
    graph : nx.DiGraph
    thisNode : str
    predecessors : set

    @abstractmethod
    def solver(self):
        pass

    @staticmethod
    def cutTooLow(candidates, threshold=0.001):
        candidates = np.array(candidates)
        candidates = np.round(candidates / threshold) * threshold
        return set(candidates[candidates >= threshold])

    def arePredecessorsSolved(self) -> bool:
        """
        Checks if every incoming node has been solved.
        :return: bool
        """
        return all([p["hasComputed"] for p in self.predecessors])

    def getTruePredecessors(self) -> tuple[set[str], dict[str, float], dict[str, set[float]]]:
        """
        Since the graph has collapsed cycles, but a SCT value is assigned to either a Recipe, an Item or an Ingredient,
        this method gets the SCT and weight values of the "true" predecessors,
        in the sense that this also includes subnodes within a cycle.
        :returns:
        (**predecessors** - the set of incoming nodes
        ; **edgeWeight** - the dictionary of weight values for those nodes (1 per node)
        ; **nodeValue** - the dictionary of SCT values for those nodes (multiple per node))
        """
        predecessors = set()
        edgeWeight = {}
        nodeValue = {}
        for p in predecessors:
            if p["type"] != "cycle":
                predecessors.add(p)
                edgeWeight[p] = self.graph.edges()[p][self.thisNode].get("weight",np.nan)
                nodeValue[p] = self.graph[p]["SCT"]
            else:
                edge = self.graph[p][self.thisNode]
                for e,w in zip(edge["from_subnode"], edge["weight"]):
                    predecessors.add(e)
                    edgeWeight[e] = w
                    nodeValue[e] = self.graph[p]["subgraph"][e]["SCT"]

        return predecessors, edgeWeight, nodeValue
