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
Test operational model
"""
# Import Pyomo libraries
import pyomo.environ as pyo

# Import IDAES solvers
from pareto.utilities.solvers import get_solver
from pareto.operational_water_management.operational_produced_water_optimization_model import (
    create_model,
    ProdTank,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues
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
def build_operational_model():
    # This emulates what the pyomo command-line tools does
    # Tabs in the input Excel spreadsheet
    set_list = [
        "ProductionPads",
        "CompletionsPads",
        "ProductionTanks",
        "FreshwaterSources",
        "StorageSites",
        "SWDSites",
        "TreatmentSites",
        "ReuseOptions",
        "NetworkNodes",
    ]
    parameter_list = [
        "RCA",
        "FCA",
        "PCT",
        "FCT",
        "CCT",
        "PKT",
        "PRT",
        "CKT",
        "CRT",
        "PAL",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "ProductionTankCapacity",
        "InitialDisposalCapacity",
        "CompletionsPadStorage",
        "TreatmentCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "DriveTimes",
        "DisposalPipeCapEx",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PadStorageCost",
        "PipingOperationalCost",
        "TruckingHourlyCost",
        "FreshSourcingCost",
        "ProductionRates",
        "TreatmentEfficiency",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
    ]

    with resources.path(
        "pareto.case_studies", "EXAMPLE_INPUT_DATA_FILE_generic_operational_model.xlsx"
    ) as fpath:
        [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)
    df_parameters["MinTruckFlow"] = 75
    df_parameters["MaxTruckFlow"] = 37000
    # create mathematical model
    operational_model = create_model(
        df_sets,
        df_parameters,
        default={
            "has_pipeline_constraints": True,
            "production_tanks": ProdTank.equalized,
        },
    )
    return operational_model


@pytest.mark.unit  # Keith
def test_basic_build(build_operational_model):
    """Make a model and make sure it doesn't throw exception"""
    m = build_operational_model
    assert degrees_of_freedom(m) == 133
    # Check unit config arguments
    assert len(m.config) == 3
    assert m.config.production_tanks
    assert isinstance(m.s_T, pyo.Set)
    assert isinstance(m.v_F_Piped, pyo.Var)
    assert isinstance(m.p_PPA, pyo.Param)
    assert isinstance(m.ProductionTankBalance, pyo.Constraint)


@pytest.mark.component
def test_run_operational_model(build_operational_model):
    m = build_operational_model
    results = solver.solve(m, tee=True)
    assert results.solver.termination_condition == pyo.TerminationCondition.optimal
    assert results.solver.status == pyo.SolverStatus.ok
    assert degrees_of_freedom(m) == 133
    # solutions obtained from running the generic case study
    assert pytest.approx(327997.5, abs=1e-3) == pyo.value(m.v_Objective)
    assert pytest.approx(993.0, abs=1e-3) == pyo.value(
        m.v_F_Trucked["PP04", "CP01", "T1"]
    )

    # To DO:
    # 1.- add mass balance checks
    # 2.- create test marks (unit, component, etc.) (work with Ludovico/Keith)
    # 3.- skip test if solver doesnt exist
