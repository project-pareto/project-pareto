#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2025 by the software owners:
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
import matplotlib.pyplot as plt


def plot_network(
    m,
    show_piping=True,
    show_trucking=False,
    show_results=False,
    save_fig=None,
    show_fig=True,
    pos={},
):
    G = nx.MultiDiGraph()
    for i in m.s_L:
        G.add_node(i)

    piping_arcs = []
    for i in m.s_LLA:
        piping_arcs.append(i)

    trucking_arcs = []
    for i in m.s_LLT:
        trucking_arcs.append(i)

    if show_piping:
        G.add_edges_from(piping_arcs)

    if show_trucking:
        G.add_edges_from(trucking_arcs)

    if len(pos) == 0:
        pos = nx.circular_layout(G)

    plt.figure()

    for node in m.s_PP:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=500,
            node_color="lightgreen",
            edgecolors="black",
        )

    for node in m.s_CP:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="o",
            node_size=500,
            node_color="lightgreen",
            edgecolors="black",
        )

    for node in m.s_F:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="P",
            node_size=600,
            node_color="lightblue",
            edgecolors="black",
        )

    for node in m.s_K:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="X",
            node_size=600,
            node_color="lightgreen",
            edgecolors="black",
        )

    for node in m.s_S:
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape="H",
            node_size=400,
            node_color="lightgreen",
            edgecolors="black",
        )

    for node in m.s_R:
        if m.p_chi_DesalinationSites[node]:
            shape = "s"
            size = 300
        else:
            shape = "p"
            size = 400
        nx.draw_networkx_nodes(
            G,
            pos,
            [node],
            node_shape=shape,
            node_size=size,
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
            node_shape=",",
            node_size=0,
        )

    proxies = []
    labels = []
    from matplotlib.lines import Line2D

    if show_piping:
        draw_arcs(
            G,
            pos,
            piping_arcs,
            piping_arcs,
            color="blue",
            width=6,
            arrowsize=20,
            node_size=500,
        )
        proxies.append(Line2D([0, 1], [0, 1], color="blue"))
        labels.append("Pipeline arcs")

    if show_trucking:
        draw_arcs(
            G,
            pos,
            trucking_arcs,
            trucking_arcs,
            color="red",
            width=3,
            arrowsize=10,
            node_size=800,
        )
        proxies.append(Line2D([0, 1], [0, 1], color="red"))
        labels.append("Trucking arcs")

    if show_results:
        built_pipes = []
        for i in piping_arcs:
            for d in m.s_D:
                if m.vb_y_Pipeline[i, d].value > 0 and m.p_delta_Pipeline[d].value > 0:
                    built_pipes.append(i)
                    break
        draw_arcs(
            G,
            pos,
            built_pipes,
            piping_arcs,
            color="yellow",
            width=1,
            arrowsize=8,
            node_size=1200,
        )
        proxies.append(Line2D([0, 1], [0, 1], color="yellow"))
        labels.append("Pipelines built/expanded")

    nx.draw_networkx_labels(G, pos, {n: n for n in m.s_L}, font_size=7)

    plt.legend(proxies, labels)

    if save_fig is not None:
        plt.savefig(save_fig)

    if show_fig:
        plt.show()


def draw_arcs(
    G, pos, arcs_to_draw, all_arcs, color="blue", width=6, arrowsize=20, node_size=500
):
    bidir_arcs_drawn = []
    for arc in arcs_to_draw:
        # Check if arc is bidirectional
        reverse = (arc[1], arc[0])
        if reverse in all_arcs:
            # Arc is bidirectional
            if reverse in bidir_arcs_drawn:
                # Arc has already been drawn (in "reverse" direction) - skip
                continue
            else:
                # Arc has not yet been drawn - draw it without arrowheads
                # and add it to the list of drawn bidirectional arcs
                nx.draw_networkx_edges(
                    G,
                    pos,
                    [arc],
                    edge_color=color,
                    style="-",
                    width=width,
                    arrows=True,
                    arrowstyle="-",
                    node_size=node_size,
                )
                bidir_arcs_drawn.append(arc)
        else:
            # Arc is not bidirectional - draw it with arrowheads
            nx.draw_networkx_edges(
                G,
                pos,
                [arc],
                edge_color=color,
                style="-",
                width=width,
                arrowsize=arrowsize,
                node_size=node_size,
            )
