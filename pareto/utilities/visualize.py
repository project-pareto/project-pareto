#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2024 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

import networkx as nx
import pyomo.environ as pyo
import matplotlib.pyplot as plt


def plot_network(m):
    G = nx.Graph()
    for i in m.s_L:
        G.add_node(i)

    piping_acrs = []
    for i in m.s_LLA:
        piping_acrs.append(i)
    trucking_arcs = []
    for i in m.s_LLT:
        trucking_arcs.append(i)
    G.add_edges_from(piping_acrs)
    # G.add_edges_from(trucking_arcs)

    labels = {node: node for node in m.s_L}
    pos = nx.kamada_kawai_layout(G)

    fig = plt.figure()
    for node in m.s_PP:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=800,
            node_color="lightgreen",
            edgecolors="black",
        )
    for node in m.s_CP:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=800,
            node_color="red",
            edgecolors="black",
        )
    for node in m.s_F:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=800,
            node_color="lightgreen",
            edgecolors="black",
        )
    for node in m.s_K:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="^",
            node_size=1200,
            node_color="lightgreen",
            edgecolors="black",
        )
    for node in m.s_S:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=800,
            node_color="lightgreen",
            edgecolors="black",
        )
    for node in m.s_R:
        if m.p_chi_DesalinationSites[node]:
            nx.draw_networkx_nodes(
                G,
                pos,
                [node],
                node_shape="p",
                node_size=800,
                node_color="lightgreen",
                edgecolors="black",
            )
        else:
            nx.draw_networkx_nodes(
                G,
                pos,
                [node],
                node_shape="s",
                node_size=800,
                node_color="lightgreen",
                edgecolors="black",
            )
    for node in m.s_O:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="*",
            node_size=1200,
            node_color="lightgreen",
            edgecolors="black",
        )
    for node in m.s_N:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=800,
            node_color="lightgreen",
            edgecolors="black",
        )

    # nx.draw_networkx_edges(G,
    #                         pos,
    #                         trucking_arcs,
    #                         edge_color='blue',
    #                         alpha=0.7)

    nx.draw_networkx_edges(G, pos, piping_acrs, edge_color="black", style=":", width=1)

    nx.draw_networkx_labels(G, pos, labels, font_size=7)
    plt.show()
