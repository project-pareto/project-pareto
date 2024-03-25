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
from pareto.utilities.get_data import get_data
from pareto.utilities.decomp_utils import solve_MILP, build_MIQCP
from pareto.utilities.miqcp_decomposition import integer_cut_decomposition
from pareto.utilities.results import (
    is_feasible,
    nostdout,
)


class TestMIQCPDecomp:
    def obtain_data(self):
        """
        Building strategic model on toy case study
        """

        set_list = [
            "ProductionPads",
            "CompletionsPads",
            "SWDSites",
            "ExternalWaterSources",
            "WaterQualityComponents",
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
            "RKA",
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
            "RKT",
            "Elevation",
            "CompletionsPadOutsideSystem",
            "DesalinationTechnologies",
            "DesalinationSites",
            "BeneficialReuseCost",
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
            "ExtWaterSourcingAvailability",
            "PadOffloadingCapacity",
            "CompletionsPadStorage",
            "DisposalOperationalCost",
            "TreatmentOperationalCost",
            "ReuseOperationalCost",
            "PipelineOperationalCost",
            "ExternalSourcingCost",
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
            "ExternalWaterQuality",
            "PadWaterQuality",
            "StorageInitialWaterQuality",
            "PadStorageInitialWaterQuality",
            "DisposalOperatingCapacity",
            "TreatmentExpansionLeadTime",
            "DisposalExpansionLeadTime",
            "StorageExpansionLeadTime",
            "PipelineExpansionLeadTime_Dist",
            "PipelineExpansionLeadTime_Capac",
            "SWDDeep",
            "SWDAveragePressure",
            "SWDProxPAWell",
            "SWDProxInactiveWell",
            "SWDProxEQ",
            "SWDProxFault",
            "SWDProxHpOrLpWell",
            "SWDRiskFactors",
        ]

        # Load data from Excel input file into Python
        with resources.path(
            "pareto.case_studies",
            "strategic_toy_case_study.xlsx",
        ) as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

        return df_sets, df_parameters

    def test_decomp(self):
        df_sets, df_parameters = self.obtain_data()

        model = solve_MILP(df_sets, df_parameters)  # must precursor to building the miqcp

        model = build_MIQCP(model) 

        deco_model = integer_cut_decomposition(model, subproblem_warmstart=False, master_solver='gurobi', subproblem_solver='gams:ipopt', time_limit=600, 
                                                abs_gap=0.0, tee=False, iter_limit=10, enable_status_outputs=True)

        with nostdout():
            feasibility_status = is_feasible(deco_model)
        
        assert feasibility_status