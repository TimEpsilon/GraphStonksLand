import itertools

import networkx as nx
import numpy as np

from core.solver.NodeSolver import NodeSolver


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
        self.subgraph : nx.DiGraph = self.graph.nodes[self.thisNode]["subgraph"]
        self.initLogger()

        self.fullPredecessors, self.subTargets, self.predecessorsWeight, self.predecessorsValue = self.getTruePredecessors()

    def solver(self):
        """
        - Init the cycle nodes with only the incoming values
        - Propagate those init values to the whole cycle
        - Do this N times or until convergence.
        """
        if self.arePredecessorsSolved():
            # 1 - Init the cycle nodes
            for target in self.subTargets:
                targetType = self.subgraph[target]["type"]
                weights, values = self.predecessorsWeight[target], self.predecessorsValue[target]

                if targetType == "item":
                    # The logic is x = rk / ck
                    candidates = [np.array(values[p]) / weights[p] for p in values.keys()]
                    candidates = set(np.concatenate(candidates))
                elif targetType == "ingredient":
                    # The logic is Xi = {xi}
                    candidates = set.union(*values.values())
                elif targetType == "recipe":
                    # The logic is r = sum(Xi * ci)
                    keys = list(values.keys())
                    valuesCartesian = [np.array(list(values[k]), dtype=np.float64) for k in keys]
                    weightsCartesian = np.array([weights[k] for k in keys], dtype=np.float64)

                    # Cartesian product via itertools, results in list of tuples
                    combos = np.array(list(itertools.product(*valuesCartesian)), dtype=np.float64)  # shape: (n_combos, n_keys)

                    # Weighted sum along axis 1 (dot product with weights)
                    candidates = set(combos @ weightsCartesian)
                else :
                    candidates = set()
                candidates = self.cutTooLow(candidates)
                self.subgraph.nodes[target]["SCT"] = candidates
                self.subgraph.nodes[target]["originalSCT"] = candidates # This serves for recipe nodes

            # 2 - Propagate to the other nodes in the cycle
            converged = False
            Niter = 0
            while not converged or Niter < 100:
                converged = True
                updatedSCT = {}

                for node in self.subgraph.nodes():
                    nodeType = self.subgraph.nodes[node]["type"]
                    predecessors = list(self.subgraph.predecessors(node))
                    candidates = set()

                    if nodeType == "item":
                        # The logic is x = rk / ck
                        candidates = [np.array(self.subgraph[p]["SCT"]) / self.subgraph[p][node].get("weight", np.nan) for p in predecessors]
                        candidates = set(np.concatenate(candidates))

                        if "originalSCT" in self.subgraph.nodes[node]:
                            candidates.update(self.subgraph.nodes[node]["originalSCT"])

                        candidates = self.cutTooLow(candidates)
                        updatedSCT[node] = candidates

                    elif nodeType == "ingredient":
                        # The logic is Xi = {xi}
                        candidates = set.union(*[self.subgraph[p]["SCT"] for p in predecessors])

                        if "originalSCT" in self.subgraph.nodes[node]:
                            candidates.update(self.subgraph.nodes[node]["originalSCT"])

                        candidates = self.cutTooLow(candidates)
                        updatedSCT[node] = candidates

                    elif nodeType == "recipe":
                        # The logic is r = sum(Xi * ci)
                        keys = list(self.predecessorsValue.keys())
                        values = [np.array(list(self.subgraph.nodes[p]["SCT"]), dtype=np.float64) for p in predecessors]
                        weights = np.array([self.subgraph[p][node].get("weight", np.nan) for p in predecessors], dtype=np.float64)

                        # Cartesian product via itertools, results in list of tuples
                        combos = np.array(list(itertools.product(*values)),
                                          dtype=np.float64)  # shape: (n_combos, n_keys)

                        # Weighted sum along axis 1 (dot product with weights)
                        candidates = np.unique(combos @ weights)

                        # This only takes into account the incoming sub edges, and not the incoming main graph edges
                        if "originalSCT" in self.subgraph.nodes[node]:
                            X,Y = np.meshgrid(candidates, self.subgraph.nodes[node]["originalSCT"])
                            candidates = X+Y
                            candidates = candidates.flatten()

                        candidates = self.cutTooLow(candidates)
                        updatedSCT[node] = candidates

                    # Check if the values are stable (convergence criteria)
                    converged = converged & candidates.issubset(self.subgraph[node]["SCT"])

                # 2nd loop to update every value at once
                # We don't keep the previous values as they are only used for the convergence to the fixed point
                for node in self.subgraph.nodes():
                    self.subgraph.nodes[node]["SCT"] = updatedSCT[node]

                Niter += 1

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
            edgeWeight[e[1]] = {**edgeWeight[e[1]], **{e[0] : e[2].get("weight", np.nan)}}
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

