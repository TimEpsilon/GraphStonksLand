from pyvis.network import Network
import numpy as np

def plotGraph(G, name, fixedInOut=True):
    g = Network(width="80%", height=1000, directed=True, select_menu=True, filter_menu=True, layout=True, notebook=False)
    g.show_buttons(["physics"])
    g.options.edges.smooth.enabled = False
    G = cleanupGraph(G)
    g.from_nx(G)

    # Get source and sink nodes
    for n in g.nodes:
        nid = n["id"]
        n["size"] = G.nodes[nid].get("size", 30)
        n["color"] = G.nodes[nid].get("color", "gray")
        n["shape"] = G.nodes[nid].get("shape", "circle")
        n["font"] = {"size":10}
        n["title"] = G.nodes[nid].get("SCT", "")

    for e in g.edges:
        src, dst = e['from'], e['to']
        weight = G[src][dst].get("weight", 0)
        if isinstance(weight, list):
            weight = sum(weight)
        e['label'] = str(weight)
        e["font"] = {"size": 15, "color": "black"}
        e['arrows'] = 'to'
        e['arrowStrikethrough'] = False
        e['width'] = 1 + 2 * np.log10(weight+1)
        e['smooth'] = False

    #g.barnes_hut(spring_strength=1, spring_length=1000, overlap=1)
    g.options.layout.hierarchical.enabled = fixedInOut
    g.options.layout.hierarchical.sortMethod = "directed"
    g.options.configure.filter = ["physics"]
    g.show(f"{name}.html", notebook=False)

def cleanupGraph(G):
    G = G.copy()
    for n,data in G.nodes.data():
        if data["type"] == "cycle":
            del G.nodes[n]["subgraph"]
        G.nodes[n].update(sanitize(data))
    return G

def sanitize(obj):
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    return obj