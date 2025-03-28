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
This file parses data retreived by the get_data() function to align with the qcp model.
"""

from pareto.utilities.get_data import get_data
from pareto.models_extra.CM_module.cm_utils.spec_utils import (
    set_processing,
    parameter_processing,
)
from pareto.utilities.process_data import (
    get_valid_piping_arc_list,
    get_valid_trucking_arc_list,
)


def _tolist(d):
    print(d)
    d = d.values.squeeze().tolist()
    if type(d) is list:
        return d
    return [d]


def data_parser(df_sets, df_parameters):
    d = {}

    # ---------------SETS---------------------
    # nodes
    d["s_NMS"] = df_sets["NetworkNodes"].tolist()
    d["s_NP"] = df_sets["ProductionPads"].tolist()  # production pads
    d["s_NC"] = df_sets["CompletionsPads"].tolist()  # completion pads
    d["s_NS"] = df_sets["StorageSites"].tolist()  # storage
    d["s_ND"] = df_sets["SWDSites"].tolist()  # disposal
    d["s_NW"] = df_sets["ExternalWaterSources"].tolist()  # freshwater
    d["s_NT"] = df_sets["TreatmentSites"].tolist()  # treatment
    # NTIN, NTTW, NTCW created in set processing

    # ARCS
    d["s_A"] = []

    arcs = [
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "SNA",
        "FCA",
        "RCA",
        "RSA",
        "SCA",
        "RNA",
        "PCT",
        "FCT",
        "PKT",
        "CKT",
        "CCT",
        "CST",
    ]

    # Creating the unified arc set and appending 'Piped' or 'Trucked' to the arc tuple
    for arc_name in arcs:
        if arc_name in list(df_parameters.keys()):
            for aIN, aOUT in df_parameters[arc_name]:
                assert df_parameters[arc_name][(aIN, aOUT)] == 1
                if arc_name[2] == "A":
                    d["s_A"].append((aIN, aOUT, "Piped"))
                elif arc_name[2] == "T":
                    d["s_A"].append((aIN, aOUT, "Trucked"))
                else:
                    "ERROR: Arc is neither defined as a trucking or piping arc"

    # s_Ain and s_Aout created in set processing

    # QUALITY
    d["s_Q"] = df_sets["WaterQualityComponents"].tolist()

    d["s_Qalpha_int"] = df_parameters["ComponentTreatment"]
    # going to be made in post processing

    # TIME PERIODS
    d["s_T"] = df_sets["TimePeriods"]

    d = set_processing(d, df_parameters)

    # -----------------PARAMETERS-----------------------
    # FGen
    d["p_FGen"] = {
        **df_parameters["PadRates"],
        **df_parameters["FlowbackRates"],
    }  # Production pads and completions

    # CGen
    d["p_CGen"] = {
        (n, q, t): df_parameters["PadWaterQuality"][(n, q)]
        for (n, q) in df_parameters["PadWaterQuality"].keys()
        for t in d["s_T"]
    }

    # FCons
    d["p_FCons"] = df_parameters["CompletionsDemand"]

    # FCons of production pads will be handles in parameter_processing()

    # Mixers splitters FCons, FGen, CGen will be handled in parameter_processing()

    # Inventory Parameters
    d["p_I0"] = df_parameters["InitialStorageLevel"]
    d["p_C0"] = df_parameters["StorageInitialWaterQuality"]

    # Treatment Efficiencies
    d["p_alphaW"] = {
        d["NT_set"][n][0]: df_parameters["TreatmentEfficiency"][n] for n in d["s_NT"]
    }
    d["p_alpha"] = {
        (d["NT_set"][n][0], q): df_parameters["RemovalEfficiency"][n, q]
        for n in d["s_NT"]
        for q in d["s_Q"]
    }

    # Treatment Capacities
    d["p_Cap_fresh"] = df_parameters["ExtWaterSourcingAvailability"]
    d["p_Cap_disposal"] = df_parameters[
        "InitialDisposalCapacity"
    ]  # adding capacity for component recovery in parameter_processing
    d["p_Cap_treat"] = df_parameters["InitialTreatmentCapacity"]
    # Combining the three into one p_Cap will be done in the parameter processing

    # Cmin
    d["p_Cmin"] = {
        (d["NT_set"][n][2], q): df_parameters["MinResidualQuality"][n, q]
        for n in d["s_NT"]
        for q in d["s_Q"]
    }
    d["p_Fmin"] = {
        d["NT_set"][n][0]: df_parameters["MinTreatmentFlow"][n] for n in d["s_NT"]
    }

    # TimeDiscretization
    d["p_dt"] = 7

    # Operating costs
    d["p_betaArc"] = {}
    for aIN, aOUT, aTP in d["s_A"]:
        if aOUT.endswith("_CW") or aOUT.endswith("_TW"):
            d["p_betaArc"][
                aIN, aOUT, aTP
            ] = 0  # setting all arcs to K_CW as have no cost
        elif aTP == "Piped":
            d["p_betaArc"][aIN, aOUT, aTP] = df_parameters["PipelineOperationalCost"][
                (aIN, aOUT)
            ]
        else:  # trucking case
            d["p_betaArc"][aIN, aOUT, aTP] = 0.01
    d["p_betaD"] = df_parameters["DisposalOperationalCost"]
    d["p_betaW"] = df_parameters["ExternalSourcingCost"]
    d["p_betaT"] = {
        d["NT_set"][n][0]: df_parameters["TreatmentOperationalCost"][n]
        for n in d["s_NT"]
    }
    d["p_betaS"] = df_parameters["StorageCost"]
    d["p_betaR"] = {
        d["NT_set"][n][1]: df_parameters["BeneficialReuseCost"][n] for n in d["s_NT"]
    }

    d["p_gammaT"] = {
        (d["NT_set"][n][2], q): df_parameters["ComponentPrice"][n, q]
        for n in d["s_NT"]
        for q in d["s_Q"]
    }
    d["p_gammaS"] = df_parameters["StorageWithdrawalRevenue"]
    d["p_gammaR"] = {
        d["NT_set"][n][1]: df_parameters["BeneficialReuseCredit"][n] for n in d["s_NT"]
    }

    # Bounds
    d["p_Ibounds"] = {
        (n, t): (0, df_parameters["InitialStorageCapacity"][n])
        for n in d["s_NS"]
        for t in d["s_T"]
    }

    d["p_Fbounds"] = {}
    for aIN, aOUT, aTP in d["s_A"]:
        for t in d["s_T"]:
            # Trucked flow = Max Piped flow if volume is being trucked
            if aTP == "Trucked":
                d["p_Fbounds"][aIN, aOUT, aTP, t] = (
                    0,
                    max(list(df_parameters["InitialPipelineCapacity"].values())),
                )

            # Flow from treatment unit to pseudo disposal is max piped flow
            elif aOUT.endswith("_TW") or aOUT.endswith("_CW"):
                d["p_Fbounds"][aIN, aOUT, aTP, t] = (
                    0,
                    max(list(df_parameters["InitialPipelineCapacity"].values())),
                )

            # For all the other cases - store the pipeline capacity as is
            else:
                d["p_Fbounds"][aIN, aOUT, aTP, t] = (
                    0,
                    df_parameters["InitialPipelineCapacity"][aIN, aOUT],
                )
                # Treatment flows within the network are handled in parameter processing

    d = parameter_processing(d, df_parameters)

    return d
