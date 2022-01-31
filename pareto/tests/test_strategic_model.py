#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
#####################################################################################################
"""
Test strategic model
"""
# Import Pyomo libraries
import pyomo.environ as pyo

# Import IDAES solvers
from pareto.utilities.solvers import get_solver
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    Objectives,
)
from pareto.utilities.get_data import get_data
from importlib import resources
import pandas as pd
import pytest
from idaes.core.util.model_statistics import degrees_of_freedom

__author__ = "Pareto Team (Andres Calderon, M. Zamarripa)"

# -----------------------------------------------------------------------------
# Get default solver for testing
solver = get_solver("cbc")
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def build_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "ProductionTanks",
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
    ]
    parameter_list = [
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
        "SNA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "InitialPipelineCapacity",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
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
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineExpansionCost",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # create mathematical model
    strategic_model = create_model(
        df_sets, df_parameters, default={"objective": Objectives.cost}
    )
    return strategic_model


@pytest.mark.unit
def test_basic_build(build_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_strategic_model
    assert degrees_of_freedom(m) == 63944
    # Check unit config arguments
    assert len(m.config) == 2
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)


# if solver cbc exists @solver
@pytest.mark.component
def test_run_strategic_model(build_strategic_model):
    m = build_strategic_model
    solver = get_solver("cbc")
    solver.options["seconds"] = 60
    results = solver.solve(m, tee=False)
    assert degrees_of_freedom(m) == 63944


@pytest.fixture(scope="module")
def build_reduced_strategic_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "ProductionTanks",
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
    ]
    parameter_list = [
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
        "SNA",
        "PCT",
        "PKT",
        "FCT",
        "CST",
        "CCT",
        "CKT",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "InitialPipelineCapacity",
        "InitialDisposalCapacity",
        "InitialTreatmentCapacity",
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
        "DisposalExpansionCost",
        "StorageExpansionCost",
        "TreatmentExpansionCost",
        "PipelineExpansionCost",
        "PipelineExpansionDistance",
        "Hydraulics",
        "Economics",
    ]

    # note the double backslashes '\\' in that path reference
    with resources.path(
        "pareto.case_studies",
        "small_strategic_case_study.xlsx",
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

    # create mathematical model
    strategic_model = create_model(
        df_sets, df_parameters, default={"objective": Objectives.cost}
    )
    return strategic_model


@pytest.mark.unit
def test_basic_reduced_build(build_reduced_strategic_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_reduced_strategic_model
    assert degrees_of_freedom(m) == 63069
    # Check unit config arguments
    assert len(m.config) == 2
    assert m.config.objective
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_pi_Trucking, pyo.Param)
    assert isinstance(m.PipelineCapacityExpansion, pyo.Constraint)


# if solver cbc exists @solver
@pytest.mark.component
def test_run_reduced_strategic_model(build_reduced_strategic_model):
    m = build_reduced_strategic_model
    solver = get_solver("cbc")
    solver.options["seconds"] = 60 * 7
    results = solver.solve(m, tee=False)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 63069
    # solutions obtained from running the reduced generic case study
    assert pytest.approx(10353565.0, abs=1e-1) == pyo.value(m.v_Z)
