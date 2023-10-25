#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
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
Test utilities
"""

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    RemovalEfficiencyMethod,
)
from pareto.utilities.get_data import get_data
from importlib import resources

from pyomo.environ import value

# Modules to test:
from pareto.utilities.bounding_functions import VariableBounds
from pareto.utilities.model_modifications import free_variables
from pareto.utilities.model_modifications import deactivate_slacks


############################
def fetch_strategic_model(config_dict):
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "SWDSites",
        "FreshwaterSources",
        "StorageSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
        "PipelineDiameters",
        "StorageCapacities",
        "InjectionCapacities",
        "TreatmentCapacities",
        "TreatmentTechnologies",
    ]
    parameter_list = [
        "Units",
        "PNA",
        "CNA",
        "CCA",
        "NNA",
        "NCA",
        "NKA",
        "NRA",
        "NSA",
        "FCA",
        "RCA",
        "RNA",
        "RSA",
        "SCA",
        "SNA",
        "ROA",
        "SOA",
        "NOA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "RST",
        "ROT",
        "SOT",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
        "ReuseMinimum",
        "ReuseCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "CompletionsPadStorage",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PipelineOperationalCost",
        "FreshSourcingCost",
        "TruckingHourlyCost",
        "PipelineDiameterValues",
        "DisposalCapacityIncrements",
        "InitialStorageCapacity",
        "StorageCapacityIncrements",
        "TreatmentCapacityIncrements",
        "TreatmentEfficiency",
        "RemovalEfficiency",
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineCapexDistanceBased",
        "PipelineCapexCapacityBased",
        "PipelineCapacityIncrements",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
        "PadStorageInitialWaterQuality",
        "DisposalOperatingCapacity",
        "TreatmentExpansionLeadTime",
        "DisposalExpansionLeadTime",
        "StorageExpansionLeadTime",
        "PipelineExpansionLeadTime_Dist",
        "PipelineExpansionLeadTime_Capac",
    ]

    # user needs to provide the path to the case study data file
    # for example: 'C:\\user\\Documents\\myfile.xlsx'
    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "strategic_toy_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # create mathematical model
    """Valid values of config arguments for the default parameter in the create_model() call
    objective: [Objectives.cost, Objectives.reuse]
    pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
    pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
    node_capacity: [True, False]
    water_quality: [WaterQuality.false, WaterQuality.post_process, WaterQuality.discrete]
    removal_efficiency_method: [RemovalEfficiencyMethod.concentration_based, RemovalEfficiencyMethod.load_based]
    """

    strategic_model = create_model(
        df_sets,
        df_parameters,
        default=config_dict,
    )

    options = {
        "deactivate_slacks": True,
        "scale_model": False,
        "scaling_factor": 1000,
        "running_time": 100,
        "gap": 0,
    }

    results = solve_model(model=strategic_model, options=options)

    return strategic_model


############################
def test_utilities_wout_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.false,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_01
    if __name__ == "__main__":
        print(
            "After VariableBounds: Not all v_F_Piped upper bounds are None: ", check_01
        )

    # Free variables with exception list and test that variables have NOT been freed
    free_variables(model, exception_list=["v_F_Piped"])
    check_02 = not all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_02
    if __name__ == "__main__":
        print(
            "After free_variables with v_F_Piped in exception_list: Not all v_F_Piped upper bounds are None: ",
            check_02,
        )

    # Free variables and test that variables have been freed
    free_variables(model)
    check_03 = all(
        model.v_F_Piped[ll, t].upper is None for ll in model.s_LLA for t in model.s_T
    )
    assert check_03
    if __name__ == "__main__":
        print(
            "After free_variables with no exception_list: All v_F_Piped upper bounds are None: ",
            check_03,
        )

    # Deactivate slacks and test that slacks have been set to zero
    deactivate_slacks(model)
    check_04 = all(
        [
            all(
                value(model.v_S_FracDemand[p, t]) == 0
                for p in model.s_CP
                for t in model.s_T
            ),
            all(
                value(model.v_S_Production[p, t]) == 0
                for p in model.s_PP
                for t in model.s_T
            ),
            all(
                value(model.v_S_Flowback[p, t]) == 0
                for p in model.s_CP
                for t in model.s_T
            ),
            all(
                value(model.v_S_PipelineCapacity[l1, l2]) == 0
                for l1 in model.s_L
                for l2 in model.s_L
            ),
            all(value(model.v_S_StorageCapacity[s]) == 0 for s in model.s_S),
            all(value(model.v_S_DisposalCapacity[k]) == 0 for k in model.s_K),
            all(value(model.v_S_TreatmentCapacity[r]) == 0 for r in model.s_R),
            all(value(model.v_S_BeneficialReuseCapacity[o]) == 0 for o in model.s_O),
        ]
    )
    assert check_04
    if __name__ == "__main__":
        print("After deactivate_slacks: All slack variables are 0: ", check_04)


############################
def test_utilities_w_post_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.post_process,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_01
    if __name__ == "__main__":
        print("After VariableBounds: Not all v_Q upper bounds are None: ", check_01)

    # Free variables with exception list and test that variables have NOT been freed
    free_variables(model, exception_list=["quality.v_Q"])
    check_02 = not all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_02
    if __name__ == "__main__":
        print(
            "After free_variables with v_Q in exception_list: Not all v_Q upper bounds are None: ",
            check_02,
        )

    # Free variables and test that variables have been freed
    free_variables(model)
    check_03 = all(
        model.quality.v_Q[n, q, t].upper is None
        for n in model.quality.s_WQL
        for q in model.s_QC
        for t in model.s_T
    )
    assert check_03
    if __name__ == "__main__":
        print(
            "After free_variables with no exception_list: All v_Q upper bounds are None: ",
            check_03,
        )


############################
def test_utilities_w_discrete_quality():
    config_dict = {
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.discrete,
        "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
    }
    model = fetch_strategic_model(config_dict)

    # Add bounds and check to confirm that bounds have been added
    model = VariableBounds(model)
    check_01 = not all(
        model.v_F_DiscretePiped[key, t, w, q].upper is None
        for key in model.s_NonPLP
        for t in model.s_T
        for w in model.s_QC
        for q in model.s_Q
    )
    assert check_01
    if __name__ == "__main__":
        print(
            "After VariableBounds: Not all v_F_DiscretePiped upper bounds are None: ",
            check_01,
        )


############################
if __name__ == "__main__":
    test_utilities_wout_quality()
    test_utilities_w_post_quality()
    test_utilities_w_discrete_quality()
