import logging
import os
import pathlib

import networkx as nx
import pandas as pd

from core.solver.CycleSolver import CycleSolver
from core.solver.IngredientSolver import IngredientSolver
from core.solver.ItemSolver import ItemSolver
from core.solver.RecipeSolver import RecipeSolver

ATOMICPATH = os.path.join(pathlib.Path(__file__).parent.resolve(), "../atomicInputs.csv")

class Propagation:

    def __init__(self, graph : nx.DiGraph):
        """
        This class implements the value propagation algorithm on the given graph.

        :param graph: the Directed Acyclic Graph on which the algorithm will be applied.
        """
        self.logger = self._logInit()
        self.graph = graph
        self.partitionMap = self._generatePartitionMap()
        self._generateNodeToCycle()

        self.inputs = None

    def setupForSolving(self):
        """
        Applies the starting SCT values to the atomic nodes based on the input dataframe.
        Then, setups the solvers for every other node.
        """
        # Init values
        for _,row in self.inputs.iterrows():
            if pd.isna(row["cycle"]):
                self.graph.nodes[row["node"]]["SCT"] = {row["value"]}
                self.graph.nodes[row["node"]]["hasComputed"] = True
            else:
                if row["representative"] is None:
                    self.log(f"{row['node']} has no representative", level=logging.ERROR)
                    raise ValueError
                self.graph.nodes[row["node"]]["subgraph"].nodes[row["representative"]] = {row["value"]}
                self.graph.nodes[row["node"]]["subgraph"].nodes[row["hasComputed"]] = True
        self.log("Starting values initialized")

    def solve(self):
        self.log("Starting node computing")

        # Topological Ordering
        orderedNodes = list(nx.topological_sort(self.graph))

        # Init solvers
        def assignSolver(node):
            solvers = {
                "item": ItemSolver,
                "ingredient": IngredientSolver,
                "recipe": RecipeSolver,
                "cycle": CycleSolver
            }
            return solvers[self.graph.nodes[node]["type"]]

        daskGraph = {}
        for node in orderedNodes:
            Solver = assignSolver(node)
            solver = Solver(node, self.graph)
            solver.solve()

    def generateAtomicInputs(self):
        """
        The algorithm needs starting values on the atomic nodes.
        This generates all of them within a pandas dataframe and writes them to a CSV file to be edited later.
        Only one value will be tolerated per entry.
        If the atomic node is a cycle, returns the subnode with the most outgoing outside edges.
        """
        inputs = pd.DataFrame(columns=["node", "cycle", "representative", "partition", "value"])
        self.log("Getting atomic inputs")
        for node,data in self.graph.nodes.data():
            if self.graph.in_degree(node) == 0 and data["type"] in ["cycle","item"]:
                if data["type"] == "cycle":
                    self.log(f"Cycle detected: {node} with {len(self.graph.nodes[node]['subgraph'].nodes())} nodes",
                             level=logging.WARNING)
                    tokeep = set()
                    for subnode in self.graph.nodes[node]["subgraph"].nodes:
                        # Only keep item subnode (what is the value of a recipe / ingredient?)
                        if self.graph.nodes[node]["subgraph"].nodes[subnode]["type"] != "item":
                            continue
                        tokeep.add(subnode)
                    inputs.loc[len(inputs)] = [node, tokeep, None, self.partitionMap[node], 0]
                else:
                    inputs.loc[len(inputs)] = [node, None, None, self.partitionMap[node], 0]
        self.inputs = inputs
        self._filterAtomicInputs()
        self.log(f"Full input table size is {len(self.inputs)}")

    def saveAtomicInputs(self):
        self.inputs.to_csv(ATOMICPATH, index=False)
        self.log(f"Inputs saved to atomicInputs.csv")

    def loadAtomicInputs(self):
        if os.path.exists(ATOMICPATH):
            self.log("Found an existing input file")
            self.inputs = pd.read_csv(ATOMICPATH)
        else:
            self.log("No input file found")

    def _filterAtomicInputs(self):
        BANNED_KEYWORDS = {
            "spawn_egg",
            "command_block",
            "creative",
            "bedrock"
        }
        self.log(f"Banned keywords are : {BANNED_KEYWORDS}")
        toDrop = []
        for ban in BANNED_KEYWORDS:
            for i,row in self.inputs.iterrows():
                if ban in row["node"]:
                    toDrop.append(i)
        self.inputs.drop(toDrop, inplace=True)
        self.log(f"Dropped {len(toDrop)} nodes")

    def _generatePartitionMap(self):
        partitionMap = {}
        for i,part in enumerate(nx.weakly_connected_components(self.graph)):
            for node in part:
                partitionMap[node] = f"part-{i:03}"

        return partitionMap

    def _generateNodeToCycle(self):
        self.nodeToCycle = {}
        for node in self.graph.nodes:
            if self.graph.nodes[node]["type"] != "cycle":
                continue
            for n in self.graph.nodes[node]["subgraph"].nodes():
                self.nodeToCycle[n] = node

    def _logInit(self):
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(f'%(levelname)s - %(name)s - %(funcName)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger

    def log(self, message, level=logging.INFO):
        self.logger.log(level, f'{message}', stacklevel=2)

