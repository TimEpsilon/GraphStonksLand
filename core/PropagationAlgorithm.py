import fnmatch
import json
import logging
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed


import networkx as nx
import numpy as np
import pandas as pd

from core.solver.CycleSolver import CycleSolver
from core.solver.IngredientSolver import IngredientSolver
from core.solver.ItemSolver import ItemSolver
from core.solver.NodeSolver import NodeSolver
from core.solver.RecipeSolver import RecipeSolver

ATOMICPATH = os.path.join(pathlib.Path(__file__).parent.resolve(), "../config/atomicInputs.csv")

class Propagation:

    def __init__(self, graph : nx.DiGraph, equivalencyPath : str):
        """
        This class implements the value propagation algorithm on the given graph.

        :param graph: the Directed Acyclic Graph on which the algorithm will be applied.
        :param equivalencyPath: the path of the file containing the equivalency tags.
        """
        self.logger = self._logInit()
        self.equivalencyPath = equivalencyPath

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
                self.log(f"{row['node']} has value {row['value']}", level=logging.DEBUG)
            else:
                if row["representative"] is None:
                    self.log(f"{row['node']} has no representative", level=logging.ERROR)
                    continue
                subgr = self.graph.nodes[row["node"]]["subgraph"]
                subgr.nodes[row["representative"]]["SCT"] = {row["value"]}
                subgr.nodes[row["representative"]]["originalSCT"] = {row["value"]}
                subgr.nodes[row["representative"]]["hasComputed"] = True

        self.log("Starting values initialized")

        # Init solvers
        def assignSolver(node):
            solvers = {
                "item": ItemSolver,
                "ingredient": IngredientSolver,
                "recipe": RecipeSolver,
                "cycle": CycleSolver
            }
            return solvers[self.graph.nodes[node]["type"]]

        self.taskDict = {}
        for node in self.graph.nodes:
            Solver = assignSolver(node)
            solver = Solver(node, self.graph)
            self.taskDict[node] = solver.solve

        self.log("Task Graph initialized")


    def solve(self):
        self.log("Starting node computing")

        for layer in nx.topological_generations(self.graph):
            layerTask = [self.taskDict[n] for n in layer]
            self.log(f"Current layer is {layer}")

            N = min(os.cpu_count()-1, len(layerTask))
            with ThreadPoolExecutor(max_workers=N) as executor:
                futures = [executor.submit(task) for task in layerTask]
                for future in as_completed(futures):
                    future.result()

    def saveOutputs(self):
        self.log("Getting outputs")
        outputs = pd.DataFrame(columns=("node","SCT"))
        for node,data in self.graph.nodes.data():
            if data["type"] == "item":
                sct = np.array(list(data["SCT"])).astype(float)
                sct = sct[sct!=0]
                out = sct.min() if len(sct) > 0 else 0
                out = format(out, '.3f')
                outputs.loc[len(outputs)] = [node, out]

            if data["type"] == "cycle":
                for subnode, subdata in data["subgraph"].nodes.data():
                    if subdata["type"] == "item":
                        out = np.array(list(subdata["SCT"])).min() if len(subdata["SCT"]) > 0 else 0
                        out = format(out, '.3f')
                        outputs.loc[len(outputs)] = [subnode, out]
        outputs.to_csv("output.csv", index=False)

        self.log("Saving output JSON")
        # To Json for easier managing back in Java
        outputs.set_index("node", inplace=True)
        outputs = outputs.T.to_dict("list")
        outputs = dict(sorted(outputs.items()))

        equivalencies = json.load(open(self.equivalencyPath))
        js = {}
        for key in outputs:
            if "#" in key:
                for subkey in equivalencies[key]:
                    js[subkey] = {"SCT" : float(outputs[key][0])}
            else:
                js[key] = {"SCT" : float(outputs[key][0])}

        with open("sct.json", "w") as f:
            json.dump({"values" : js}, f, indent=4)

        return outputs


    def generateAtomicInputs(self):
        """
        The algorithm needs starting values on the atomic nodes.
        This generates all of them within a pandas dataframe and writes them to a CSV file to be edited later.
        Only one value will be tolerated per entry.
        If the atomic node is a cycle, returns the subnode with the most outgoing outside edges.
        """
        inputs = pd.DataFrame(columns=["node", "value", "cycle", "representative", "partition"])
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
                    inputs.loc[len(inputs)] = [node, 0.0, tokeep, None, self.partitionMap[node]]
                else:
                    inputs.loc[len(inputs)] = [node, 0.0, None, None, self.partitionMap[node]]
        self.inputs = inputs
        self.log(f"Full input table size is {len(self.inputs)}")

    def saveAtomicInputs(self):
        self.inputs.to_csv(ATOMICPATH, index=False)
        self.log(f"Inputs saved to atomicInputs.csv")

    def crossmatchAtomicInputs(self, path):
        """
        Using an already existing table of values, sets some values in the input table beforehand
        :param path: the path to the crossmatching table
        """
        crossmatch = pd.read_csv(path)
        crossmatch["value"] = crossmatch["value"].astype(float)
        crossmatch.set_index("node", inplace=True)

        counter = 0
        for i,row in self.inputs.copy().iterrows():
            # Basic node
            if row["node"] in crossmatch.index:
                self.inputs.at[i, "value"] = crossmatch.loc[row["node"],"value"]
                counter += 1
                continue

            # Cycle node
            if not pd.isna(row["cycle"]):
                for subnode in row["cycle"]:
                    if subnode in crossmatch.index:
                        self.inputs.at[i, "representative"] = subnode
                        self.inputs.at[i, "value"] = crossmatch.loc[subnode,"value"]
                        counter += 1
                        continue

        self.log(f"Cross matched {counter} atoms")

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
            logger.setLevel(logging.INFO)
        return logger

    def log(self, message, level=logging.INFO):
        self.logger.log(level, f'{message}', stacklevel=2)

