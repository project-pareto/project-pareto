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
from idaes.core.util.model_statistics import degrees_of_freedom
import matplotlib.pyplot as plt


def make_mee_mvr_model(N_evap=1, inputs_variables=False):
    """
    Contains a model for mee-mvr desalination unit with
    heat integration and single stage compression. The model is built based
    on the paper by Onishi et. al.
    Citation: V. C. Onishi, et.al. “Shale gas flowback water desalination: Single vs multiple effect
    evaporation with vapor recompression cycle and thermal integration,” Desalination,
    vol. 404, pp. 230–248, Feb. 2017

    Inputs
    -------
        N_evap - Number of evaporator stages
        inputs_variables - Boolean sepcifiying if feed flow rate and salinity
                           are variables or not

    Returns
    --------
    mee-mvr unit model
    """

    # Create model
    m = pyo.ConcreteModel()

    # Parameter definitions
    if inputs_variables:
        # Flowrate of feed stream
        m.flow_feed = pyo.Var(
            initialize=20, units=pyo.units.kg / pyo.units.s, bounds=(0, 100)
        )

        # Salt in the feed stream
        m.salt_feed = pyo.Var(
            initialize=80, units=pyo.units.g / pyo.units.kg, bounds=(70, 210)
        )
    else:
        # Flowrate of feed stream
        m.flow_feed = pyo.Param(
            initialize=10, units=pyo.units.kg / pyo.units.s, mutable=True
        )

        # Salt in the feed stream
        m.salt_feed = pyo.Param(
            initialize=100, units=pyo.units.g / pyo.units.kg, mutable=True
        )

    # Temperature of the feed stream
    m.feed_temperature = pyo.Param(initialize=25, units=pyo.units.C, mutable=True)

    # TDS in brine concentration
    m.salt_outlet_spec = pyo.Param(
        initialize=250, units=pyo.units.g / pyo.units.kg, mutable=True
    )

    # Water recovery fraction
    m.water_recovery_fraction = pyo.Var(initialize=0.3, bounds=(1e-20, 1))

    # Temperature constraint parameters
    m.DT_min = pyo.Param(initialize=2, units=pyo.units.C)
    m.DT_min_1 = pyo.Param(initialize=2, units=pyo.units.C)
    m.DT_min_2 = pyo.Param(initialize=2, units=pyo.units.C)
    m.DT_min_stage = pyo.Param(initialize=2, units=pyo.units.C)

    # Antoine coefficients
    m.a = pyo.Param(initialize=12.98437)
    m.b = pyo.Param(initialize=-2001.77468)
    m.c = pyo.Param(initialize=139.61335)

    # Specific heat capacity of vapor
    m.cp_vapor = pyo.Param(initialize=1.873)

    # Minimum pressure delta between evaporators
    m.DP_min = pyo.Param(initialize=0.1)

    # Overall heat transfer coefficient (Known parameter)
    m.overall_heat_transfer_coef = pyo.Param(initialize=100)

    # Heat capacity ratio
    m.gamma = pyo.Param(initialize=1.33)

    # Maximum compression ratio
    m.CR_max = pyo.Param(initialize=4, mutable=True)

    # Efficiency of compressors (isentropic efficiency)
    m.eta = pyo.Param(initialize=0.75)

    # Costing parameters
    m.r = pyo.Param(initialize=0.1)
    m.years = pyo.Param(initialize=10)
    m.cepci_2022 = pyo.Param(initialize=813)
    m.cepci_2003 = pyo.Param(initialize=402)

    # Set definitions
    # Set of Evaporator effects
    m.i = pyo.Set(initialize=range(N_evap))

    # Set of all evaporators except the first
    m.i_except_1 = pyo.Set(initialize=range(1, N_evap))

    # Variable definitions
    # ====================================================================
    # All flow variables
    # Flow of brine evaporator
    m.flow_brine = pyo.Var(
        m.i,
        bounds=(1e-20, 100),
        initialize=[pyo.value(m.flow_feed) * pyo.value(1 - m.water_recovery_fraction)]
        * N_evap,
        units=pyo.units.kg / pyo.units.s,
    )

    # Flow of vapor evaporator
    m.flow_vapor_evaporator = pyo.Var(
        m.i,
        bounds=(1e-20, 100),
        initialize=[pyo.value(m.flow_feed - m.flow_brine[m.i.last()])] * N_evap,
        units=pyo.units.kg / pyo.units.s,
    )

    # Flow of super heated vapor
    m.flow_super_heated_vapor = pyo.Var(
        bounds=(1e-20, 100),
        initialize=pyo.value(m.flow_vapor_evaporator[m.i.last()]),
        units=pyo.units.kg / pyo.units.s,
    )

    # Flow of treated water
    m.flow_treated_water = pyo.Var(
        bounds=(1e-20, 100),
        initialize=pyo.value(m.flow_vapor_evaporator[m.i.last()]),
        units=pyo.units.kg / pyo.units.s,
    )

    m.flow_brine_last = pyo.Var(
        bounds=(1e-20, 100), initialize=1, units=pyo.units.kg / pyo.units.s
    )
    # ======================================================================
    # All concentration variables
    # Concentration of salt/TDS
    m.salt = pyo.Var(
        m.i,
        bounds=(1e-20, 300),
        initialize=[100] * N_evap,
        units=pyo.units.g / pyo.units.kg,
    )

    # Salt mass fraction (XS in paper)
    m.salt_mass_frac = pyo.Var(m.i, bounds=(1e-20, 1), initialize=0.5)

    # Salt mass fraction in the feed
    m.salt_mass_frac_feed = pyo.Var(
        bounds=(1e-10, 1), initialize=pyo.value(m.salt_feed) / 1000
    )

    # ======================================================================
    # All pressure variables
    # Vapor pressure in evaporator effects
    m.evaporator_vapor_pressure = pyo.Var(
        m.i, bounds=(1, 200), initialize=[70] * N_evap, units=pyo.units.kPa
    )
    m.super_heated_vapor_pressure = pyo.Var(
        bounds=(1, 200), initialize=60.540, units=pyo.units.kPa
    )

    m.saturated_vapor_pressure = pyo.Var(
        m.i, bounds=(1, 300), initialize=101.00, units=pyo.units.kPa
    )

    # =======================================================================
    # All temperature variables
    # Actual temperature of feed entering the evaporator after preheating
    m.evaporator_feed_temperature = pyo.Var(
        bounds=(1, 200), initialize=25, units=pyo.units.C
    )

    m.evaporator_ideal_temperature = pyo.Var(
        m.i, bounds=(1, 200), initialize=25, units=pyo.units.C
    )
    m.evaporator_brine_temperature = pyo.Var(
        m.i, bounds=(1, 200), initialize=35, units=pyo.units.C
    )
    m.evaporator_condensate_temperature = pyo.Var(
        m.i, bounds=(1, 200), initialize=30, units=pyo.units.C
    )
    m.super_heated_vapor_temperature = pyo.Var(
        bounds=(1, 300), initialize=50, units=pyo.units.C
    )

    m.evaporator_saturated_vapor_temperature = pyo.Var(
        m.i, bounds=(1, 200), initialize=30, units=pyo.units.C
    )

    m.fresh_water_temperature = pyo.Var(
        bounds=(1, 200), initialize=25, units=pyo.units.C
    )

    m.LMTD = pyo.Var(m.i, initialize=1, units=pyo.units.C)

    m.theta_1 = pyo.Var(m.i, bounds=(1, 200), initialize=1, units=pyo.units.C)

    m.theta_2 = pyo.Var(m.i, bounds=(1, 200), initialize=1, units=pyo.units.C)

    m.preheater_LMTD = pyo.Var(initialize=1, units=pyo.units.C)

    m.preheater_theta_1 = pyo.Var(bounds=(1, 200), initialize=1, units=pyo.units.C)

    m.preheater_theta_2 = pyo.Var(bounds=(1, 200), initialize=1, units=pyo.units.C)

    m.isentropic_temperature = pyo.Var(
        bounds=(1e-20, 200), initialize=25, units=pyo.units.C
    )
    m.mixer_temperature = pyo.Var(bounds=(1e-20, 200), initialize=25, units=pyo.units.C)

    # =======================================================================
    # All enthalpy variables
    # Specific Enthalpies of brine and vapor in the evaporator
    m.evaporator_brine_enthalpy = pyo.Var(m.i, domain=pyo.Reals, initialize=400)

    m.evaporator_vapor_enthalpy = pyo.Var(m.i, domain=pyo.Reals, initialize=400)
    # Defined only for first evaporator
    m.evaporator_condensate_vapor_enthalpy = pyo.Var(domain=pyo.Reals, initialize=100)

    m.evaporator_condensate_enthalpy = pyo.Var(domain=pyo.Reals, initialize=100)

    m.super_heated_vapor_enthalpy = pyo.Var(domain=pyo.Reals, initialize=100)
    # Enthalpy of the feed stream
    m.enthalpy_feed = pyo.Var(domain=pyo.Reals, initialize=200)

    # =======================================================================
    # All area variables
    m.evaporator_total_area = pyo.Var(
        bounds=(14, 1500), initialize=60, units=pyo.units.m**2
    )
    m.each_evaporator_area = pyo.Var(
        m.i, bounds=(14, 372), initialize=30, units=pyo.units.m**2
    )

    # =======================================================================
    # Other Variables
    # Evaporator heat flow - Q
    m.evaporator_heat_flow = pyo.Var(m.i, bounds=(1e-20, None), initialize=1)
    # Boiling point elevation
    m.bpe = pyo.Var(m.i, bounds=(1e-20, 200), initialize=[15] * N_evap)

    # Latent heat
    m.latent_heat = pyo.Var(m.i_except_1, bounds=(1e-20, None), initialize=1)

    # Heat transfer coefficient
    m.heat_transfer_coef = pyo.Var(m.i, bounds=(1e-20, None), initialize=1)

    # Specific heat capacity of condensate
    m.cp_condensate = pyo.Var(bounds=(1e-20, None), initialize=1)

    # Specific heat capacity of feed
    m.cp_feed = pyo.Var(bounds=(1e-20, None), initialize=1)

    # Preheater area
    m.preheater_area = pyo.Var(bounds=(1, 372), initialize=20)

    # preheater heat transfer coefficient
    m.preheater_heat_transfer_coef = pyo.Var(bounds=(1e-20, None), initialize=0.1)

    # Each compressor work
    m.compressor_work = pyo.Var(bounds=(1e-20, 30000), initialize=1)

    m.total_compressor_work = pyo.Var(bounds=(1e-20, 30000), initialize=1)
    # =======================================================================
    # Variables for costing
    m.compressor_capacity = pyo.Var(bounds=(1e-20, 30000), initialize=150)

    m.annual_fac = pyo.Var(bounds=(1e-20, None), initialize=1)

    m.cepci_ratio = pyo.Var(bounds=(1e-20, None), initialize=1)

    m.compressor_capex = pyo.Var(bounds=(1e-20, None), initialize=1)

    m.evaporator_capex = pyo.Var(m.i, bounds=(1e-20, None), initialize=1)

    m.preheater_capex = pyo.Var(bounds=(1e-20, None), initialize=1)

    m.CAPEX = pyo.Var(bounds=(1e-20, None), initialize=1)

    m.OPEX = pyo.Var(bounds=(1e-20, None), initialize=1)

    # =======================================================================
    "Model Constraints"

    # =======================================================================
    # Evaporator Constraints
    # Flow balance across the evaporator (Equation 1, 3)
    def _evaporator_flow_balance(m, i):
        if i != m.i.last():
            return (
                m.flow_brine[i + 1] - m.flow_brine[i] - m.flow_vapor_evaporator[i] == 0
            )
        else:
            return m.flow_feed - m.flow_brine[i] - m.flow_vapor_evaporator[i] == 0

    m.evaporator_flow_balance = pyo.Constraint(m.i, rule=_evaporator_flow_balance)

    # Linking treated water variable with vapor flow from last evaporator
    def _treated_water_linking_cons(m):
        return m.flow_treated_water == sum(m.flow_vapor_evaporator[i] for i in m.i)

    m.treated_water_linking_cons = pyo.Constraint(rule=_treated_water_linking_cons)

    # Linking brine water from the last evaporator to the flow_brine_last var
    def _brine_water_linking_cons(m):
        return m.flow_brine_last == m.flow_brine[m.i.last()]

    m.brine_water_linking_cons = pyo.Constraint(rule=_brine_water_linking_cons)

    # Solid balance in the evaporator (Equation 3, 4)
    def _evaporator_salt_balance(m, i):
        if i != m.i.last():
            return (
                m.flow_brine[i + 1] * m.salt[i + 1] - m.flow_brine[i] * m.salt[i] == 0
            )
        else:
            return m.flow_feed * m.salt_feed - m.flow_brine[i] * m.salt[i] == 0

    m.evaporator_salt_balance = pyo.Constraint(m.i, rule=_evaporator_salt_balance)

    # Estimating the ideal temperature in an evaporator (Equation 5)
    def _ideal_evaporator_temperature(m, i):
        return pyo.log(m.evaporator_vapor_pressure[i]) == m.a + m.b / (
            m.evaporator_ideal_temperature[i] + m.c
        )

    m.evaporator_ideal_temp_con = pyo.Constraint(
        m.i, rule=_ideal_evaporator_temperature
    )

    # Boiling point elevation (Equation 6)
    def _bpe_con(m, i):
        return (
            m.bpe[i]
            == 0.1581
            + 2.769 * m.salt_mass_frac[i]
            - 0.002676 * m.evaporator_ideal_temperature[i]
            + 41.78 * m.salt_mass_frac[i] ** 2
            + 0.134 * m.salt_mass_frac[i] * m.evaporator_ideal_temperature[i]
        )

    m.bpe_con = pyo.Constraint(m.i, rule=_bpe_con)

    # Relating mass fraction of salt to brine salinity (Equation 7)
    def _match_mass_frac_to_salinity(m, i):
        return m.salt_mass_frac[i] - 0.001 * m.salt[i] == 0

    m.match_mass_frac_to_salinity = pyo.Constraint(
        m.i, rule=_match_mass_frac_to_salinity
    )

    # Relating salt mass frac of feed to salinity of feed
    def _match_mass_frac_to_salinity_feed(m):
        return m.salt_mass_frac_feed == 0.001 * m.salt_feed

    m.match_mass_frac_to_salinity_feed = pyo.Constraint(
        rule=_match_mass_frac_to_salinity_feed
    )

    # Relate brine temperature to ideal temperature and bpe (Equation 8)
    def _brine_temp_con(m, i):
        return (
            m.evaporator_brine_temperature[i]
            - m.evaporator_ideal_temperature[i]
            - m.bpe[i]
            == 0
        )

    m.brine_temp_con = pyo.Constraint(m.i, rule=_brine_temp_con)

    # Energy balance in the evaporator (Equations 9, 10)
    def _evaporator_energy_balance(m, i):
        if i != m.i.last():
            return (
                1
                / 1000
                * (
                    m.evaporator_heat_flow[i]
                    + m.flow_brine[i + 1] * m.evaporator_brine_enthalpy[i + 1]
                    - m.flow_brine[i] * m.evaporator_brine_enthalpy[i]
                    - m.flow_vapor_evaporator[i] * m.evaporator_vapor_enthalpy[i]
                )
                == 0
            )
        else:
            return (
                1
                / 1000
                * (
                    m.evaporator_heat_flow[i]
                    + m.flow_feed * m.enthalpy_feed
                    - m.flow_brine[i] * m.evaporator_brine_enthalpy[i]
                    - m.flow_vapor_evaporator[i] * m.evaporator_vapor_enthalpy[i]
                )
                == 0
            )

    m.evaporator_energy_balance = pyo.Constraint(m.i, rule=_evaporator_energy_balance)

    # Estimating the enthalpies (Equations 11, 12, 13)
    def _enthalpy_vapor_estimate(m, i):
        return 1 / 1000 * (m.evaporator_vapor_enthalpy[i]) == 1 / 1000 * (
            -13470 + 1.84 * m.evaporator_brine_temperature[i]
        )

    m.enthalpy_vapor_estimate = pyo.Constraint(m.i, rule=_enthalpy_vapor_estimate)

    def _enthalpy_brine_estimate(m, i):
        return 1 / 1000 * (m.evaporator_brine_enthalpy[i]) == 1 / 1000 * (
            -15940
            + 8787 * m.salt_mass_frac[i]
            + 3.557 * m.evaporator_brine_temperature[i]
        )

    m.enthalpy_brine_estimate = pyo.Constraint(m.i, rule=_enthalpy_brine_estimate)

    def _enthalpy_feed_estimate(m):
        return 1 / 1000 * m.enthalpy_feed == 1 / 1000 * (
            -15940
            + 8787 * m.salt_mass_frac_feed
            + 3.557 * m.evaporator_feed_temperature
        )

    m._enthalpy_feed_estimate = pyo.Constraint(rule=_enthalpy_feed_estimate)

    # ==============================================================================
    # Estimating the condensate temperature in the first evaporator from the outlet compressor pressure
    def _condensate_temperature_estimate(m, i):
        if i == m.i.first():
            return (
                pyo.log(m.super_heated_vapor_pressure)
                - m.a
                - m.b / (m.evaporator_condensate_temperature[i] + m.c)
                == 0
            )
        else:
            return (
                pyo.log(m.evaporator_vapor_pressure[i - 1])
                - m.a
                - m.b / (m.evaporator_condensate_temperature[i] + m.c)
                == 0
            )

    m.condensate_temperature_estimate = pyo.Constraint(
        m.i, rule=_condensate_temperature_estimate
    )

    # Estimating enthalpy of the condensate vapor and condensate
    def _enthalpy_condensate_vapor_estimate(m):
        return 1 / 1000 * (m.evaporator_condensate_vapor_enthalpy) == 1 / 1000 * (
            -13470 + 1.84 * m.evaporator_condensate_temperature[m.i.first()]
        )

    m.enthalpy_condensate_vapor_estimate = pyo.Constraint(
        rule=_enthalpy_condensate_vapor_estimate
    )

    def _enthalpy_condensate_estimate(m):
        return 1 / 1000 * (m.evaporator_condensate_enthalpy) == 1 / 1000 * (
            -15940 + 3.557 * m.evaporator_condensate_temperature[m.i.first()]
        )

    m.enthalpy_condensate_estimate = pyo.Constraint(rule=_enthalpy_condensate_estimate)

    # Flow balance for super heated vapor (Equation 15)
    m.flow_balance_super_heated_vapor = pyo.Constraint(
        expr=m.flow_super_heated_vapor == m.flow_vapor_evaporator[m.i.last()]
    )

    # Heat requirements in evaporators
    def _evaporator_heat_balance(m, i):
        if i == m.i.first():
            # Heat requirements in the 1st evaporator (Equation 14)
            return 1 / 1000 * (m.evaporator_heat_flow[m.i.first()]) == 1 / 1000 * (
                m.flow_super_heated_vapor
                * m.cp_vapor
                * (
                    m.super_heated_vapor_temperature
                    - m.evaporator_condensate_temperature[m.i.first()]
                )
                + m.flow_super_heated_vapor
                * (
                    m.evaporator_condensate_vapor_enthalpy
                    - m.evaporator_condensate_enthalpy
                )
            )

        else:
            # Heat requirements in other evaporators (Equation 16)
            return 1 / 1000 * (m.evaporator_heat_flow[i]) == 1 / 1000 * (
                m.flow_vapor_evaporator[i - 1] * m.latent_heat[i]
            )

    m.evaporator_heat_balance = pyo.Constraint(m.i, rule=_evaporator_heat_balance)

    # Calculating latent heat from temperature (Equation 17)
    def _latent_heat_estimation(m, i):
        if i == m.i.first():
            return pyo.Constraint.Skip
        return m.latent_heat[
            i
        ] == 2502.5 - 2.3648 * m.evaporator_saturated_vapor_temperature[i] + 1.840 * (
            m.evaporator_saturated_vapor_temperature[i - 1]
            - m.evaporator_saturated_vapor_temperature[i]
        )

    m.latent_heat_estimation = pyo.Constraint(m.i, rule=_latent_heat_estimation)

    # Calculating saturated vapor temperature from saturated vapor pressure
    def _saturated_vapor_temp_estimate(m, i):
        if N_evap == 1:
            return pyo.Constraint.Skip
        return (
            pyo.log(m.saturated_vapor_pressure[i])
            - m.a
            - m.b / (m.evaporator_saturated_vapor_temperature[i] + m.c)
            == 0
        )

    m.saturated_vapor_temp_estimate = pyo.Constraint(
        m.i, rule=_saturated_vapor_temp_estimate
    )

    # Pressure and temperature feasiility constraints (Equation 18)
    def _pressure_gradient_constraint(m, i):
        if i != m.i.last():
            return (
                m.evaporator_vapor_pressure[i]
                >= m.evaporator_vapor_pressure[i + 1] + m.DP_min
            )
        else:
            return pyo.Constraint.Skip

    m.pressure_gradient_constraint = pyo.Constraint(
        m.i, rule=_pressure_gradient_constraint
    )

    # Relating evaporator vapor pressure with saturated vapor pressure (Equation 19)
    def _relating_pressure_in_evaporator(m, i):
        if i != m.i.first():
            return m.saturated_vapor_pressure[i] == m.evaporator_vapor_pressure[i - 1]
        else:
            return m.saturated_vapor_pressure[i] == m.super_heated_vapor_pressure

    m.relating_pressure_in_evaporator = pyo.Constraint(
        m.i, rule=_relating_pressure_in_evaporator
    )

    # Calculating the heat transfer coefficient (Equation 20)
    def _heat_transfer_coef_calculation(m, i):
        return m.heat_transfer_coef[i] == 0.001 * (
            1939.4
            + 1.40562 * m.evaporator_brine_temperature[i]
            - 0.00207525 * m.evaporator_brine_temperature[i] ** 2
            + 0.0023186 * m.evaporator_brine_temperature[i] ** 3
        )

    m.heat_transfer_coef_calculation = pyo.Constraint(
        m.i, rule=_heat_transfer_coef_calculation
    )

    # Evaporator heat transfer area calculation (Equation 21)
    def _total_evaporator_heat_transfer_area(m):
        return m.evaporator_total_area == sum(m.each_evaporator_area[i] for i in m.i)

    m.total_evaporator_heat_transfer_area = pyo.Constraint(
        rule=_total_evaporator_heat_transfer_area
    )

    # Area of the first evaporator
    def _first_evaporator_area_calculation(m):
        return m.each_evaporator_area[
            m.i.first()
        ] == m.flow_super_heated_vapor * m.cp_vapor * (
            m.super_heated_vapor_temperature
            - m.evaporator_condensate_temperature[m.i.first()]
        ) / (
            m.overall_heat_transfer_coef * m.LMTD[m.i.first()]
        ) + m.flow_super_heated_vapor * (
            m.evaporator_condensate_vapor_enthalpy - m.evaporator_condensate_enthalpy
        ) / (
            m.heat_transfer_coef[m.i.first()]
            * (
                m.evaporator_condensate_temperature[m.i.first()]
                - m.evaporator_brine_temperature[m.i.first()]
            )
            + 1e-6
        )

    m.first_evaporator_area_calculation = pyo.Constraint(
        rule=_first_evaporator_area_calculation
    )

    def _evaporator_total_area_from_heat_calculation(m):
        if N_evap == 1:
            return pyo.Constraint.Skip
        else:
            return m.evaporator_total_area == sum(
                (m.evaporator_heat_flow[i] / (m.heat_transfer_coef[i] * m.LMTD[i]))
                for i in m.i
            )

    m.evaporator_total_area_from_heat_calculation = pyo.Constraint(
        rule=_evaporator_total_area_from_heat_calculation
    )

    def _theta_1_calculation(m, i):
        if i == m.i.first():
            return (
                m.theta_1[i]
                == m.super_heated_vapor_temperature - m.evaporator_brine_temperature[i]
            )
        else:
            return (
                m.theta_1[i]
                == m.evaporator_saturated_vapor_temperature[i]
                - m.evaporator_brine_temperature[i]
            )

    m.theta_1_calculation = pyo.Constraint(m.i, rule=_theta_1_calculation)

    def _theta_2_calculation(m, i):
        if N_evap == 1:
            return (
                m.theta_2[i]
                == m.evaporator_condensate_temperature[i]
                - m.evaporator_feed_temperature
            )
        else:
            if i == m.i.first():
                return (
                    m.theta_2[i]
                    == m.evaporator_condensate_temperature[i]
                    - m.evaporator_brine_temperature[i + 1]
                )
            elif i == m.i.last():
                return (
                    m.theta_2[i]
                    == m.evaporator_condensate_temperature[i]
                    - m.evaporator_feed_temperature
                )
            else:
                return (
                    m.theta_2[i]
                    == m.evaporator_condensate_temperature[i]
                    - m.evaporator_brine_temperature[i + 1]
                )

    m.theta_2_calculation = pyo.Constraint(m.i, rule=_theta_2_calculation)

    def _LMTD_calculation(m, i):
        alpha = m.theta_1[i] / m.theta_2[i]
        eps = 1e-10
        return (
            m.LMTD[i]
            == m.theta_2[i]
            * ((alpha - 1) ** 2 + eps) ** 0.5
            / (pyo.log(alpha) ** 2 + eps) ** 0.5
        )

    m.LMTD_calculation = pyo.Constraint(m.i, rule=_LMTD_calculation)

    # Restrictions on area for uniform distribution (Equation 27, 28)
    def _area_restriction_con_1(m, i):
        if i == m.i.first():
            return pyo.Constraint.Skip
        else:
            return m.each_evaporator_area[i] <= 3 * m.each_evaporator_area[i - 1]

    m.area_restricion_con_1 = pyo.Constraint(m.i, rule=_area_restriction_con_1)

    def _area_restriction_con_2(m, i):
        if i == m.i.first():
            return pyo.Constraint.Skip
        else:
            return m.each_evaporator_area[i] >= 1 * m.each_evaporator_area[i - 1]

    m.area_restricion_con_2 = pyo.Constraint(m.i, rule=_area_restriction_con_2)

    # Temperature constraints to avoid temperature crossovers in evaporator effects (Equation 29-36)
    def _temp_con_1(m):
        return (
            m.super_heated_vapor_temperature
            >= m.evaporator_condensate_temperature[m.i.first()] + m.DT_min_1
        )

    m.temp_con_1 = pyo.Constraint(rule=_temp_con_1)

    def _temp_con_2(m, i):
        if i == m.i.first():
            return pyo.Constraint.Skip
        else:
            return (
                m.evaporator_brine_temperature[i - 1]
                >= m.evaporator_condensate_temperature[i] + m.DT_min_1
            )

    m.temp_con_2 = pyo.Constraint(m.i, rule=_temp_con_2)

    def _temp_con_3(m, i):
        if i == m.i.last():
            return pyo.Constraint.Skip
        else:
            return (
                m.evaporator_brine_temperature[i]
                >= m.evaporator_brine_temperature[i + 1] + m.DT_min_stage
            )

    m.temp_con_3 = pyo.Constraint(m.i, rule=_temp_con_3)

    def _temp_con_4(m):
        return (
            m.evaporator_brine_temperature[m.i.last()]
            >= m.evaporator_feed_temperature + m.DT_min_2
        )

    m.temp_con_4 = pyo.Constraint(rule=_temp_con_4)

    def _temp_con_5(m, i):
        if i == m.i.last():
            return pyo.Constraint.Skip
        else:
            return (
                m.evaporator_condensate_temperature[i]
                >= m.evaporator_brine_temperature[i + 1] + m.DT_min
            )

    m.temp_con_5 = pyo.Constraint(m.i, rule=_temp_con_5)

    def _temp_con_6(m):
        return (
            m.evaporator_condensate_temperature[m.i.last()]
            >= m.evaporator_feed_temperature + m.DT_min
        )

    m.temp_con_6 = pyo.Constraint(rule=_temp_con_6)

    def _temp_con_7(m, i):
        return (
            m.evaporator_condensate_temperature[i]
            >= m.evaporator_brine_temperature[i] + m.DT_min
        )

    m.temp_con_7 = pyo.Constraint(m.i, rule=_temp_con_7)

    def _temp_con_8(m, i):
        return (
            m.evaporator_saturated_vapor_temperature[i]
            >= m.evaporator_brine_temperature[i] + m.DT_min
        )

    m.temp_con_8 = pyo.Constraint(m.i, rule=_temp_con_8)

    # =====================================================================================
    # Mixer constraint
    def _mixer_energy_balance(m):
        i_last = m.i.last()
        i_first = m.i.first()
        return m.mixer_temperature == (
            m.flow_vapor_evaporator[i_last]
            * m.evaporator_condensate_temperature[i_first]
            + sum(
                m.flow_vapor_evaporator[i - 1] * m.evaporator_condensate_temperature[i]
                for i in m.i_except_1
            )
        ) / sum(m.flow_vapor_evaporator[i] for i in m.i)

    m.mixer_energy_balance = pyo.Constraint(rule=_mixer_energy_balance)
    # =====================================================================================
    # Preheater constraints

    # Energy balance in the preheater (Equation 43)
    def _energy_balance_pre_heater(m):
        return sum(m.flow_vapor_evaporator[i] for i in m.i) * m.cp_condensate * (
            m.mixer_temperature - m.fresh_water_temperature
        ) == m.flow_feed * m.cp_feed * (
            m.evaporator_feed_temperature - m.feed_temperature
        )

    m.energy_balance_pre_heater = pyo.Constraint(rule=_energy_balance_pre_heater)

    # Cp_feed calculation (Equation 44)
    def _cp_feed_estimate(m):
        return m.cp_feed == 0.001 * (
            4206.8
            - 6.6197 * m.salt_feed
            + 1.2288e-2 * m.salt_feed**2
            + (-1.1262 + 5.418e-2 * m.salt_feed) * m.feed_temperature
        )

    m.cp_feed_estimate = pyo.Constraint(rule=_cp_feed_estimate)

    # Cp_condensate calculation (Equation 45)
    def _cp_condensate_estimate(m):
        return m.cp_condensate == 0.001 * (4206.8 - 1.1262 * m.mixer_temperature)

    m.cp_condensate_estimate = pyo.Constraint(rule=_cp_condensate_estimate)

    # Preheater Heat tranfer coefficient calculation
    def _preheater_heat_transfer_coef_con(m):
        return m.preheater_heat_transfer_coef == 0.001 * (
            1939.4
            + 1.40562 * m.mixer_temperature
            - 0.00207525 * m.mixer_temperature**2
            + 0.0023186 * m.mixer_temperature**3
        )

    m.preheater_heat_transfer_coef_con = pyo.Constraint(
        rule=_preheater_heat_transfer_coef_con
    )

    # Heat transfer area of feed preheater(Equation 46)
    def _preheater_area_calculation(m):
        return m.preheater_area == sum(
            m.flow_vapor_evaporator[i] for i in m.i
        ) * m.cp_condensate * (m.mixer_temperature - m.fresh_water_temperature) / (
            m.preheater_heat_transfer_coef * m.preheater_LMTD + 1e-20
        )

    m.preheater_area_calculation = pyo.Constraint(rule=_preheater_area_calculation)

    # Preheater LMTD calculation (Equation 47)
    def _preheater_LMTD_calculation(m):
        alpha = m.preheater_theta_1 / m.preheater_theta_2
        eps = 1e-10
        return (
            m.preheater_LMTD
            == m.preheater_theta_2
            * ((alpha - 1) ** 2 + eps) ** 0.5
            / (pyo.log(alpha) ** 2 + eps) ** 0.5
        )

    m.preheater_LMTD_calculation = pyo.Constraint(rule=_preheater_LMTD_calculation)

    def _preheater_theta_1_calculation(m):
        return (
            m.preheater_theta_1 == m.mixer_temperature - m.evaporator_feed_temperature
        )

    m.preheater_theta_1_calculation = pyo.Constraint(
        rule=_preheater_theta_1_calculation
    )

    def _preheater_theta_2_calculation(m):
        return m.preheater_theta_2 == m.fresh_water_temperature - m.feed_temperature

    m.preheater_theta_2_calculation = pyo.Constraint(
        rule=_preheater_theta_2_calculation
    )

    # =====================================================================================
    # Single stage Compressor
    # Isentropic temperature constraints (Equation 51, 52)
    def _isentropic_temp_calculation(m):
        return (
            m.isentropic_temperature
            == (m.evaporator_brine_temperature[m.i.last()] + 273.15)
            * (m.super_heated_vapor_pressure / m.evaporator_vapor_pressure[m.i.last()])
            ** ((m.gamma - 1) / m.gamma)
            - 273.15
        )

    m.isentropic_temp_calculation = pyo.Constraint(rule=_isentropic_temp_calculation)

    # Maximum possible compression (Equation 53)
    def _maximum_compression_calculation(m):
        return (
            m.super_heated_vapor_pressure
            <= m.CR_max * m.evaporator_vapor_pressure[m.i.last()]
        )

    m.maximum_compression_calculation = pyo.Constraint(
        rule=_maximum_compression_calculation
    )

    # Temperature of superheated vapor
    def _temperature_super_heated_vapor_calculation(m):
        return m.super_heated_vapor_temperature == m.evaporator_brine_temperature[
            m.i.last()
        ] + 1 / m.eta * (
            m.isentropic_temperature - m.evaporator_brine_temperature[m.i.last()]
        )

    m.temperature_super_heated_vapor_calculation = pyo.Constraint(
        rule=_temperature_super_heated_vapor_calculation
    )

    # (Equation 56, 57)
    def _compressor_pressure_con(m):
        return m.super_heated_vapor_pressure >= m.evaporator_vapor_pressure[m.i.last()]

    m.compressor_pressure_con = pyo.Constraint(rule=_compressor_pressure_con)

    # Compressor work calculation (Equation 58)
    def _compressor_work_calculation(m):
        return 1 / 100 * (m.compressor_work) == 1 / 100 * (
            m.flow_super_heated_vapor
            * (m.super_heated_vapor_enthalpy - m.evaporator_vapor_enthalpy[m.i.last()])
        )

    m.compressor_work_calculation = pyo.Constraint(rule=_compressor_work_calculation)

    def _super_heated_vapor_enthalpy_calculation(m):
        return (
            1 / 1000 * m.super_heated_vapor_enthalpy
            == (-13470 + 1.84 * m.super_heated_vapor_temperature) / 1000
        )

    m.super_heated_vapor_enthalpy_calculation = pyo.Constraint(
        rule=_super_heated_vapor_enthalpy_calculation
    )

    # Salt outlet condition
    def _salt_outlet_con(m):
        return m.salt[m.i.first()] == m.salt_outlet_spec

    m.salt_outlet_con = pyo.Constraint(rule=_salt_outlet_con)

    # Fresh water constraint
    def _water_recovery_con(m):
        return (
            sum(m.flow_vapor_evaporator[i] for i in range(0, N_evap))
            == m.water_recovery_fraction * m.flow_feed
        )

    m.water_recovery_con = pyo.Constraint(rule=_water_recovery_con)

    # Costing===========================================================================
    # Costing is taken from the couper book same as used in Onishi's paper

    # Converting compressor_capacity from kW to HP
    def _comp_capacity_con(m):
        return m.compressor_capacity == m.compressor_work * 1.34

    m.comp_capacity_con = pyo.Constraint(rule=_comp_capacity_con)

    def _annual_fac_con(m):
        return m.annual_fac == m.r * (m.r + 1) ** m.years / ((1 + m.r) ** m.years - 1)

    m.annual_fac_con = pyo.Constraint(rule=_annual_fac_con)

    def _cepci_ratio_con(m):
        return m.cepci_ratio == m.cepci_2022 / m.cepci_2003

    m.cepci_ratio_con = pyo.Constraint(rule=_cepci_ratio_con)

    # All costs are in kUS$
    def _compressor_capex_con(m):
        return m.compressor_capex == m.cepci_ratio * (
            7.9 * m.compressor_capacity**0.62
        )

    m.compressor_capex_con = pyo.Constraint(rule=_compressor_capex_con)

    def _evaporator_capex_con(m, i):
        # material factor for nickel
        fm = 1.8
        return m.evaporator_capex[i] == m.cepci_ratio * fm * 1.218 * pyo.exp(
            3.2362
            - 0.0126 * pyo.log(m.each_evaporator_area[i] * 10.764)
            + 0.0244 * (pyo.log(m.each_evaporator_area[i] * 10.764)) ** 2
        )

    m.evaporator_capex_con = pyo.Constraint(m.i, rule=_evaporator_capex_con)

    def _preheater_capex_con(m):
        a = m.preheater_area * 10.764
        fd = pyo.exp(-0.9816 + 0.0830 * pyo.log(a))  # utube heat exchanger
        fp = 1  # pressure < 4 bar
        fm = 1  # carbon steel
        Cb = pyo.exp(8.821 - 0.308 * pyo.log(a) + 0.0681 * (pyo.log(a)) ** 2)
        return m.preheater_capex == m.cepci_ratio * 1.218 / 1000 * fd * fm * fp * Cb

    m.preheater_capex_con = pyo.Constraint(rule=_preheater_capex_con)

    m.capital_cost = pyo.Constraint(
        expr=m.CAPEX
        == m.annual_fac
        * (
            sum(m.evaporator_capex[i] for i in range(N_evap))
            + m.compressor_capex
            + m.preheater_capex
        )
    )

    m.operation_cost = pyo.Constraint(expr=m.OPEX == 1.4 * m.compressor_work)

    m.obj = pyo.Objective(expr=(m.CAPEX + m.OPEX))

    return m
