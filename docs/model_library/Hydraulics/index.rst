Pipeline Hydraulics
====================

.. note::
   The hydraulics module presented below is currently only added as an extension to the strategic model.

Overview
-----------

Produced water (PW) network operations are highly affected by the pipeline designs and geographical terrain because of pressure losses due to friction and elevation changes. PARETO hydraulics module is an extension to the strategic model that allows the user to compute pressures at every node in the network enabling the user to add operational constraints such as maximum allowable operating pressures (MAOP) and minimum required pressure at injection facilities or at 3rd party offtake points. For this, the PARETO model explicitly considers pipeline details (i.e., length, diameter, material, etc.) and geographic elevations in the model to compute time varying pressures at each node. The hydraulics module is an extension to the PARETO strategic model and can be accessed through the following options in the config argument: 

a)	Hydraulics.false: This option allows the user to skip the hydraulics computations in the PARETO model.

b)	Hydraulics.post_process: In this method, the basic PARETO strategic model is solved as step 1, and then using the optimal flows and network design, the hydraulics block containing constraints for pressure balances and losses is solved as step 2. In this case, as only the hydraulics model block solved for the objective of minimizing cost, the optimal values for variables included in the main strategic model and obtained from step 1 remain unaffected.

c)	Hydraulics.co_optimize: In this method, the hydraulics model block is solved together with the strategic model. However, as the flow and diameter are variables in the strategic model, the addition of hydraulics block makes the model a mixed integer nonlinear programming (MINLP) model. In order to solve this MINLP model, the strategic model without the hydraulics constraints is solved as step 1 to determine a good initial state for all variables and constraints.
 
Note: The MINLP as currently implemented requires the following MINLP solvers: SCIP and BARON. The model is first solved using BARON (if available) to determine a feasible solution and then using SCIP. 
Some subtle differences in model components such as in the definition of variables and parameters have been made to avoid nonlinearities and allow the user to use the same solver for solving the post-process method as used for the strategic model. These differences will be shown in the description of mathematical notation and formulation below.


+--------------------------------------------------------+
| Section                                                |
+========================================================+
| :ref:`hydraulics_model_mathematical_notation`          |
+--------------------------------------------------------+
| :ref:`mathematical_model_formulation`                  |
+--------------------------------------------------------+

.. _hydraulics_model_mathematical_notation:

Hydraulics Model Mathematical Notation
-------------------------------------------

Similar to the strategic model, following color coding has been implemented in describing the model notation. All input :math:`\textcolor{green}{parameters}` are in :math:`\textcolor{green}{green}` and all model :math:`\textcolor{red}{variables}` are in :math:`\textcolor{red}{red}`.

**Parameters**

:math:`\textcolor{green}{\zeta_{l}}` =                        Geographical elevation of a Node

:math:`\textcolor{green}{\rho.g}` =                        Product of water density and accelaration due to gravity

:math:`\textcolor{green}{\iota^{CHW}}` =                        Constant for pipeline material in Hazen-Williams equation

:math:`\textcolor{green}{\nu^{Pump}}` =                        Fixed cost of installing a pump

:math:`\textcolor{green}{\nu^{Electricity}}` =                        Electricity price

:math:`\textcolor{green}{\eta^{Pump}}` =                        Efficiency of the pump

:math:`\textcolor{green}{\eta^{Motor}}` =                        Efficiency of the motor for pump

:math:`\textcolor{green}{\xi^{Minimum}}` =                        Minimum allowable operating pressure in a pipeline

:math:`\textcolor{green}{\xi^{Maximum}}` =                        Maximum allowable operating pressure in a pipeline (MAOP)

:math:`\textcolor{green}{D_{l,\tilde{l}}^{Existing}}` =                        Diameter of an existing pipeline

:math:`\textcolor{green}{\upsilon_{p,t}^{Maximum}}` =                        Well pressure at production or completions pad

**Binary Variables**

:math:`\textcolor{red}{y_{l,\tilde{l},[t]}^{Pump}}` =     New pump installation, 1 if a new pump is installed, 0 otherwise

**Continuous Variables**

:math:`\textcolor{red}{H_{l,\tilde{l},t}^{Pump}}` =                        Pump head added in the direction of flow

:math:`\textcolor{red}{H_{l,\tilde{l},t}^{Valve}}` =                        Valve head removed in the direction of flow

:math:`\textcolor{red}{C_{l,\tilde{l}}^{Pump}}` =                      Total cost of pumping between given nodes

:math:`\textcolor{red}{P_{l,t}}` =                      Node pressure

:math:`\textcolor{red}{Z^{Hydraulics}}` =                   Total cost of all pumps, Objective function variable

**Notations specific to the post_processing method:**

  :math:`\textcolor{green}{D_{l,\tilde{l}}^{Effective}}` =                        Effective pipeline diameter

  :math:`\textcolor{green}{H_{l,\tilde{l},t}^{Friction, HW}}` =                        Head loss due to friction (using Hazen-Williams equation)

**Notations specific to the co_optimize method:**

  :math:`\textcolor{red}{D_{l,\tilde{l}}^{Effective}}` =                        Effective pipeline diameter

  :math:`\textcolor{red}{H_{l,\tilde{l},t}^{Friction, HW}}` =                        Head loss due to friction (using Hazen-Williams equation)


.. _mathematical_model_formulation:

Hydraulics Model Formulation
--------------------------------


**Objective:**

Total cost of pumping in the pipeline network.

.. math::

    \min \ \textcolor{red}{Z^{Hydraulics}} = \sum_{(l,\tilde{l}) \in LLA}\textcolor{red}{C_{l,\tilde{l}}^{Pump}}


**Max allowable pressure rule:** :math:`\forall \textcolor{blue}{l \in L}, \textcolor{blue}{t \in T}`

Limits the maximum operating pressure in a pipeline.

.. math::

    \textcolor{red}{P_{l,t}} \leq \textcolor{green}{\xi^{Maximum}}


**Pump head rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}, \textcolor{blue}{t \in T}`

Allows pumping only if a pump exists in a pipeline.

.. math::

    \textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \leq \textcolor{green}{M^{Flow}} \cdot \textcolor{red}{y_{l,\tilde{l},[t]}^{Pump}}


**Equations/constraints specific to the post_process method**

      **Effective diameter calculation:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}`

      Aggregate diameters for all existing pipelines between any 2 locations.

      .. math::

          \textcolor{green}{D_{l,\tilde{l}}^{Effective}} = \textcolor{green}{D_{l,\tilde{l}}^{Existing}} + \sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d,[t]}^{Pipeline}}


      **Hazen-Williams based frictional head loss calculation:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}, \textcolor{blue}{t \in T}`

      Calculate head loss using Hazen-Williams equation. Note that units for all terms in this equation are in SI units so, appropriate conversion factors must be added.

      .. math::

          \textcolor{green}{H_{l,\tilde{l},t}^{Friction, HW}} \cdot (\textcolor{green}{D_{l,\tilde{l}}^{Effective}})^{4.87}
          = 10.704 \cdot (\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} / \textcolor{green}{\iota^{CHW}})^{1.85} \cdot \textcolor{green}{\lambda_{l,\tilde{l}}^{Pipeline}}

      **Node pressure rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}, \textcolor{blue}{t \in T}`

      Pressure constraint based on Bernoulli's energy balance equation.

      .. math::

          \textcolor{red}{P_{l,t}} + \textcolor{green}{\zeta_{l}} \cdot \textcolor{green}{\rho.g}
          = \textcolor{red}{P_{\tilde{l},t}} + \textcolor{green}{\zeta_{\tilde{l}}} \cdot \textcolor{green}{\rho.g}
          + \textcolor{green}{H_{l,\tilde{l},t}^{Friction, HW}} \cdot \textcolor{green}{\rho.g}
          + \textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \cdot \textcolor{green}{\rho.g}
          - \textcolor{red}{H_{l,\tilde{l},t}^{Valve}} \cdot \textcolor{green}{\rho.g}


      **Pump cost rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}`

      Allows pumping only if a pump exists in a pipeline.

      .. math::

          \textcolor{red}{C_{l,\tilde{l}}^{Pump}} = \textcolor{green}{\nu^{Pump}} \cdot \textcolor{red}{y_{l,\tilde{l},[t]}^{Pump}}
          + \textcolor{green}{\nu^{Electricity}} \cdot \textcolor{green}{\rho.g} \cdot \sum_{t \in T}\textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \cdot \textcolor{red}{F_{l,\tilde{l},t}^{Piped}}


**Equations/constraints specific to the co_optimize method**

    **Effective diameter rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}`

    Aggregate diameters for all existing pipelines between any 2 locations.

    .. math::

        \textcolor{red}{D_{l,\tilde{l}}^{Effective}} = \textcolor{green}{D_{l,\tilde{l}}^{Existing}} + \sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d,[t]}^{Pipeline}}


    **Hazen-Williams based frictional head loss calculation:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}, \textcolor{blue}{t \in T}`

    Calculate head loss using Hazen-Williams equation. Note that units for all terms in this equation are in SI units so, appropriate conversion factors must be added.

    .. math::

        \textcolor{red}{H_{l,\tilde{l},t}^{Friction, HW}} \cdot (\textcolor{red}{D_{l,\tilde{l}}^{Effective}})^{4.87}
        = 10.704 \cdot (\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} / \textcolor{green}{\iota^{CHW}})^{1.85} \cdot \textcolor{green}{\lambda_{l,\tilde{l}}^{Pipeline}}

    **Node pressure rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}, \textcolor{blue}{t \in T}`

    Pressure constraint based on Bernoulli's energy balance equation.

    .. math::

        \textcolor{blue}{\tilde{l},l \in LLA}
        \textcolor{red}{P_{l,t}} + \textcolor{green}{\zeta_{l}} \cdot \textcolor{green}{\rho.g}
         = \textcolor{red}{P_{\tilde{l},t}} + \textcolor{green}{\zeta_{\tilde{l}}} \cdot \textcolor{green}{\rho.g}
         + \textcolor{red}{H_{l,\tilde{l},t}^{Friction, HW}} \cdot \textcolor{green}{\rho.g}
         - \textcolor{red}{H_{\tilde{l},l,t}^{Friction, HW}} \cdot \textcolor{green}{\rho.g}
         - \textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \cdot \textcolor{green}{\rho.g}
         + \textcolor{red}{H_{l,\tilde{l},t}^{Valve}} \cdot \textcolor{green}{\rho.g}

    .. math::
         \textcolor{blue}{\tilde{l},l \notin LLA}
        \textcolor{red}{P_{l,t}} + \textcolor{green}{\zeta_{l}} \cdot \textcolor{green}{\rho.g}
         = \textcolor{red}{P_{\tilde{l},t}} + \textcolor{green}{\zeta_{\tilde{l}}} \cdot \textcolor{green}{\rho.g}
         + \textcolor{red}{H_{l,\tilde{l},t}^{Friction, HW}} \cdot \textcolor{green}{\rho.g}
         - \textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \cdot \textcolor{green}{\rho.g}
         + \textcolor{red}{H_{l,\tilde{l},t}^{Valve}} \cdot \textcolor{green}{\rho.g}

    **Pump cost rule:** :math:`\forall \textcolor{blue}{l,\tilde{l} \in LLA}`

    Allows pumping only if a pump exists in a pipeline.

    .. math::

        \textcolor{red}{C_{l,\tilde{l}}^{Pump}} = \textcolor{green}{\nu^{Pump}} \cdot \textcolor{red}{y_{l,\tilde{l},[t]}^{Pump}}
        + \textcolor{green}{\nu^{Electricity}} \cdot \textcolor{green}{\rho.g} \cdot \sum_{t \in T}\textcolor{red}{H_{l,\tilde{l},t}^{Pump}} \cdot \textcolor{red}{F_{l,\tilde{l},t}^{Piped}}


