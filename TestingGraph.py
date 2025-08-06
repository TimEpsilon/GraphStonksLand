from core.GraphCreator import GraphCreator
from core.PlotGraph import plotGraph
from core.PropagationAlgorithm import Propagation

gc = GraphCreator("items.txt", "recipes.json", "equivalencyTags.json")

#plotGraph(gc.G, "full", fixedInOut=False)

prop = Propagation(gc.G)
prop.generateAtomicInputs()
prop.saveAtomicInputs()