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
        self.originalGraph = self._generateGraph()
        self.G = self.originalGraph.copy()
        self._collapseCycles()

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

    def _generateGraph(self) -> nx.DiGraph:
        graph = nx.DiGraph()

        # Item Node
        graph.add_nodes_from(
            self.itemList,
            type="item",
            SCT=set(),
            hasComputed=False,
            color='#8ceef5',
            size=30,
            shape="dot",)

        for r in self.recipeDict.keys():
            # Recipe Node
            graph.add_node(
                f"{self.recipeDict[r]['type']}-{r}",
                type="recipe",
                SCT=set(),
                hasComputed=False,
                color='green',
                size=15,
                shape="diamond")

            for ingr in self.recipeDict[r]["input"].keys():

                # Ingredient Node
                graph.add_node(
                    ingr,
                    type="ingredient",
                    SCT=set(),
                    hasComputed=False,
                    color='orange',
                    size=5,
                    shape="square")

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
        cycles = [c for c in nx.strongly_connected_components(self.originalGraph) if len(c) > 1]
        results = {}
        self.nodeToCycle = {}
        for i, c in enumerate(cycles):
            results[f"cycle-{i}"] = c
            for n in c:
                self.nodeToCycle[n] = f"cycle-{i}"
        return results

    def _collapseCycles(self):
        toRemove = set()
        cycleIn = set()
        cycleOut = set()
        for cycleid,cycle in self._getCycles().items():
            # We set the corresponding cycle subgraph as a node attribute
            self.G.add_node(
                cycleid,
                type="cycle",
                SCT=None,
                hasComputed=False,
                subgraph=self.G.subgraph(cycle).copy(),
                shape="triangleDown", color="black", size=50)

            inEdges = list()
            outEdges = list()

            for n in cycle:
                for p in self.originalGraph.predecessors(n):
                    if p not in cycle:
                        inEdges.append((p, n, self.originalGraph[p][n]))
                        cycleIn.add((p, cycleid))
                        if p in self.nodeToCycle.keys():
                            cycleIn.add((self.nodeToCycle[p], cycleid))
                for s in self.originalGraph.successors(n):
                    if s not in cycle:
                        outEdges.append((s, n, self.originalGraph[n][s]))
                        cycleOut.add((cycleid, s))
                        if s in self.nodeToCycle.keys():
                            cycleOut.add((cycleid, self.nodeToCycle[s]))

            self.G.nodes[cycleid]["inEdges"] = inEdges
            self.G.nodes[cycleid]["outEdges"] = outEdges


            toRemove.update(cycle)

        self.G.add_edges_from(cycleIn)
        self.G.add_edges_from(cycleOut)
        self.G.remove_nodes_from(toRemove)


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
