import networkx as nx
import pandas as pd


class Propagation:
    def __init__(self, graph : nx.DiGraph):
        """
        This class implements the value propagation algorithm on the given graph.
        First, the atomic node

        :param graph: the Directed Acyclic Graph on which the algorithm will be applied.
        """
        self.graph = graph
        self.inputs = self.generateAtomicInputs()

    def generateAtomicInputs(self) -> pd.DataFrame:
        """
        The algorithm needs starting values on the atomic nodes.
        This generates all of them within a pandas dataframe and writes them to a CSV file to be edited later.
        Only one value will be tolerated per entry.
        If the atomic node is a cycle, returns the subnode with the most outgoing outside edges.
        :return: A dataframe where one column is the node name,
        another is the name of the cycle if it is from a cycle node
        another the starting value.
        """
        inputs = pd.DataFrame(columns=["node", "cycle", "value"])
        for node,data in self.graph.nodes.data():
            if self.graph.in_degree(node) == 0:
                if data["type"] is "cycle":
                    df = pd.DataFrame(columns=["node","out"])
                    for subnode in self.graph.nodes[node]["subgraph"].nodes:
                        out = 0
                        for e in self.graph.nodes[node]["outEdges"]:
                            if e[0] == subnode:
                                out += 1
                        df.append([subnode, out])
                    tokeep = df.iloc[df["out"].idxmax()]
                    inputs.append([tokeep, node, 0])
                else:
                    inputs.append([node, None, 0])

        inputs.to_csv("../atomicInputs.csv")
        return inputs

    def reloadAtomicInputs(self):
        self.inputs = pd.read_csv("../atomicInputs.csv")
