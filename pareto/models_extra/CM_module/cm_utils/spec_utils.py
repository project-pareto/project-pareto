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
"""
Specific Utilities
This has specific utilities which helps in processing data
"""


def set_processing(d, df_parameters):
    # Treatment nodes
    d["s_NTIN"] = [NT + "_IN" for NT in d["s_NT"]]
    d["s_NTTW"] = [NT + "_TW" for NT in d["s_NT"]]
    d["s_NTCW"] = [NT + "_CW" for NT in d["s_NT"]]
    d["NT_set"] = {NT: [NT + "_IN", NT + "_TW", NT + "_CW"] for NT in d["s_NT"]}

    # additional disposal sites for the component recovery
    k = 1
    for n in d["s_NT"]:
        if df_parameters["DesalinationSites"][n] == 1:
            new_TW_disposal = "K" + str(k) + "_TW"
            d["s_ND"].append(new_TW_disposal)
            d["s_A"].append((d["NT_set"][n][1], new_TW_disposal, "Piped"))

        new_CW_disposal = "K" + str(k) + "_CW"
        d["s_ND"].append(new_CW_disposal)  # adding disposal site to list
        k += 1
        d["s_A"].append(
            (d["NT_set"][n][2], new_CW_disposal, "Piped")
        )  # adding CW->K arcs

    d["s_N"] = (
        d["s_NMS"]
        + d["s_NP"]
        + d["s_NC"]
        + d["s_NS"]
        + d["s_NW"]
        + d["s_ND"]
        + d["s_NTIN"]
        + d["s_NTTW"]
        + d["s_NTCW"]
    )

    # s_Qalpha
    d["s_Qalpha"] = {
        d["NT_set"][n][0]: [q for q in d["s_Q"] if d["s_Qalpha_int"][n, q] == 1]
        for n in d["s_NT"]
    }

    return d


def parameter_processing(d, df_parameters):
    # FCons for production pads
    for n in d["s_NP"]:
        for t in d["s_T"]:
            d["p_FCons"][n, t] = 0

    # FCons, CGen, FGen for mixers/splitters
    for node in d["s_NMS"]:
        for t in d["s_T"]:
            d["p_FGen"][(node, t)] = 0
            d["p_FCons"][(node, t)] = 0
            for q in d["s_Q"]:
                d["p_CGen"][(node, q, t)] = 0

    # Capacities
    # Disposal
    d["p_Cap"] = d["p_Cap_disposal"]  # this will capture the regular disposal

    # freshwater
    for n in d["s_NW"]:
        # checking that the freshwater sourcing is the same over time
        time_list = [value for key, value in d["p_Cap_fresh"].items() if key[0] == n]
        assert all(x == time_list[0] for x in time_list)

        # changing the freshwater sourcing to not being dependent on time
        d["p_Cap"][n] = d["p_Cap_fresh"][n, d["s_T"][0]]

    # treatment
    for n in d["s_NT"]:
        d["p_Cap"][d["NT_set"][n][0]] = d["p_Cap_treat"][n]

    del d["p_Cap_fresh"], d["p_Cap_disposal"], d["p_Cap_treat"]

    # replacing NT with NTIN or NTTW
    d["s_A_int"] = []
    for aIN, aOUT, aTP in d["s_A"]:
        # replacing NT with NTIN
        if aOUT in d["s_NT"]:
            # correcting betaArc
            beta_int_value = d["p_betaArc"][aIN, aOUT, aTP]
            del d["p_betaArc"][aIN, aOUT, aTP]
            d["p_betaArc"][aIN, d["NT_set"][aOUT][0], aTP] = beta_int_value

            # correcting Flow bounds
            for t in d["s_T"]:
                bound_int_value = d["p_Fbounds"][aIN, aOUT, aTP, t]
                del d["p_Fbounds"][aIN, aOUT, aTP, t]
                d["p_Fbounds"][aIN, d["NT_set"][aOUT][0], aTP, t] = bound_int_value

            # correcting the arc set
            d["s_A_int"].append((aIN, d["NT_set"][aOUT][0], aTP))

        # replacing NT with NTTW
        elif aIN in d["s_NT"]:
            # correcting betaArc
            beta_int_value = d["p_betaArc"][aIN, aOUT, aTP]
            del d["p_betaArc"][aIN, aOUT, aTP]
            d["p_betaArc"][(d["NT_set"][aIN][1], aOUT, aTP)] = beta_int_value

            # correcting Flow bounds
            for t in d["s_T"]:
                bound_int_value = d["p_Fbounds"][aIN, aOUT, aTP, t]
                del d["p_Fbounds"][aIN, aOUT, aTP, t]
                d["p_Fbounds"][(d["NT_set"][aIN][1], aOUT, aTP, t)] = bound_int_value

            # correcting the arc set
            d["s_A_int"].append((d["NT_set"][aIN][1], aOUT, aTP))

        else:
            d["s_A_int"].append((aIN, aOUT, aTP))

    d["s_A"] = d["s_A_int"]
    del d["s_A_int"]

    # Arcs In and Out
    d["s_Aout"] = {n: [arc for arc in d["s_A"] if n == arc[0]] for n in d["s_N"]}
    d["s_Ain"] = {n: [arc for arc in d["s_A"] if n == arc[1]] for n in d["s_N"]}

    # Functional parameters
    d["p_nodeUp"] = {a: a[0] for a in d["s_A"]}
    d["p_nodeDown"] = {a: a[1] for a in d["s_A"]}
    d["p_tp"] = {a: a[2] for a in d["s_A"]}
    d["p_treatedIN"] = {
        d["NT_set"][n][1]: d["NT_set"][n][0] for n in d["s_NT"]
    }  # treated water
    d["p_treatedIN"].update(
        {d["NT_set"][n][2]: d["NT_set"][n][0] for n in d["s_NT"]}
    )  # concentrated water

    # this will capture the component recovery disposal
    for n in d["s_ND"]:
        if n.endswith("_CW") or n.endswith("_TW"):
            TCTW = d["s_Ain"][n][0][0]
            d["p_Cap"][n] = d["p_Cap"][d["p_treatedIN"][TCTW]]
            d["p_betaD"][n] = 0

    # Trucking costs
    for aIN, aOUT, aTP in d["s_A"]:
        if aTP == "Trucked":
            if (aIN, aOUT) in list(df_parameters["TruckingTime"].keys()):
                d["p_betaArc"][aIN, aOUT, aTP] == df_parameters["TruckingHourlyCost"][
                    aIN
                ] * df_parameters["TruckingTime"][aIN, aOUT] / 110

    # Concentration bounds
    alphaW_max = max(list(d["p_alphaW"].values()))
    alpha_max = max(list(d["p_alpha"].values()))
    Cin_max = max(list(d["p_CGen"].values()))
    Cmax = Cin_max * (1 - alphaW_max + alpha_max) / (1 - alphaW_max)
    d["p_C0_seg_bounds"] = (0, Cin_max)
    assert all(Cmax >= d["p_Cmin"][n, q] for n in d["s_NTCW"] for q in d["s_Q"])

    d["p_Cbounds"] = {}
    for n in list(set(d["s_N"]) - set(d["s_ND"])):
        for q in d["s_Q"]:
            for t in d["s_T"]:
                if n in d["s_NTCW"]:
                    d["p_Cbounds"][n, q, t] = (0, Cmax)
                else:
                    d["p_Cbounds"][n, q, t] = (0, Cin_max)

    return d
