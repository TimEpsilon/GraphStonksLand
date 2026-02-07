from pyvis.network import Network
import numpy as np

def plotGraph(G, name, ylim=1000, fixedInOut=True):
    g = Network(width=1900, height=1000, directed=True, select_menu=True, filter_menu=True, layout=True)
    g.options.edges.smooth.enabled = False
    G = cleanupGraph(G)
    g.from_nx(G)


    top_y = -ylim  # Top line y-coordinate
    bottom_y = ylim  # Bottom line y-coordinate

    # Get source and sink nodes
    sources = [n for n in G.nodes if G.in_degree(n) == 0]
    sinks = [n for n in G.nodes if G.out_degree(n) == 0]

    i = 0
    j = 0
    d = 200
    for n in g.nodes:
        nid = n["id"]
        n["size"] = G.nodes[nid].get("size", 30)
        n["color"] = G.nodes[nid].get("color", "gray")
        n["shape"] = G.nodes[nid].get("shape", "circle")
        n["font"] = {"size":10}
        n["title"] = G.nodes[nid].get("SCT", "")

        #if (nid in sources) & fixedInOut:
        #    n["x"] = d/2 * i + d/2 if i%2 == 1 else - d/2 * i
        #    n["y"] = bottom_y
        #    n["fixed"] = {"x": True, "y": True}
        #    n["physics"] = False
        #    n["color"] = "red"
        #    i += 1
        #elif (nid in sinks) & fixedInOut:
        #    n["x"] = d/2 * j + d/2 if j%2 == 1 else - d/2 * j
        #    n["y"] = top_y
        #    n["fixed"] = {"x": True, "y": True}
        #    n["physics"] = False
        #    n["color"] = "red"
        #    j += 1
#
#
        #elif fixedInOut:
        #    n["y"] = np.random.normal(0, ylim/5)
        #    n["physics"] = True
        #    n["fixed"] = {"x": False, "y": False}


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

    g.show_buttons()

    if fixedInOut:
        options = """{
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "sortMethod": "directed"
                }
            },
            "interaction": {
                "hover": true
            },
            "manipulation": {
                "enabled": true
            },
            "physics": {
                "hierarchicalRepulsion": {
                    "centralGravity": 0,
                    "avoidOverlap": null
                },
                "minVelocity": 0.75,
                "solver": "hierarchicalRepulsion",
                "timestep": 0.35
            }
        }"""
        #g.set_options(options)
    else:
        g.set_options("""
                {
                  "physics": {
                    "forceAtlas2Based": {
                      "gravitationalConstant": -50,
                      "springLength": 200,
                      "springConstant": 0.05
                    },
                    "maxVelocity": 20,
                    "solver": "forceAtlas2Based",
                    "timestep": 0.35,
                    "stabilization": {
                      "iterations": 150
                    }
                  },
                    "interaction": {
                    "hover": true
                    },
                }
                """)


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