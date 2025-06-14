from abc import ABC, abstractmethod
from typing import Optional

import networkx as nx
import numpy as np

from core.utils.Logger import Logger


class NodeSolver(ABC):
    """
    Abstract class onto which each node specific solver is built.
    """
    graph : nx.DiGraph
    thisNode : str
    predecessors : set
    logger: Optional[Logger] = None

    @abstractmethod
    def solver(self):
        pass

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
        for p in self.predecessors:
            if self.graph.nodes[p]["type"] != "cycle":
                predecessors.add(p)
                edgeWeight[p] = self.graph[p][self.thisNode].get("weight",np.nan)
                nodeValue[p] = self.graph.nodes[p]["SCT"]
            else:
                for e in self.graph.nodes[p]["outEdges"]:
                    if e[1] == self.thisNode:
                        predecessors.add(e[0])
                        edgeWeight[e[0]] = e[2]["weight"]
                        nodeValue[e[0]] = self.graph.nodes[p]["subgraph"].nodes[e[0]]["SCT"]

        return predecessors, edgeWeight, nodeValue

    def log(self, message):
        self.logger.log(message)

    def initLogger(self):
        self.logger = Logger(self.__class__, self)


    @staticmethod
    def cutTooLow(candidates, threshold=0.001):
        candidates = np.array(candidates)
        candidates = np.round(candidates / threshold) * threshold
        return set(candidates[candidates >= threshold])
