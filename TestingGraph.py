from core.GraphCreator import GraphCreator
from core.PlotGraph import plotGraph
from core.PropagationAlgorithm import Propagation
import networkx as nx
import pickle

# Uncomment to generate full graph from scratch
#gc = GraphCreator("config/input/items.txt", "config/input/recipes.json", "config/input/tags.json", "config/equivalencyTags.json", "config/CustomRecipe.json", "config/bannedKeywords.json")
#with open("fullGraph.txt", "w", encoding="utf-8") as f:
#    nx.write_network_text(gc.originalGraph, f)
#
#with open('fullGraph.gpickle', 'wb') as f:
#    pickle.dump(gc, f, pickle.HIGHEST_PROTOCOL)
#
#plotGraph(gc.G, "full", fixedInOut=False)

# Uncommment if graph has been saved beforehand
with open('fullGraph.gpickle', 'rb') as f:
    gc = pickle.load(f)

prop = Propagation(gc.G, "config/equivalencyTags.json")
prop.generateAtomicInputs()
prop.crossmatchAtomicInputs("config/mainItemReference.csv")
prop.saveAtomicInputs()

prop.setupForSolving()

prop.solve()
prop.saveOutputs()

