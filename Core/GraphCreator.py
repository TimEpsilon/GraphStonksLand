from collections import defaultdict
from typing import Hashable

import numpy as np
import json
import networkx as nx


class GraphCreator:

    def __init__(self, itemPath : str, recipePath : str):
        """
        Generates the basic structure of the recipe graph, a Directed Acyclic Graph.
        There are 4 node types :
            - Item, a minecraft item
            - Recipe, a recipe
            - Ingredient, the wrapper of item inputs for a recipe
            - Cycle, the collapsed SCC made in order to make the graph acyclic
        Most edges hold a "weight" attribute, representing the amount consumed / produced by a recipe.

        :param itemPath: path to the item list txt
        :param recipePath: path to the recipe json file
        """
        self.itemPath = itemPath
        self.recipePath = recipePath

        # Item list
        self.itemList, self.modList = self._getItems()

        # Recipe dict
        self.recipeDict = self._getRecipes()

        # Graph
        # We keep a copy of the original graph just in case
        self.Originalgraph = self._generateGraph()
        self.G = self.Originalgraph.copy()



    def _getItems(self) -> tuple[list, list]:
        items = open(self.itemPath).readlines()
        items = [s.replace("\n", "") for s in items]
        return items, list(np.unique([s.split(":")[0] for s in items]))

    def _getRecipes(self) -> dict:
        recipes = json.load(open(self.recipePath))
        for r in recipes.keys():
            for ingr in list(recipes[r]["input"].keys()):
                # Renames the ingredients
                new = ingr.replace("net.minecraft.world.item.crafting.", "")
                recipes[r]["input"][new] = recipes[r]["input"].pop(ingr)

                # Removes empty ingredients (like for shaped recipes)
                if new == "Ingredient@1":
                    recipes[r]["input"].pop(new)
        return recipes

    def _generateGraph(self) -> nx.DiGraph[Hashable]:
        graph = nx.DiGraph()

        # Item Node
        graph.add_nodes_from(self.itemList, type="item", SCT=np.nan, color='#8ceef5', size=30, shape="dot")

        for r in self.recipeDict.keys():
            # Recipe Node
            graph.add_node(f"{self.recipeDict[r]['type']}-{r}", type="craft", SCT=np.nan, color='green', size=15,
                           shape="diamond")

            for ingr in self.recipeDict[r]["input"].keys():

                # Ingredient Node
                graph.add_node(ingr, type="ingredient", SCT=np.nan, color='orange', size=5, shape="square")

                inputs = list(self.recipeDict[r]["input"][ingr].keys())
                output = list(self.recipeDict[r]["output"])
                if len(output) == 0:
                    print(f"No output for {r}")
                    continue

                inAmount = list(self.recipeDict[r]["input"][ingr].values())
                outAmount = self.recipeDict[r]["output"][output[0]]

                # Item -> Ingredient (not necessarily unique)
                graph.add_edges_from([(i, ingr) for i in inputs])

                # Ingredient -> Recipe (amount is the same for every item in an ingredient)
                graph.add_edge(ingr, f"{self.recipeDict[r]['type']}-{r}", weight=inAmount[0])

                # Recipe -> Item
                graph.add_edge(f"{self.recipeDict[r]['type']}-{r}", output[0], weight=outAmount)
        return graph

    def _getCycles(self) -> dict[str, set]:
        cycles = [c for c in nx.strongly_connected_components(self.Originalgraph) if len(c) > 1]
        return {f"cycle-{i}":c for i,c in enumerate(cycles)}

    def _collapseCycles(self):
        for cycleid,cycle in self._getCycles().items():
            # We set the corresponding cycle subgraph as a node attribute
            self.G.add_node(cycleid, type="cycle", shape="triangleDown", color="black", size=50, subgraph=self.G.subgraph(cycle).copy())

            # List of incoming edges, represented as a tuple (incoming outside node, cycleid, attributes dict)
            # The attributes are : the ones already in the edge + to_subnode,
            # encoding the original node to which this edge pointed to
            in_edges = []
            for n in cycle:
                for p in self.G.predecessors(n):
                    if p not in cycle:
                        in_edges.append((p, cycleid, {**self.G[p][n], "to_subnode":n}))

            # List of outgoing edges, represented as a tuple (cycleid, outside node, attributes dict)
            # The attributes are : the ones already in the edge + from_subnode,
            # encoding the original node to which this edge pointed from
            out_edges = []
            for n in cycle:
                for s in self.G.successors(n):
                    if s not in cycle:
                        out_edges.append((cycleid, s, {**self.G[n][s], "from_subnode":n}))

            in_edges = GraphCreator._combineEdges(in_edges)
            out_edges = GraphCreator._combineEdges(out_edges)

            self.G.add_edges_from(in_edges)
            self.G.add_edges_from(out_edges)

            self.G.remove_nodes_from(cycle)

    @staticmethod
    def _combineEdges(edge_list : list[tuple[str,str,dict]]) -> list[tuple[str,str,dict]]:
        """
        Combines identical edges into one but every attribute is appended to a list.
        This means that if 2 edges go to the cycle node but used to point to 2 different subnodes,
        their attributes values are stored in a list on the same key,
        the first edge being accessed by an index 0 and the 2nd edge by an index 1
        :param edge_list: list of 3 tuples representing the edges
        :return: The same list but every identical edge is combined
        """
        grouped = defaultdict(list)

        # Group property dicts by (from, to)
        for from_node, to_node, props in edge_list:
            grouped[(from_node, to_node)].append(props)

        # Compress the properties into lists
        compressed = []
        for (from_node, to_node), props_list in grouped.items():
            merged_props = defaultdict(list)
            for prop in props_list:
                for key, value in prop.items():
                    if isinstance(value, list):
                        merged_props[key] = merged_props[key] + value
                    else:
                        merged_props[key].append(value)
            compressed.append((from_node, to_node, dict(merged_props)))

        return compressed


    # --------------------------------------------------------------------
    #                            Public Methods
    # --------------------------------------------------------------------

    def getAtoms(self, filterForInput=True) -> set[str]:
        """
        An atom is a node from which every edge is an exiting edge (in degree = 0).

        This is filtered to be either an item node or a cycle node

        :param filterForInput: whether to only keep the item and cycle nodes

        :return: The set of all Atoms in the graph
        """
        atoms = []

        for n, data in list(self.G.nodes(data=True)):
            if (data["type"] not in ["item", "cycle"]) & filterForInput:
                continue

            if self.G.in_degree(n) == 0:
                atoms.append(n)

        return set(atoms)

    def getDeadend(self) -> set[str]:
        """
        A Deadend is a node from which every edge is an incoming edge (out degree = 0).

        :return: The set of all Deadends in the graph
        """
        deadend = []

        for n, data in list(self.G.nodes(data=True)):
            if self.G.in_degree(n) == 0:
                deadend.append(n)

        return set(deadend)

