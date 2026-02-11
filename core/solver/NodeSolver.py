import logging
from abc import ABC, abstractmethod
from logging import Logger

import networkx as nx
import numpy as np

class NodeSolver(ABC):
    """
    Abstract class onto which each node specific solver is built.
    """
    graph : nx.DiGraph
    thisNode : str
    predecessors : set
    logger : Logger

    @abstractmethod
    def solve(self):
        pass

    def arePredecessorsSolved(self) -> bool:
        """
        Checks if every incoming node has been solved.
        :return: bool
        """
        return all([self.graph.nodes[p]["hasComputed"] for p in self.predecessors])

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
                        edgeWeight[e[0]] = e[2].get("weight")
                        nodeValue[e[0]] = self.graph.nodes[p]["subgraph"].nodes[e[0]]["SCT"]

        return predecessors, edgeWeight, nodeValue

    def _logInit(self):
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(f'%(levelname)s - %(name)s - %(funcName)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger

    def log(self, message, level=logging.INFO):
        self.logger.log(level, f'{self.thisNode} - {message}', stacklevel=2)


    @staticmethod
    def cutTooLow(candidates, threshold=0.01):
        candidates = np.array(list(candidates)) if len(candidates) > 0 else np.array([0])
        candidates = np.round(candidates / threshold) * threshold
        return set(candidates[candidates >= threshold].astype(float).tolist())

    def selectionMethod(self, values : set):
        result = min(values) if len(values) > 0 else 0
        self.log(f"Candidates {values} have been reduced to {result}", level=logging.DEBUG)
        return {result}
