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
import matplotlib.pyplot as plt


def plot_network(
    m,
    show_trucking=None,
    show_piping=None,
    show_results=None,
    save_fig=None,
    show_fig=None,
    pos={},
):
    if show_piping == None and show_trucking == None:
        show_piping = True
    if show_fig == None:
        show_fig = True

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

    if show_piping:
        draw_arcs(G, pos, piping_arcs)

    if show_trucking:
        draw_arcs(G, pos, trucking_arcs, color="red", width=1.5, arrowsize=10)

    if show_results != None:
        built_pipes = []
        built_trucking = []
        for t in m.s_T:
            for i in piping_arcs:
                if m.v_C_Piped[i, t].value:
                    built_pipes.append(i)
            for i in trucking_arcs:
                if m.v_C_Trucked[i, t].value:
                    built_trucking.append(i)

    nx.draw_networkx_labels(G, pos, {n: n for n in m.s_L}, font_size=7)

    if save_fig is not None:
        plt.savefig(save_fig)

    if show_fig:
        plt.show()


def draw_arcs(G, pos, arcs, color="blue", width=3, arrowsize=15):
    bidir_arcs_drawn = []
    for arc in arcs:
        # Check if arc is bidirectional
        reverse = (arc[1], arc[0])
        if reverse in arcs:
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
                    node_size=500,
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
                node_size=500,
            )
