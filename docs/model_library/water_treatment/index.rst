Water Treatment
===============

Overview
-----------

Treatment systems play a crucial role for achieving desired water quality for various purposes, such as recycling for hydraulic fracturing, beneficial reuse applications, and critical mineral recovery.  Depending on the purpose and degree of treatment, the costs associated with treatment systems can be significant and greatly impact the investment cost in a management option. This makes it necessary to carefully consider the treatment models and their costs when evaluating produced water management strategies. Therefore, it is essential to integrate treatment models into the PARETO decision-making process. This will enable stakeholders to better understand the trade-offs between different management options and their associated costs, ultimately leading to more informed decisions.


+--------------------------------------------------------+
| Section                                                |
+========================================================+
| :ref:`treatmet_model_within_pareto_network`            |
+--------------------------------------------------------+
| :ref:`treatment_model_description`                     |
+--------------------------------------------------------+
| :ref:`treatment_efficiency_(recovery)`                 |
+--------------------------------------------------------+
| :ref:`removal_efficiency`                              |
+--------------------------------------------------------+
| :ref:`treatment_cost`                                  |
+--------------------------------------------------------+


.. _treatmet_model_within_pareto_network:

Treatment model within PARETO network
-----------------------------------------

The PARETO network identifies treatment plants based on their location (:math:`r \in R`), capacity (:math:`j \in J`), and technology (:math:`wt \in WT`). The streams that are piped or trucked to treatment plants are represented by arcs (:math:`(l,r) \in LRA \cup LRT`), where l can be any location or node in PARETO network. The indices :math:`j` and :math:`wt` are employed in conjunction with a binary variable to install or expand a treatment plant with a specific capacity (for further details, please refer to `strategic  water management <../strategic_water_management/index.rst>`_).
    
The following equation describes the flow balance at location :math:`r`:

.. math::
    
    \sum_{l \in L | (l, r) \in LRA \cup LRT}F_{n,r,t} = F_{r,t}^{treatment\ feed}

.. math::
    
    \sum_{l \in L | (l, r) \in LRA \cup LRT} F_{n,r,t} \cdot Q_{n,qc,t} = Q_{r,qc,t} \cdot F_{r,t}^{treatment\ feed}

where :math:`F` and :math:`Q` denotes the flow and quality (concentrations) of streams. The units of concentration are typically reported as mass/volume (mg/L, g/m3, kg/L, etc.) and the units of flow rate are reported in volume/time (e.g. bbl/week).


.. _treatment_model_description:

Treatment Model Description
--------------------------------

Water treatment systems are modeled using overall water and constituent balances, treatment and removal efficiencies, and operating cost and capital cost values/equations. The schematic in Figure 1 depicts a treatment unit that processes a treatment feed with specific qualities, yielding two output streams: treated water and residual water. The treated water and residual water streams have distinct qualities, which vary depending on the specific treatment process employed.
The overall water and constituent balance equations for water treatment systems are as follows:
  

.. figure:: ../../img/treatmentpic.png
    :width: 400
    :align: center

    Figure 1. Treatment plant schematic
 


* Overall water balance: 

  .. math::

      F^{treatment\ feed} = F^{treated\ water} + F^{residual\ water}

* Overall constituent balance: 

  .. math::

      F^{treatment\ feed}Q^{feed} = F^{treated\ water}Q^{treated\ water} + F^{residual\ water}Q^{residual\ water}


.. _treatment_efficiency_(recovery):

Treatment Efficiency (Recovery)
--------------------------------------

Treatment efficiency is defined as the ratio of the treated water volume to the ratio of the feed water volume to the treatment plant as follows:

.. math::
    
    \text{Treatment efficiency} = \frac{F^{treated\ water}}{F^{treatment\ feed}}

Note that treatment efficiency can also be expressed as a percentage by multiplying the above expression by 100.

.. math::
    
    \text{Treatment efficiency (%)} = \frac{F^{treated\ water}}{F^{feed}} \times 100
    

.. _removal_efficiency:

Water Treatment Removal Efficiency
-----------------------------------

Removal efficiency is a measure of the overall reduction in the concentration or load of a constituent in a treatment plant, expressed as a percentage. The removal efficiency of a certain constituent is commonly calculated based on the influent (feed) concentration and the effluent (treated water) concentration as follows:

.. math::
    
    \text{Removal Efficiency (%)} = \frac{Q^{treatment\ feed} - Q^{treated\ water}}{Q^{treatment\ feed}} \times 100

For example, if the influent concentration of a constituent is 200 mg/L and the effluent concentration is 20 mg/L, then the removal efficiency can be calculated as:

.. math::
    
    \text{Removal Efficiency (%)} = \frac{200 - 20}{200} = 0.9 = 90\%

Another method for calculating removal efficiency is the measure of overall reduction in the load (mass times flow) instead of reduction in concentration. This approach is specifically useful in situations where there are substantial water losses due to evaporation and evapotranspiration. 

.. math::

   \text{Removal Efficiency (%)} = \frac{F^{treatment\ feed}Q^{treatment\ feed} - F^{treated\ water}Q^{treated\ water}}{F^{treatment\ feed}Q^{treatment\ feed}}


it should be paid attention that the load-based definition of removal efficiency will have a non-zero value even for situations where there is no concentration reduction happening, such as a simple splitter. To correctly evaluate the load-based removal efficiency in this case, considering `Qfeed = Qtreatedwater` and substituting `Qfeed` with `Qtreatedwater` in the load-based removal efficiency formula, we will obtain the removal efficiency value as follows:

Removal efficiency = 1 - treatment efficiency (recovery)

It is worth noting that in cases where there is minimal water loss to the residual stream, such that the treated water flow is approximately equal to the feed flow, the removal efficiency values obtained by the two definitions become the same. 

PARETO supports both formulations and gives the user the option to choose between the two methods based on their available data or the technology considered. The two options are expressed as `RemovalEfficiencyMethod.Concentration_based` and `RemovalEfficiencyMethod.Load_based` in PARETO configruation argument for removal efficiency.

.. _treatment_cost:

Water Treatment Cost
---------------------
The total cost of produced water treatment consist of capital costs and annual operating costs.Capital costs include the costs associated with the land purchanse, construction, purchasing process equipment, and installation. Annual operating costs refer to the cost during plant operation such as cost of energy, equimpment replacement, chemicals, labor, and maintenance. The sum of the unit operating costs and the unit annualized capital costs determines the total capital cost per unit volume of produced water.

In PARETO, treatment costs can be incorporated in three ways. Firstly, users may enter their own estimated values for operating and capital costs of each treatment technology. PARETO provides a treatment technology matrix displayed below (for further detail regarding selected technologies and references please refer to the provided sheet: :download:`treatment matrix <../2022_10_31_206_017_PWTreatment_Technology_matrix.xlsx>`)

) with data collected from available literature on various technologies, such as membrane distillation, multieffect distillation, mechanical vapor recompression, and osmotically assisted reverse osmosis. The technologies considered in this matrix are capable of treating hypersaline produced water up to saturation limits. Users may use these values to evaluate treatment options using PARETO. However, we encourage users to provide their own cost data, obtained from treatment technology vendors, to enable better evaluation of management options.
It is important to note that currently, PARETO incorporates treatment costs for discrete values of treatment capacity expansions. In other words, the treatment cost calculations are limited to specific capacity levels.

+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
|                                   Treatment Technology                        |  Pretreatment   | Multiple effect evaopration    | Mechanical vapor compression (MVC)        | Direct contact membrane distillation (DCMD)| Air gap membrane distillation (AGMD)      | Permeate gap membrane distillation (PGMD) |Conductive gap membrane distillation (CGMD)| Sweeping gas membrane distillation (SGMD)  | Vacuum membrane distillation (VMD)         | Osmotically assisted reverse osmosis (OARO)| Cascading osmotically mediated reverse osmosis (COMRO) | Low-salt rejection reverse osmosis (LSRRO) | Brine reflux OARO (BR-OARO)                | Split feed counterflow reverse osmosis (SF-OARO) | Consecutive loop OARO (CL-OARO)            |
+===============================================================================+=================+================================+===========================================+============================================+===========================================+===========================================+===========================================+============================================+============================================+============================================+========================================================+============================================+============================================+==================================================+============================================+
|CAPEX [$ / (bbl feed/day)]                                                     | 60 - 90         | 726                            | 1092                                      | 363-1148                                   | 511-589                                   | 534-749                                   | 461-645                                   | 1339                                       | 314-689                                    | 448-1432                                   | 1301                                                   | 965                                        | 1389                                       | 1777                                             | 2181                                       |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
|OPEX [$ / bbl feed]                                                            | 0.04 - 1.50     | 1.25                           | 0.34                                      | 0.61-1.51                                  | 0.43-0.62                                 | 1.28-3.80                                 | 0.53-1.15                                 | 1.27                                       | 0.45-1.77                                  | 0.066-0.32                                 | 0.47                                                   | 0.43                                       | 0.51                                       | 0.55                                             | 0.68                                       |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
|total annualized cost [$ / bbl feed]                                           | 0.07 - 1.40     | 1.57                           | 0.82                                      | 0.79-1.83                                  | 0.56-0.73                                 | 1.44-3.92                                 | 0.67-1.25                                 | 1.56                                       | 0.60-1.84                                  | 0.12-0.54                                  | 0.83                                                   | 0.7                                        | 0.82                                       | 0.94                                             | 1.15                                       |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Plant capacity [bbl feed/ day]                                                | 3774            | 5661                           | 5661                                      | 5079                                       | 5079                                      | 5079                                      | 5079                                      | 5079                                       | 5079                                       | 2944                                       | 2944                                                   | 2944                                       | 5079                                       | 5079                                             | 5079                                       |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| TDS operating limits [mg/L]                                                   | N/A             | 0-350,000                      | 0-350,000                                 | 0-350,000                                  | 0-350,000                                 | 0-350,000                                 | 0-350,000                                 | 0-350,000                                  | 0-350,000                                  | 0-350,000                                  | 0-350,000                                              | 0-350,000                                  | 0-350,000                                  | 0-350,000                                        | 0-350,000                                  |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Energy type                                                                   | Varies          | Thermal                        | Electrical                                | Thermal                                    | Thermal                                   | Thermal                                   | Thermal                                   | Thermal                                    | Thermal                                    | Electrical                                 | Electrical                                             | Electrical                                 | Electrical                                 | Electrical                                       | Electrical                                 |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Theoretical energy requirements [kWh/m3]                                      | Varies          | 200 kWth/m3                    | 20-30                                     | 182-359 kWth/m3                            | 117-167 kWth/m3                           | 395-1214 kWth/m3                          | 164-354 kWth/m3                           | 364 kWth/m3                                | 130-640 kWth/m3                            | 8-20                                       | 12.8                                                   | 28.9                                       | 16.13                                      | 17.46                                            | 26.6                                       |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Water recovery [%]                                                            | Varies          | 82                             | 82                                        | varies                                     | 74                                        | 74                                        | 74                                        | 74                                         | 74                                         | varies                                     | 75                                                     | 75                                         | 74                                         | 74                                               | 74                                         |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Inlet salinity [mg/ LTDS]                                                     | N/A             | 70                             | 70                                        |varies                                      | 100                                       | 100                                       | 100                                       | 100                                        | 100                                        | varies                                     | 70                                                     | 70                                         | 100                                        | 100                                              | 100                                        |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+
| Brine salinity [mg/L TDS]                                                     | N/A             | 300000                         | 300000                                    | 300000                                     | 300000                                    | 300000                                    | 300000                                    | 300000                                     | 300000                                     | 230000                                     | 230000                                                 | 300000                                     | 300000                                     | 300000                                           |300000                                      |
+-------------------------------------------------------------------------------+-----------------+--------------------------------+-------------------------------------------+--------------------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------------+--------------------------------------------+--------------------------------------------+--------------------------------------------------+--------------------------------------------+



An alternative approach to incorporating treatment costs in PARETO is through the use of surrogate models. These models allow for linear or nonlinear approximations of treatment costs as a function of treatment capacity, feed quality, and recovery. This method is currently under development and not yet available in the current version of PARETO, and it is planned for inclusion in future updates.

The third method for incorporating treatment costs into PARETO is through the integration of rigorous technoeconomic optimization treatment models. These models allow for accurate capture of the effect of changes in input parameters on treatment plant performance and costs. Currently, a technoeconomic optimization-based modeling approach for single effect and multi-effect mechanical vapor compression (MVR) desalination systems is available for integration with PARETO. The following section will provide a detailed description of the MVR modeling effort.

