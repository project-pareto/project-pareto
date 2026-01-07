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


import pyomo.environ as pyo
from pyomo.environ import Constraint, Var, Expression, units as pyunits, value
import re

import pandas as pd
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
)


# ---- Define the stochastic model ---- #
class StochasticPareto(pyo.ConcreteModel):
    def __init__(self, scenarios_data, pd_data, *args, **kwds):

        self.scenario_data = scenarios_data
        self.probability_data = pd_data
        super().__init__(*args, **kwds)

        self.type = "strategic"
        self.model_type = "strategic"

        self.set_scenarios = pyo.Set(initialize=list(self.scenario_data.keys()))

        @self.Block(self.set_scenarios)
        def scenario(blk, s):
            parent = blk.model()
            model = create_model(**parent.scenario_data[s])
            blk.transfer_attributes_from(model)

            optional_infrastructure_attrs = [
                "infrastructure_firstUse",
                "infrastructure_buildStart",
                "infrastructure_leadTime",
            ]
            for attr in optional_infrastructure_attrs:
                # if hasattr(model, attr):
                setattr(blk, attr, getattr(model, attr, {}))

        ref = list(self.set_scenarios)[0]
        ref_model = self.scenario[ref]

        for set_name in (
            "s_T",
            "s_R",
            "s_S",
            "s_K",
            "s_L",
            "s_O",
            "s_D",
            "s_C",
            "s_WT",
            "s_J",
            "s_I",
            "s_LLA",
            "s_P",
        ):
            if hasattr(ref_model, set_name):
                ref_set = getattr(ref_model, set_name)
                try:
                    elements = list(ref_set.data())
                except Exception:
                    elements = list(ref_set)  # fallback for non-standard Sets
                setattr(self, set_name, pyo.Set(initialize=elements))

        self.model_units = ref_model.model_units
        self.df_parameters = ref_model.df_parameters
        self.user_units = ref_model.user_units
        self.config.hydraulics = ref_model.config.hydraulics
        if hasattr(ref_model, "p_M_Flow"):
            try:
                val = pyo.value(ref_model.p_M_Flow)
            except Exception:
                val = float(ref_model.p_M_Flow)
            # create a new Param owned by the top-level model
            self.p_M_Flow = pyo.Param(initialize=val, mutable=False)

        # ---- First-stage variables ---- #
        self.v_T_Capacity = pyo.Var(
            ref_model.s_R,
            within=pyo.NonNegativeReals,
            units=ref_model.model_units["volume_time"],
            doc="Treatment capacity at a treatment site [volume/time]",
        )

        self.vb_y_Pipeline = pyo.Var(
            ref_model.s_L,
            ref_model.s_L,
            ref_model.s_D,
            within=pyo.Binary,
            initialize=0,
            doc="New pipeline installed between one location and another location with specific diameter",
        )

        self.vb_y_Storage = pyo.Var(
            ref_model.s_S,
            ref_model.s_C,
            within=pyo.Binary,
            initialize=0,
            doc="New or additional storage capacity installed at storage site with specific storage capacity",
        )

        self.vb_y_Treatment = pyo.Var(
            ref_model.s_R,
            ref_model.s_WT,
            ref_model.s_J,
            within=pyo.Binary,
            initialize=0,
            doc="New or additional treatment capacity installed at treatment site with specific treatment capacity and treatment technology",
        )

        self.vb_y_Disposal = pyo.Var(
            ref_model.s_K,
            ref_model.s_I,
            within=pyo.Binary,
            initialize=0,
            doc="New or additional disposal capacity installed at disposal site with specific injection capacity",
        )

        self.vb_y_BeneficialReuse = pyo.Var(
            ref_model.s_O,
            ref_model.s_T,
            within=pyo.Binary,
            initialize=0,
            doc="Beneficial reuse option selection",
        )

        self.shared_vars = [
            "v_T_Capacity",
            "vb_y_Pipeline",
            "vb_y_Storage",
            "vb_y_Treatment",
            "vb_y_Disposal",
            "vb_y_BeneficialReuse",
        ]

        self.nonanticipativity = pyo.Block()

        def non_anticipativity_rule(blk, s, *idx, varname=None):
            root_var = getattr(self, varname)
            scen_var = getattr(self.scenario[s], varname)
            return root_var[idx] == scen_var[idx]

        for varname in self.shared_vars:
            example_var = getattr(self.scenario[ref], varname)
            index_set = example_var.index_set()
            setattr(
                self.nonanticipativity,
                f"{varname}_con",
                pyo.Constraint(
                    self.set_scenarios,
                    index_set,
                    rule=lambda blk, s, *idx, varname=varname: non_anticipativity_rule(
                        blk, s, *idx, varname=varname
                    ),
                ),
            )
        # ---- Deactivate scenario objectives and define overall objective ---- #
        for s in self.set_scenarios:
            self.scenario[s].objective_Cost.deactivate()
            self.scenario[s].model_type = "strategic"

        self.obj = pyo.Objective(
            expr=sum(
                self.probability_data[s] * self.scenario[s].objective_Cost.expr
                for s in self.set_scenarios
            )
        )
