import networkx as nx

from core.GraphCreator import GraphCreator
from core.PropagationAlgorithm import Propagation

gc = GraphCreator("items.txt", "recipes.json")

initset = set(nx.all_neighbors(gc.G, "cycle-48"))
for n in initset.copy():
    initset.update(nx.all_neighbors(gc.G, n))

initset.update(gc.G.predecessors("cycle-73"))
initset.update(gc.G.predecessors("cycle-176"))
initset.update(gc.G.predecessors("cycle-155"))

graph = gc.G.subgraph(initset).copy()
for n, data in graph.copy().nodes.data():
    if data["type"] != "item" and graph.in_degree(n) == 0:
        graph.remove_node(n)


prop = Propagation(graph.copy())
#prop.generateAtomicInputs()
#prop.saveAtomicInputs()
prop.loadAtomicInputs()
prop.setupForSolving()
prop.solve()
output = prop.getOutputs()
print(output.to_markdown())