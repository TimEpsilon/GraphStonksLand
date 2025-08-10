import fnmatch
import logging
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed


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

    def getOutputs(self):
        self.log("Getting outputs")
        outputs = pd.DataFrame(columns=("node","SCT"))
        for node,data in self.graph.nodes.data():
            if data["type"] == "item":
                outputs.loc[len(outputs)] = [node, data["SCT"]]
            if data["type"] == "cycle":
                for subnode, subdata in data["subgraph"].nodes.data():
                    if subdata["type"] == "item":
                        outputs.loc[len(outputs)] = [subnode, subdata["SCT"]]
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
                    inputs.loc[len(inputs)] = [node, 0, tokeep, None, self.partitionMap[node]]
                else:
                    inputs.loc[len(inputs)] = [node, 0, None, None, self.partitionMap[node]]
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

    def matchInputValue(self, pattern, value, overwrite=False):
        toSet = set(fnmatch.filter(self.inputs["node"], pattern))
        if not overwrite:
            toSet = toSet.difference(set(self.inputs[self.inputs["value"] != 0]["node"]))
        self.log(f"{pattern} matches up with {toSet}")
        self.inputs.loc[self.inputs["node"].isin(toSet), "value"] = value

    def _filterAtomicInputs(self):
        BANNED_KEYWORDS = {
            "*spawn_egg",
            "*command_block*",
            "*creative*",
            "minecraft:bedrock",
            "minecraft:jigsaw",
            "minecraft:barrier",
            "minecraft:light",
            "minecraft:structure*",
            "minecraft:petrified_oak_slab",
            "*debug_*",
            "minecraft:knowledge_book",
            "minecraft:reinforced_deepslate",
            "minecraft:budding_amethyst",
            "minecraft:chorus_plant",
            "minecraft:dirt_path",
            "minecraft:end_portal_frame",
            "minecraft:farmland",
            "*:infested_*",
            "minecraft:*spawner",
            "create:*minecart_contraption",
            'amendments:dye_bottle',
            'create:andesite_encased_*',
            'create:chromatic_compound',
            'create:*_backtank_placeable',
            'create:elevator_contact',
            'create:handheld_worldshaper',
            'create:incomplete_*',
            'create:refined_radiance*',
            'create:schematic',
            'create:shadow_steel*',
            'create:shopping_list',
            'create:unprocessed_obsidian_sheet',
            'exposure:broken_interplanar_projector',
            'exposure:chromatic_sheet',
            'exposure:signed_album',
            'exposure:stacked_photographs',
            'ftblibrary:icon_item',
            'lootr:*',
            'minecraft:air',
            'minecraft:chipped_anvil',
            'minecraft:damaged_anvil',
            'modonomicon:*',
            'moonlight:*',
            'randomium:any_item',
            'sereneseasons:ss_icon',
            'sophisticatedbackpacks:*infinity_upgrade',
            'sophisticatedstorage:inaccessible_slot',
            'sophisticatedstorage:*infinity_upgrade',
            'supplementaries:raked_gravel',
            'create:cardboard_package_*'
        }
        self.log(f"Banned keywords are : {BANNED_KEYWORDS}")
        toDrop = []
        for ban in BANNED_KEYWORDS:
            toBan = fnmatch.filter(self.inputs["node"], ban)
            self.log(f"Keyword {ban} matches with {toBan}", level=logging.DEBUG)
            for i,row in self.inputs.iterrows():
                if row["node"] in toBan:
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

