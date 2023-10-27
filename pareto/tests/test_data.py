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
from importlib import resources
import pytest

from pareto.utilities.get_data import get_data


class Sets:
    operational = [
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
    strategic = [
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


class Parameters:
    operational = [
        "Units",
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
        "TankFlowbackRates",
        "FlowbackRates",
        "ProductionTankCapacity",
        "DisposalCapacity",
        "CompletionsPadStorage",
        "TreatmentCapacity",
        "FreshwaterSourcingAvailability",
        "PadOffloadingCapacity",
        "TruckingTime",
        "DisposalOperationalCost",
        "TreatmentOperationalCost",
        "ReuseOperationalCost",
        "PadStorageCost",
        "PipelineOperationalCost",
        "TruckingHourlyCost",
        "FreshSourcingCost",
        "ProductionRates",
        "TreatmentEfficiency",
        "PadWaterQuality",
        "StorageInitialWaterQuality",
    ]
    strategic = [
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
        "Elevation",
        "CompletionsPadOutsideSystem",
        "DesalinationTechnologies",
        "DesalinationSites",
        "BeneficialReuseCredit",
        "TruckingTime",
        "CompletionsDemand",
        "PadRates",
        "FlowbackRates",
        "WellPressure",
        "NodeCapacities",
        "InitialPipelineCapacity",
        "InitialPipelineDiameters",
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


@pytest.mark.parametrize(
    "file_name",
    [
        "operational_generic_case_study.xlsx",
        "strategic_toy_case_study.xlsx",
        "strategic_treatment_demo.xlsx",
        "strategic_small_case_study.xlsx",
        "strategic_permian_demo.xlsx",
    ],
)
def test_case_studies(file_name: str):
    if file_name.startswith("operational"):
        sets, parameters = Sets.operational, Parameters.operational
    elif file_name.startswith("strategic"):
        sets, parameters = Sets.strategic, Parameters.strategic

    with resources.path("pareto.case_studies", file_name) as fpath:
        data = get_data(fpath, sets, parameters)
    assert data is not None
