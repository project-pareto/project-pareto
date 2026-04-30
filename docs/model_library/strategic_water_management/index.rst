Strategic Water Management
==========================

Overview
--------

Given a set of existing network components (completion pads, storage pads, production pads, and distribution options like trucks and/or pipelines) and capacity expansion options, the strategic water management model provides an insight into financial opportunities and mid-long term investment decisions to reduce operational costs or maximize reuse or reduce externally sourced water consumption.

+---------------------------------------------------------+
| Section                                                 |
+=========================================================+
| :ref:`strategic_model_terminology`                      |
+---------------------------------------------------------+
| :ref:`strategic_model_mathematical_notation`            |
+---------------------------------------------------------+
| :ref:`strategic_model_mathematical_program_formulation` |
+---------------------------------------------------------+
| :ref:`strategic_model_water_quality_extension`          |
+---------------------------------------------------------+
| :ref:`strategic_model_discrete_water_quality_extension` |
+---------------------------------------------------------+
| :ref:`strategic_model_references`                       |
+---------------------------------------------------------+


.. _strategic_model_terminology:

Terminology
-----------

**Beneficial reuse options:** This term refers to the reuse of water at mining facilities, farms, etc.

**Completions demand:** Demand set by completions pads.  This demand can be met by produced water, treated water, or externally sourced water.

**Completions reuse water:** Water that meets demand at a completions site. This does not include externally sourced water or water for beneficial reuse.

**Network Nodes:** These are branch points for pipelines only.

.. note:: Well pads are not a subset of network nodes.

:math:`[\textcolor{blue}{t}]` **or** :math:`[\textcolor{blue}{t \in T}]` **:** This notation indicates that timing of capacity expansion has not yet been implemented.

**Terminal storage level:** These are goal storage levels for the final time period. Without this, the storage levels would likely be depleted in the last time period.

**Water boosting:** Moving large volumes of water requires water pumps. Water boosting refers to the infrastructure required to maintain water pressure.


.. _strategic_model_mathematical_notation:

Strategic Model Mathematical Notation
-------------------------------------

**Sets**

:math:`\textcolor{blue}{t \in T}`           Time periods (i.e. days)

:math:`\textcolor{blue}{p \in P}`           Well pads

:math:`\textcolor{blue}{p \in PP}`          Production pads (subset of well pads :math:`\textcolor{blue}{P}`)

:math:`\textcolor{blue}{p \in CP}`          Completions pads (subset of well pads :math:`\textcolor{blue}{P}`)

:math:`\textcolor{blue}{f \in F}`           External water sources

:math:`\textcolor{blue}{k \in K}`           Disposal sites

:math:`\textcolor{blue}{s \in S}`           Storage sites

:math:`\textcolor{blue}{r \in R}`           Treatment sites

:math:`\textcolor{blue}{o \in O}`           Beneficial reuse options

:math:`\textcolor{blue}{n \in N}`           Network nodes

:math:`\textcolor{blue}{l \in L}`           Locations (superset of well pads, disposal sites, nodes, ...)

:math:`\textcolor{blue}{d \in D}`           Pipeline diameters

:math:`\textcolor{blue}{c \in C}`           Storage capacities

:math:`\textcolor{blue}{j \in J}`           Treatment capacities

:math:`\textcolor{blue}{i \in I}`           Injection (i.e. disposal) capacities

.. note::
    The sets for capacity sizes :math:`\textcolor{blue}{d \in D}`, :math:`\textcolor{blue}{c \in C}`, :math:`\textcolor{blue}{j \in J}`, :math:`\textcolor{blue}{i \in I}` should also include the 0th case (e.g., 0 bbl) that indicates the choice to not expand capacity.
    Alternatively, if it is desired to only consider sizes to build, the 0th case can be left out.

:math:`\textcolor{blue}{wt \in WT}`           Treatment technologies

:math:`\textcolor{blue}{(p,p) \in PCA}`     Production-to-completions pipeline arcs

:math:`\textcolor{blue}{(p,n) \in PNA}`     Production-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) \in PPA}`     Production-to-production pipeline arcs

:math:`\textcolor{blue}{(p,n) \in CNA}`     Completions-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) \in CCA}`     Completions-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,n) \in NNA}`     Node-to-node pipeline arcs

:math:`\textcolor{blue}{(n,p) \in NCA}`     Node-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,k) \in NKA}`     Node-to-disposal pipeline arcs

:math:`\textcolor{blue}{(n,s) \in NSA}`     Node-to-storage pipeline arcs

:math:`\textcolor{blue}{(n,r) \in NRA}`     Node-to-treatment pipeline arcs

:math:`\textcolor{blue}{(n,o) \in NOA}`     Node-to-beneficial reuse pipeline arcs

:math:`\textcolor{blue}{(f,p) \in FCA}`     Externally sourced water-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,n) \in RNA}`     Treatment-to-node pipeline arcs

:math:`\textcolor{blue}{(r,p) \in RCA}`     Treatment-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,k) \in RKA}`     Treatment-to-disposal pipeline arcs

:math:`\textcolor{blue}{(r,s) \in RSA}`     Treatment-to-storage pipeline arcs

:math:`\textcolor{blue}{(r,o) \in ROA}`     Treatment-to-reuse pipeline arcs

:math:`\textcolor{blue}{(s,n) \in SNA}`     Storage-to-node pipeline arcs

:math:`\textcolor{blue}{(s,p) \in SCA}`     Storage-to-completions pipeline arcs

:math:`\textcolor{blue}{(s,k) \in SKA}`     Storage-to-disposal pipeline arcs

:math:`\textcolor{blue}{(s,r) \in SRA}`     Storage-to-treatment pipeline arcs

:math:`\textcolor{blue}{(s,o) \in SOA}`     Storage-to-beneficial reuse pipeline arcs

:math:`\textcolor{blue}{(l,\tilde{l}) \in LLA}`     All valid pipeline arcs

:math:`\textcolor{blue}{(p,p) \in PCT}`     Production-to-completions trucking arcs

:math:`\textcolor{blue}{(p,k) \in PKT}`     Production-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) \in PST}`     Production-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) \in PRT}`     Production-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,o) \in POT}`     Production-to-beneficial reuse trucking arcs

:math:`\textcolor{blue}{(f,p) \in FCT}`     Externally sourced water-to-completions trucking arcs

:math:`\textcolor{blue}{(p,k) \in CKT}`     Completions-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) \in CST}`     Completions-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) \in CRT}`     Completions-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,p) \in CCT}`     Completions-to-completions trucking arcs (flowback reuse)

:math:`\textcolor{blue}{(s,p) \in SCT}`     Storage-to-completions trucking arcs

:math:`\textcolor{blue}{(s,k) \in SKT}`     Storage-to-disposal trucking arcs

:math:`\textcolor{blue}{(s,o) \in SOT}`     Storage-to-reuse trucking arcs

:math:`\textcolor{blue}{(r,k) \in RKT}`     Treatment-to-disposal trucking arcs

:math:`\textcolor{blue}{(r,s) \in RST}`     Treatment-to-storage trucking arcs

:math:`\textcolor{blue}{(r,o) \in ROT}`     Treatment-to-reuse trucking arcs

:math:`\textcolor{blue}{(l,\tilde{l}) \in LLT}`     All valid trucking arcs


**Continuous Variables**

:math:`\textcolor{red}{F_{l,\tilde{l},t}^{Piped}}` =                        Produced water piped from one location to another location

:math:`\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}}` =                      Water trucked from one location to another location

:math:`\textcolor{red}{F_{f,p,t}^{Sourced}}` =                      Externally sourced water **piped** to completions

:math:`\textcolor{red}{F_{p,t}^{PadStorageIn}}` =                   Water put into completions pad storage

:math:`\textcolor{red}{F_{p,t}^{PadStorageOut}}` =                  Water removed from completions pad storage

:math:`\textcolor{red}{F_{s,t}^{StorageEvaporationStream}}` =       Water at storage lost to evaporation

:math:`\textcolor{red}{F_{r,t}^{TreatmentFeed}}` =       Flow of feed to a treatment site

:math:`\textcolor{red}{F_{r,t}^{ResidualWater}}` =                  Flow of residual water out of a treatment site

:math:`\textcolor{red}{F_{r,t}^{TreatedWater}}` =                   Flow of treated water out of a treatment site

:math:`\textcolor{red}{F_{p,t}^{CompletionsReuseDestination}}` =    Water delivered to completions pad for reuse

:math:`\textcolor{red}{F_{k,t}^{DisposalDestination}}` =            Water injected at disposal site

:math:`\textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}` =     Water delivered to beneficial reuse option

:math:`\textcolor{red}{F_{p,t}^{CompletionsDestination}}` =         All water delivered to completions pad

:math:`\textcolor{red}{L_{s,t}^{Storage}}` =                        Water level at storage site at the end of time period t

:math:`\textcolor{red}{L_{p,t}^{PadStorage}}` =                     Water level in completions pad storage  at the end of time period t

:math:`\textcolor{red}{F^{TotalTrucked}}` =                         Total volume of water trucked

:math:`\textcolor{red}{F^{TotalSourced}}` =                         Total volume of externally sourced water

:math:`\textcolor{red}{F^{TotalDisposed}}` =                        Total volume of produced water disposed

:math:`\textcolor{red}{F^{TotalCompletionsReuse}}` =                Total volume of produced water reused at completions

:math:`\textcolor{red}{F^{TotalBeneficialReuse}}` =                 Total volume of water beneficially reused

:math:`\textcolor{red}{C_{l,\tilde{l},t}^{Piped}}` =                        Cost of piping produced water from one location to another location

:math:`\textcolor{red}{C_{l,\tilde{l},t}^{Trucked}}` =                      Cost of trucking produced water from one location to another location

:math:`\textcolor{red}{C_{f,p,t}^{Sourced}}` =                      Cost of sourcing external water from source to completions pad

:math:`\textcolor{red}{C_{k,t}^{Disposal}}` =                       Cost of injecting produced water at disposal site

:math:`\textcolor{red}{C_{r,t}^{Treatment}}` =                      Cost of treating produced water at treatment site

:math:`\textcolor{red}{C_{p,t}^{CompletionsReuse}}` =               Cost of reusing produced water at completions site

:math:`\textcolor{red}{C_{s,t}^{Storage}}` =                        Cost of storing produced water at storage site (incl. treatment)

:math:`\textcolor{red}{C_{o,t}^{BeneficialReuse}}` =                Processing cost of sending water to beneficial reuse

:math:`\textcolor{red}{R_{s,t}^{Storage}}` =                        Credit for retrieving stored produced water from storage site

:math:`\textcolor{red}{R_{o,t}^{BeneficialReuse}}` =                Credit for sending water to beneficial reuse

:math:`\textcolor{red}{C^{TotalSourced}}` =                         Total cost of externally sourced water

:math:`\textcolor{red}{C^{TotalDisposal}}` =                        Total cost of injecting produced water

:math:`\textcolor{red}{C^{TotalTreatment}}` =                       Total cost of treating produced water

:math:`\textcolor{red}{C^{TotalCompletionsReuse}}` =                Total cost of reusing produced water

:math:`\textcolor{red}{C^{TotalPiping}}` =                          Total cost of piping produced water

:math:`\textcolor{red}{C^{TotalStorage}}` =                         Total cost of storing produced water

:math:`\textcolor{red}{C^{TotalTrucking}}` =                        Total cost of trucking produced water

:math:`\textcolor{red}{C^{TotalBeneficialReuse}}` =                 Total processing cost for sending water to beneficial reuse

:math:`\textcolor{red}{C^{Slack}}` =                                Total cost of slack variables

:math:`\textcolor{red}{R^{TotalStorage}}` =                         Total credit for withdrawing produced water

:math:`\textcolor{red}{R^{TotalBeneficialReuse}}` =                 Total credit for sending water to beneficial reuse

:math:`\textcolor{red}{D_{k,[t]}^{Capacity}}` =                     Disposal capacity in a given time period at disposal site

:math:`\textcolor{red}{X_{s,[t]}^{Capacity}}` =                     Storage capacity in a given time period at storage site

:math:`\textcolor{red}{T_{r,[t]}^{Capacity}}` =                     Treatment capacity in a given time period at treatment site

:math:`\textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}}` =                   Flow capacity in a given time period between two locations

:math:`\textcolor{red}{C_{[t]}^{DisposalCapEx}}` =                  Capital cost of constructing or expanding disposal capacity

:math:`\textcolor{red}{C_{[t]}^{PipelineCapEx}}` =                  Capital cost of constructing or expanding piping capacity

:math:`\textcolor{red}{C_{[t]}^{StorageCapEx}}` =                   Capital cost of constructing or expanding storage capacity

:math:`\textcolor{red}{C_{[t]}^{TreatmentCapEx}}` =                 Capital cost of constructing or expanding treatment capacity

:math:`\textcolor{red}{S_{p,t}^{FracDemand}}` =                     Slack variable to meet the completions water demand

:math:`\textcolor{red}{S_{p,t}^{Production}}` =                     Slack variable to process produced water production

:math:`\textcolor{red}{S_{p,t}^{Flowback}}` =                       Slack variable to process flowback water production

:math:`\textcolor{red}{S_{l,\tilde{l}}^{Pipeline Capacity}}` =              Slack variable to provide necessary pipeline capacity

:math:`\textcolor{red}{S_{s}^{StorageCapacity}}` =                  Slack variable to provide necessary storage capacity

:math:`\textcolor{red}{S_{k}^{DisposalCapacity}}` =                 Slack variable to provide necessary disposal capacity

:math:`\textcolor{red}{S_{r}^{TreatmentCapacity}}` =                 Slack variable to provide necessary treatment capacity

:math:`\textcolor{red}{S_{o}^{BeneficialResueCapacity}}` =          Slack variable to provide necessary beneficial reuse capacity


**Binary Variables**

:math:`\textcolor{red}{y_{l,\tilde{l},d,[t]}^{Pipeline}}` =     New pipeline installed between one location and another location with specific diameter

:math:`\textcolor{red}{y_{s,c,[t]}^{Storage}}` =        New or additional storage facility installed at storage site with specific storage capacity

:math:`**\textcolor{red}{y_{r,wt,j}^{Treatment}}**` =      New or additional treatment capacity installed at treatment site with specific treatment capacity and treatment technology

:math:`\textcolor{red}{y_{k,i,[t]}^{Disposal}}` =       New or additional disposal facility installed at disposal site with specific injection capacity

:math:`\textcolor{red}{y_{l,\tilde{l},t}^{Flow}}` =         Directional flow between two locations

:math:`\textcolor{red}{y_{o,t}^{BeneficialReuse}}` =         Beneficial reuse option selection

..
    :math:`\textcolor{red}{z_{l,\tilde{l},d,t}^{Pipeline}}` =   Timing of pipeline installation between one location and another location with specific diameter

    :math:`\textcolor{red}{z_{s,c,t}^{Storage}}` =      Timing of storage facility installation at storage site with specific storage capacity

    :math:`\textcolor{red}{z_{k,i,t}^{Disposal}}` =     Timing of disposal facility installation at disposal site with specific injection capacity

 
**Parameters**

:math:`\textcolor{green}{\gamma_{p,t}^{Completions}}` =         Completions demand at a completions site :math:`\textcolor{blue}{p}` in time period :math:`t`

:math:`\textcolor{green}{\gamma^{TotalDemand}}` =               Total water demand over the planning horizon

:math:`\textcolor{green}{\beta_{p,t}^{Production}}` =           Produced water supply forecast for a production pad :math:`\textcolor{blue}{p}` in time period :math:`t`

:math:`\textcolor{green}{\beta_{p,t}^{Flowback}}` =             Flowback supply forecast for a completions pad :math:`\textcolor{blue}{p}` in time period :math:`t`

:math:`\textcolor{green}{\beta^{TotalProd}}` =                  Total water production (production & flowback) over the planning horizon

:math:`\textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}` =            Initial pipeline capacity between two locations :math:`\textcolor{blue}{l}` and :math:`\textcolor{blue}{\tilde{l}}`

:math:`\textcolor{green}{\sigma_{k}^{Disposal}}` =              Initial disposal capacity at disposal site :math:`\textcolor{blue}{k}`

:math:`\textcolor{green}{\sigma_{s}^{Storage}}` =               Initial storage capacity at storage site :math:`\textcolor{blue}{s}`

:math:`\textcolor{green}{\sigma_{p,t}^{PadStorage}}` =          Storage capacity at completions site :math:`\textcolor{blue}{p}` in a time period :math:`t`

:math:`\textcolor{green}{\sigma_{r,wt}^{Treatment}}` =             Initial treatment capacity at treatment site :math:`\textcolor{blue}{r}` for technology :math:`\textcolor{blue}{wt}`

:math:`\textcolor{green}{\sigma_{o,t}^{BeneficialReuseMinimum}}` =     Minimum flow that must be sent to beneficial reuse option :math:`\textcolor{blue}{o}` in time period :math:`t`

:math:`\textcolor{green}{\sigma_{o,t}^{BeneficialReuse}}` =     Capacity of beneficial reuse option :math:`\textcolor{blue}{o}` in time period :math:`t`

:math:`\textcolor{green}{\sigma_{f,t}^{ExternalWater}}` =          **Availability** of externally sourced water :math:`\textcolor{blue}{f}` in time period :math:`t`

:math:`\textcolor{green}{\sigma_{p}^{Offloading,Pad}}` =        Truck offloading sourcing capacity per pad :math:`\textcolor{blue}{p}`

:math:`\textcolor{green}{\sigma_{s}^{Offloading,Storage}}` =    Truck offloading sourcing capacity per storage site :math:`\textcolor{blue}{s}`

:math:`\textcolor{green}{\sigma_{s}^{Processing,Storage}}` =    Processing (e.g. clarification) capacity at storage site :math:`\textcolor{blue}{s}`

:math:`\textcolor{green}{\sigma_{n}^{Node}}` =                  Capacity per network node :math:`\textcolor{blue}{n}`

:math:`\textcolor{green}{W_{r}^{TreatmentComponent}}` =         Water quality component treated for at treatment site :math:`\textcolor{blue}{r}`

:math:`\textcolor{green}{\epsilon_{r, wt}^{Treatment}}` =        Treatment efficiency for technology :math:`\textcolor{blue}{wt}` at treatment site :math:`\textcolor{blue}{r}`

:math:`\textcolor{green}{\epsilon_{r, wt, qc}^{TreatmentRemoval}}` =        Removal efficiency for technology :math:`\textcolor{blue}{wt}` and quality component :math:`\textcolor{blue}{qc}` at treatment site

:math:`\textcolor{green}{\epsilon_{k,t}^{DisposalOperatingCapacity}}` = Operating capacity [%] of disposal site :math:`\textcolor{blue}{k}` in time period :math:`\textcolor{blue}{t}`

:math:`\textcolor{green}{\alpha^{AnnualizationRate}}` =         Annualization Rate [%]

:math:`\textcolor{green}{\chi_{p}^{OutsideCompletionsPad}}` = Binary parameter designating the completion pads :math:`\textcolor{blue}{p}` that are outside the system

:math:`\textcolor{green}{\chi_{wt}^{DesalinationTechnology}}` = Binary parameter designating which treatment technologies are for desalination (1) and which are not (0)

:math:`\textcolor{green}{\chi_{r}^{DesalinationSites}}` = Binary parameter designating which treatment sites are for desalination (1) and which are not (0)

:math:`\textcolor{green}{\chi_{k}^{DisposalExpansionAllowed}}` = Binary parameter indicating if expansion is allowed at site :math:`\textcolor{blue}{k}`

:math:`\textcolor{green}{\omega^{EvaporationRate}}` = Evaporation rate per week

:math:`\textcolor{green}{\delta_{k,i}^{Disposal}}` =              Increments for installation/expansion of disposal capacity :math:`\textcolor{blue}{i}` at site :math:`\textcolor{blue}{k}`

:math:`\textcolor{green}{\delta_{c}^{Storage}}` =               Increments for installation/expansion of storage capacity :math:`\textcolor{blue}{c}`

:math:`\textcolor{green}{\delta_{wt, j}^{Treatment}}` =             Increments for installation/expansion of treatment capacity :math:`\textcolor{blue}{j}` for technology :math:`\textcolor{blue}{wt}`

:math:`\textcolor{green}{\delta^{Truck}}` =                     Truck capacity

:math:`\textcolor{green}{\tau_{k, i}^{Disposal}}` =                Disposal construction or expansion lead time

:math:`\textcolor{green}{\tau_{s, c}^{Storage}}` =                 Storage construction or expansion lead time

:math:`\textcolor{green}{\tau_{r, wt, j}^{Treatment}}` =                 Treatment construction or expansion lead time

:math:`\textcolor{green}{\tau_{l,\tilde{l}}^{Trucking}}` =      Drive time between two locations :math:`\textcolor{blue}{l}` and :math:`\textcolor{blue}{\tilde{l}}`

:math:`\textcolor{green}{\lambda_{s}^{Storage}}` =              Initial storage level at storage site :math:`\textcolor{blue}{c}`

:math:`\textcolor{green}{\lambda_{p}^{PadStorage}}` =           Initial storage level at completions site :math:`\textcolor{blue}{p}`

:math:`\textcolor{green}{\theta_{s}^{Storage}}` =               Terminal storage level at storage site :math:`\textcolor{blue}{s}`

:math:`\textcolor{green}{\theta_{p}^{PadStorage}}` =            Terminal storage level at completions site :math:`\textcolor{blue}{p}`

:math:`\textcolor{green}{\kappa_{k,i}^{Disposal}}` =            Disposal construction or expansion capital cost for selected capacity increment

:math:`\textcolor{green}{\kappa_{s,c}^{Storage}}` =             Storage construction or expansion capital cost for selected capacity increment

:math:`\textcolor{green}{\kappa_{r,wt,j}^{Treatment}}` =           Treatment construction or expansion capital cost for selected capacity increment


**The cost parameter for expanding or constructing new pipeline capacity is structured differently depending on model configuration settings. If the pipeline cost configuration is distance based:**

    :math:`\textcolor{green}{\kappa^{Pipeline}}` =              Pipeline construction or expansion capital cost [currency/(diameter-distance)]

    :math:`\textcolor{green}{\mu_{d}^{Pipeline}}` =             Pipeline diameter installation or expansion increments  [diameter]

    :math:`\textcolor{green}{\lambda_{l,\tilde{l}}^{Pipeline}}` =       Pipeline segment length [distance]

    :math:`\textcolor{green}{\tau^{Pipeline}}` =              Pipeline construction or expansion lead time [time/distance]

**Otherwise, if the pipeline cost configuration is capacity based:**

    :math:`\textcolor{green}{\kappa_{l,\tilde{l},d}^{Pipeline}}` =      Pipeline construction or expansion capital cost for selected diameter capacity [currency/(volume/time)]

    :math:`\textcolor{green}{\delta_{d}^{Pipeline}}` =          Increments for installation/expansion of pipeline capacity [volume/time]

    :math:`\textcolor{green}{\tau_{l,\tilde{l},d}^{Pipeline}}` =              Pipeline construction or expansion lead time [time]


:math:`\textcolor{green}{\pi_{k}^{Disposal}}` =                 Disposal operational cost

:math:`\textcolor{green}{\pi_{r, wt}^{Treatment}}` =                Treatment operational cost

:math:`\textcolor{green}{\pi_{p}^{CompletionReuse}}` =          Completions reuse operational cost

:math:`\textcolor{green}{\pi_{s}^{Storage}}` =                  Storage deposit operational cost

:math:`\textcolor{green}{\rho_{s}^{Storage}}` =                 Storage withdrawal operational credit

:math:`\textcolor{green}{\pi_{o}^{BeneficialReuse}}` =                 Processing cost for sending water to beneficial reuse

:math:`\textcolor{green}{\rho_{o}^{BeneficialReuse}}` =                 Credit for sending water to beneficial reuse

:math:`\textcolor{green}{\pi_{l,\tilde{l}}^{Pipeline}}` =               Pipeline operational cost

:math:`\textcolor{green}{\pi_{l}^{Trucking}}` =                 Trucking hourly cost (by source)

:math:`\textcolor{green}{\pi_{f}^{Sourcing}}` =                 Externally sourced water cost

:math:`\textcolor{green}{M^{Flow}}` =                           Big-M flow parameter

:math:`\textcolor{green}{M^{Concentration}}` =                  Big-M concentration parameter

:math:`\textcolor{green}{M^{FlowConcentration}}` =              Big-M flow concentration parameter

:math:`\textcolor{green}{\psi^{FracDemand}}` =                  Slack cost parameter

:math:`\textcolor{green}{\psi^{Production}}` =                  Slack cost parameter

:math:`\textcolor{green}{\psi^{Flowback}}` =                    Slack cost parameter

:math:`\textcolor{green}{\psi^{PipelineCapacity}}` =            Slack cost parameter

:math:`\textcolor{green}{\psi^{StorageCapacity}}` =             Slack cost parameter

:math:`\textcolor{green}{\psi^{DisposalCapacity}}` =            Slack cost parameter

:math:`\textcolor{green}{\psi^{TreamentCapacity}}` =            Slack cost parameter

:math:`\textcolor{green}{\psi^{BeneficialReuseCapacity}}` =     Slack cost parameter


.. _strategic_model_mathematical_program_formulation:

Strategic Model Mathematical Program Formulation
------------------------------------------------


**Objectives**

Two objective functions can be considered for the optimization of a produced water system: first, the minimization of costs, which includes operational costs associated with procurement of externally sourced water, the cost of disposal, trucking and piping produced water between well pads and treatment facilities, and the cost of storing, treating and reusing produced water. Capital costs are also considered due to infrastructure build out such as the installation of pipelines, treatment, and storage facilities. A credit for (re)using treated water is also considered, and additional slack variables are included to facilitate the identification of potential issues with input data. The second objective is the maximization of water reused which is defined as the ratio between the treated produced water that is used in completions operations and the total produced water coming to surface.

.. math::

    \min \ \textcolor{red}{C^{TotalSourced}} + \textcolor{red}{C^{TotalDisposal}} + \textcolor{red}{C^{TotalTreatment}}

        + \textcolor{red}{C^{TotalCompletionsReuse}} + \textcolor{red}{C^{TotalPiping}} + \textcolor{red}{C^{TotalStorage}}

        + \textcolor{red}{C^{TotalTrucking}} + \textcolor{red}{C^{TotalBeneficialReuse}}

        + \textcolor{green}{\alpha^{AnnualizationRate}} \cdot (\textcolor{red}{C^{DisposalCapEx}} + \textcolor{red}{C^{StorageCapEx}}

        + \textcolor{red}{C^{TreatmentCapEx}} + \textcolor{red}{C^{PipelineCapEx}}) + \textcolor{red}{C^{Slack}}

        - \textcolor{red}{R^{TotalStorage}} - \textcolor{red}{R^{TotalBeneficialReuse}}


.. math::

    \max \ \textcolor{red}{F^{TotalCompletionsReuse}} / \textcolor{green}{\beta^{TotalProd}}


**Annualization Rate Calculation:**

The annualization rate is calculated using the formula described at this website: https://www.investopedia.com/terms/e/eac.asp. 
The annualization rate takes the discount rate (rate) and the number of years the CAPEX investment is expected to be used (life) as input.

.. math::
    \textcolor{green}{\alpha^{AnnualizationRate}} = \frac{\textcolor{green}{rate}}{(1-{(1+\textcolor{green}{rate})}^{-\textcolor{green}{life}})}


**Completions Pad Demand Balance:** :math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

If the completions pad lies outside the system, the demand is optional. Otherwise, if the completions pad is within the system, completions demand must be met.
Demand can be met by trucked or piped water moved into the pad in addition to water in completions pad storage.

If :math:`\textcolor{green}{\chi_{p}^{OutsideCompletionsPad}} = 1`:

.. math::

    \textcolor{green}{\gamma_{p,t}^{Completions}}
        \geq \sum_{l \in (L-F) | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{f \in F | (f, p) \in LLA}\textcolor{red}{F_{f,p,t}^{Sourced}}
        + \sum_{l \in L | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}

        + \textcolor{red}{F_{p,t}^{PadStorageOut}} - \textcolor{red}{F_{p,t}^{PadStorageIn}} + \textcolor{red}{S_{p,t}^{FracDemand}}

Else if :math:`\textcolor{green}{\chi_{p}^{OutsideCompletionsPad}} = 0`:

.. math::

    \textcolor{green}{\gamma_{p,t}^{Completions}}
        = \sum_{l \in (L-F) | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{f \in F | (f, p) \in LLA}\textcolor{red}{F_{f,p,t}^{Sourced}}
        + \sum_{l \in L | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}

        + \textcolor{red}{F_{p,t}^{PadStorageOut}} - \textcolor{red}{F_{p,t}^{PadStorageIn}} + \textcolor{red}{S_{p,t}^{FracDemand}}


**Completions Pad Storage Balance:** :math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

Sets the storage level at the completions pad. For each completions pad and for each time period, completions pad storage is equal to storage in last time period plus water put in minus water removed. If it is the first time period, the pad storage is the initial pad storage.

For :math:`t = 1`:

.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}} = \textcolor{green}{\lambda_{p,t=1}^{PadStorage}} + \textcolor{red}{F_{p,t}^{PadStorageIn}} - \textcolor{red}{F_{p,t}^{PadStorageOut}}


For :math:`t > 1`:

.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}} = \textcolor{red}{L_{p,t-1}^{PadStorage}} + \textcolor{red}{F_{p,t}^{PadStorageIn}} - \textcolor{red}{F_{p,t}^{PadStorageOut}}


**Completions Pad Storage Capacity:** :math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

The storage at each completions pad must always be at or below its capacity in every time period.

.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}} \leq \textcolor{green}{\sigma_{p}^{PadStorage}}


**Terminal Completions Pad Storage Level:** :math:`\forall \textcolor{blue}{p \in CP}`

The storage in the last period must be at or below its terminal storage level.

.. math::

    \textcolor{red}{L_{p,t=T}^{PadStorage}} \leq \textcolor{green}{\theta_{p}^{PadStorage}}

The storage in the last period must be at or below its terminal storage level.


**Externally Sourced Water Capacity:** :math:`\forall \textcolor{blue}{f \in F}, \textcolor{blue}{t \in T}`

For each external water source and each time period, the outgoing water from the source is below the capacity.

.. math::

      \sum_{p \in P | (f, p) \in FCA}\textcolor{red}{F_{f,p,t}^{Sourced}}
      + \sum_{p \in P | (f, p) \in FCT}\textcolor{red}{F_{f,p,t}^{Trucked}}
      \leq \textcolor{green}{\sigma_{f,t}^{ExternalWater}}


**Completions Pad Truck Offloading Capacity:** :math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

For each completions pad and time period, the volume of water being trucked into the completions pad must be below the trucking offloading capacity.

.. math::

    \sum_{l \in L | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{p}^{Offloading,Pad}}


**Storage Site Truck Offloading Capacity:** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

For each storage site and each time period, the volume of water being trucked into the storage site must be below the trucking offloading capacity for that storage site.

.. math::

    \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{s}^{Offloading,Storage}}


**Storage Site Processing Capacity:** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

For each storage site and each time period, the volume of water being piped and trucked into the storage site must be less than the processing capacity for that storage site.

.. math::

    \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{s}^{Processing,Storage}}


**Production Pad Supply Balance:** :math:`\forall \textcolor{blue}{p \in PP}, \textcolor{blue}{t \in T}`

All produced water must be accounted for. For each production pad and for each time period, the volume of outgoing water must be equal to the forecasted produced water for the production pad.

.. math::

    \textcolor{green}{\beta_{p,t}^{Production}}
        = \sum_{l \in L | (p, l) \in LLA}\textcolor{red}{F_{p,l,t}^{Piped}}
        + \sum_{l \in L | (p, l) \in LLT}\textcolor{red}{F_{p,l,t}^{Trucked}}
        + \textcolor{red}{S_{p,t}^{Production}}


**Completions Pad Supply Balance (i.e. Flowback Balance):** :math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

All flowback water must be accounted for.  For each completions pad and for each time period, the volume of outgoing water must be equal to the forecasted flowback produced water for the completions pad.

.. math::

    \textcolor{green}{\beta_{p,t}^{Flowback}}
        = \sum_{l \in L | (p, l) \in LLA}\textcolor{red}{F_{p,l,t}^{Piped}}
        + \sum_{l \in L | (p, l) \in LLT}\textcolor{red}{F_{p,l,t}^{Trucked}}
        + \textcolor{red}{S_{p,t}^{Flowback}}


**Network Node Balance:** :math:`\forall \textcolor{blue}{n \in N}, \textcolor{blue}{t \in T}`

Flow balance constraint (i.e., inputs are equal to outputs). For each pipeline node and for each time period, the volume water into the node is equal to the volume of water out of the node.

.. math::

    \sum_{l \in L | (l, n) \in LLA}\textcolor{red}{F_{l,n,t}^{Piped}}
        = \sum_{l \in L | (n, l) \in LLA}\textcolor{red}{F_{n,l,t}^{Piped}}


**Bi-Directional Flow:** :math:`\forall \textcolor{blue}{l \in (L-F-O)}, \textcolor{blue}{\tilde{l} \in (L-F)}, \textcolor{blue}{(l, \tilde{l}) \in LLA}, \textcolor{blue}{(\tilde{l}, l) \in LLA}, \textcolor{blue}{t \in T}`

There can only be flow in one direction for a given pipeline arc in a given time period.

.. math::

    \textcolor{red}{y_{l,\tilde{l},t}^{Flow}}+\textcolor{red}{y_{\tilde{l},l,t}^{Flow}} = 1

.. note:: Technically the above constraint should only be enforced for truly reversible arcs (e.g. NCA and CNA); and even then it only needs to be defined once per reversible arc (e.g. NCA only and not NCA and CNA).

Flow is only allowed in a given direction if the binary indicator for that direction is "on".

.. math::

    \textcolor{red}{F_{l,\tilde{l},t}^{Piped}} \leq \textcolor{red}{y_{l,\tilde{l},t}^{Flow}} \cdot \textcolor{green}{M^{Flow}}


**Storage Site Balance:** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

For each storage site and for each time period, if it is the first time period, the storage level is determined by the initial storage and storage inputs and outputs.
Otherwise, the storage level is determined by the storage level in the previous time period and storage inputs and outputs.
Water outputs include other system nodes (i.e., pipeline nodes and completions pads) and an evaporation stream.

For :math:`t = 1`:

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}
        = \textcolor{green}{\lambda_{s,t=1}^{Storage}}
        + \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        - \sum_{l \in L | (s, l) \in LLA}\textcolor{red}{F_{s,l,t}^{Piped}}
        - \sum_{l \in L | (s, l) \in LLT}\textcolor{red}{F_{s,l,t}^{Trucked}}
        - \textcolor{red}{F_{s,t}^{StorageEvaporationStream}}

For :math:`t > 1`:

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}
        = \textcolor{red}{L_{s,t-1}^{Storage}}
        + \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        - \sum_{l \in L | (s, l) \in LLA}\textcolor{red}{F_{s,l,t}^{Piped}}
        - \sum_{l \in L | (s, l) \in LLT}\textcolor{red}{F_{s,l,t}^{Trucked}}
        - \textcolor{red}{F_{s,t}^{StorageEvaporationStream}}

**Terminal Storage Level:** :math:`\forall \textcolor{blue}{s \in S}`

For each storage site, the storage in the last time period must be less than or equal to the predicted/set terminal storage level.

.. math::

    \textcolor{red}{L_{s,t=T}^{Storage}} \leq \textcolor{green}{\theta_{s}^{Storage}}


**Network Node Capacity:** :math:`\forall \textcolor{blue}{n \in N}, \textcolor{blue}{t \in T}`

Flow capacity constraint. For each pipeline node and for each time period, the volume should not exceed the node capacity.

.. math::

    \sum_{l \in L | (l, n) \in LLA}\textcolor{red}{F_{l,n,t}^{Piped}}
        \leq \textcolor{green}{\sigma_{n}^{Node}}


**Pipeline Capacity Construction/Expansion:**

Sets the flow capacity in a given pipeline during a given time period. The set :math:`\textcolor{blue}{D}` should also include the 0th case (e.g. 0 bbl/day) that indicates the choice to not expand capacity.
Different constraints apply based on whether a pipeline is allowed to reverse flows at any time. Thus, the following constraint applies to all pipelines that allow reversible flows:

:math:`\forall \textcolor{blue}{(l,\tilde{l}) \in LLA}, \textcolor{blue}{(\tilde{l}, l) \in LLA}, [\textcolor{blue}{t \in T}]`

.. math::

    \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}} = \textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}+\textcolor{green}{\sigma_{\tilde{l}, l}^{Pipeline}}+\sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot (\textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}+\textcolor{red}{y_{\tilde{l},l,d}^{Pipeline}} )+\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}}

The following constraint applies to all pipelines that do not allow reversible flows:

:math:`\forall \textcolor{blue}{(l,\tilde{l}) \in LLA}, [\textcolor{blue}{t \in T}]`

.. math::

    \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}} = \textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}+\sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}+\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}}

.. note::

    While popuplating the input data into the spreadsheet for initial pipeline capacities, users must use the following guidelines.

    1. For uni-directional pipelines, the initial pipeline capacity must be populated only in the direction of flow else, it will be ignored by the model.

    2. For bi-directional pipelines, the initial pipeline capacity should be populated for only one of the allowable flow directions, not both. The pipeline capacities are aggregated for both directions, so the choice of direction for the capacity is irrelevant.

.. note::

    :math:`\textcolor{green}{\delta_{d}^{Pipeline}}` can be input by user or calculated. If the user chooses to calculate pipeline capacity, the parameter will be calculated by the equation below where :math:`{\textcolor{green}{\kappa_{l,\tilde{l}}}}` is Hazen-Williams constant and :math:`\omega` is Hazen-Williams exponent as per Cafaro & Grossmann (2021) and d represents the pipeline diameter as per the set :math:`\textcolor{blue}{d \in D}`.

    See equation:

    .. math::

        \textcolor{green}{\delta_{d}^{Pipeline}} = {\textcolor{green}{\kappa_{l,\tilde{l}}}} \cdot \textcolor{blue}{d}^{\omega}


:math:`\forall \textcolor{blue}{(l,\tilde{l})} \in \textcolor{blue}{LLA}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{F_{l,\tilde{l},t}^{Piped}} \leq \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}}


**Storage Capacity Construction/Expansion:** :math:`\forall \textcolor{blue}{s \in S}, [\textcolor{blue}{t \in T}]`

The following 2 constraints account for the expansion of available storage capacity or installation of storage facilities. If expansion/construction is selected, expand the capacity by the set expansion amount. The water level at the storage site must be less than this capacity. As of now, the model considers that a storage facility is expanded or built at the beginning of the planning horizon.
The set :math:`\textcolor{blue}{C}` should also include the 0th case (0 bbl) that indicates the choice to not expand capacity.

.. math::

    \textcolor{red}{X_{s,[t]}^{Capacity}} = \textcolor{green}{\sigma_{s}^{Storage}}+\sum_{c \in C}\textcolor{green}{\delta_{c}^{Storage}} \cdot \textcolor{red}{y_{s,c}^{Storage}}+\textcolor{red}{S_{s}^{StorageCapacity}}

:math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{L_{s,t}^{Storage}} \leq \textcolor{red}{X_{s,[t]}^{Capacity}}


**Disposal Capacity Construction/Expansion:** :math:`\forall \textcolor{blue}{k \in K}, [\textcolor{blue}{t \in T}]`

The following 2 constraints account for the expansion of available disposal sites or installation of new disposal sites. If expansion/construction is selected, expand the capacity by the set expansion amount. The total disposed water in a given time period must be less than this new capacity.
The set :math:`\textcolor{blue}{I}` should also include the 0th case (e.g. 0 bbl/day) that indicates the choice to not expand capacity.

.. math::

    \textcolor{red}{D_{k,[t]}^{Capacity}} = \textcolor{green}{\sigma_{k}^{Disposal}}+\sum_{i \in I}\textcolor{green}{\delta_{k,i}^{Disposal}} \cdot \textcolor{red}{y_{k,i}^{Disposal}}+\textcolor{red}{S_{k}^{DisposalCapacity}}

:math:`\forall \textcolor{blue}{k \in K}, \textcolor{blue}{t \in T}`

.. math::

    \sum_{ | l \in L | (l, k) \in LLA}\textcolor{red}{F_{l,k,t}^{Piped}}
        + \sum_{l \in L | (l, k) \in LLT}\textcolor{red}{F_{l,k,t}^{Trucked}}
        \leq \textcolor{red}{D_{k,[t]}^{Capacity}}


**Treatment Capacity Construction/Expansion:** :math:`\forall \textcolor{blue}{r \in R}`

Similarly to disposal and storage capacity construction/expansion constraints, the current treatment capacity can be expanded as required or new facilities may be installed.
The set :math:`\textcolor{blue}{J}` should also include the 0th case (e.g. 0 bbl/day) that indicates the choice to not expand capacity.

.. math::

    \sum_{wt \in WT, j \in J}
        (\textcolor{green}{\sigma_{r,wt}^{Treatment}} \cdot \textcolor{red}{y_{r,wt,j}^{Treatment}}
        + \textcolor{green}{\delta_{wt, j}^{Treatment}} \cdot \textcolor{red}{y_{r,wt,j}^{Treatment}})
        = \textcolor{red}{T_{r}^{Capacity}}


:math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{t \in T}`

.. math::

    \sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{l \in L | (l, r) \in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}}
        \leq \textcolor{red}{T_{r,[t]}^{Capacity}} + \textcolor{red}{S_{r}^{TreatmentCapacity}}


**Treatment Feed Balance:** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{t \in T}`

At a treatment facility, the inlet raw produced water is combined into a single input treatment feed.

.. math::

    \sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{l \in L | (l, r) \in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}}
        = \textcolor{red}{F_{r,t}^{TreatmentFeed}}

**Treatment Balance:** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{t \in T}`

At a treatment facility, the input treatment feed is treated and separated into treated water and residual water.

.. math::

        \textcolor{red}{F_{r,t}^{TreatmentFeed}}
        = \textcolor{red}{F_{r,t}^{ResidualWater}}
        + \textcolor{red}{F_{r,t}^{TreatedWater}}


**Residual Water:** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{wt \in WT}, \textcolor{blue}{t \in T}`

The efficiency of a treatment technology determines the amount of residual water produced, when any treatment capacity is installed (or :math:`\sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}} = 1`). 
To ensure this, we use the big-M parameter for the flow :math:`\textcolor{blue}{M^{Flow}}` that acts as a conditional switch. As a result, the two inequalities that are formulated are mentioned below:

*Residual Water LHS*

.. math::

        \textcolor{red}{F_{r,t}^{TreatmentFeed}}
        \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{Treatment}})
        - \textcolor{green}{M^{Flow}}
         \cdot (1 - \sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}})
        \leq \textcolor{red}{F_{r,t}^{ResidualWater}}

*Residual Water RHS*

.. math::
        \textcolor{red}{F_{r,t}^{TreatmentFeed}}
        \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{Treatment}})
        + \textcolor{green}{M^{Flow}}
         \cdot (1 - \sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}})
        \geq \textcolor{red}{F_{r,t}^{ResidualWater}}

The first term calculates the untreated fraction of feed. The second term is related to any treatment capacity installation i.e., if any :math:`{y_{r,wt,j}^{Treatment}} = 1`, treatment capacity is installed and equality is enforced. When no treatment capacity is installed, :math:`{y_{r,wt,j}^{Treatment}} = 0`, 
the second term is large and negative (in the LHS constraint) or large and positive (in the RHS constraint), letting the constraints to relax. 
Thus, the “two inequalities” method ensures that when treatment is installed (active), the residual water is exactly the untreated portion of the feed; when no treatment is installed (inactive), the Big-M term relaxes the constraint entirely.

**Treated and Residual Water Balances:**

For all piping or trucking arcs :math:`\textcolor{blue}{(r, l)}` immediately downstream of a treatment site :math:`\textcolor{blue}{r}`, the user must specify whether the arc carries treated water or residual water away from the treatment site. Moreover, 

*Treated Water Balance*: :math:`\forall \textcolor{blue}{r \in R} \ |` there exists at least one arc :math:`\textcolor{blue}{(r,l)}` carrying treated water away from :math:`\textcolor{blue}{r}, \ \textcolor{blue}{t \in T}`

.. math::
        \textcolor{red}{F_{r,t}^{TreatedWater}} = \sum_{l \in L | (r, l) \in LLA \text{ and } (r,l) \text{ carries treated water}} \textcolor{red}{F_{r,l,t}^{Piped}}
        + \sum_{l \in L | (r, l) \in LLT \text{ and } (r,l) \text{ carries treated water}} \textcolor{red}{F_{r,l,t}^{Trucked}}

*Residual Water Balance*: :math:`\forall \textcolor{blue}{r \in R} \ |` there exists at least one arc :math:`\textcolor{blue}{(r,l)}` carrying residual water away from :math:`\textcolor{blue}{r}, \ \textcolor{blue}{t \in T}`

.. math::
        \textcolor{red}{F_{r,t}^{ResidualWater}} = \sum_{l \in L | (r, l) \in LLA \text{ and } (r,l) \text{ carries residual water}} \textcolor{red}{F_{r,l,t}^{Piped}}
        + \sum_{l \in L | (r, l) \in LLT \text{ and } (r,l) \text{ carries residual water}} \textcolor{red}{F_{r,l,t}^{Trucked}}

.. note:: The user is not required to specify any arcs carrying away treated or residual water immedaitely downstream of a treatment site. In reality, water that enters a treatment site must eventually leave and go somewhere, but for the sake of modeling flexibility, it is not required to include such arcs. If the user chooses to omit downstream treated and/or residual water arcs for a treatment site, then the treatment site acts as a sink within the greater network model for the water which is not propagated downstream.

**Beneficial Reuse Minimum:** :math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{t \in T}`

If a beneficial reuse option is selected (:math:`\textcolor{red}{y_{o,t}^{BeneficialReuse}} = 1`), the flow to it must meet the minimum required value.

If :math:`\textcolor{green}{\sigma_{o,t}^{BeneficialReuseMinimum}} \gt 0`:

.. math::
    \textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}
    \geq \textcolor{green}{\sigma_{o,t}^{BeneficialReuseMinimum}} \cdot \textcolor{red}{y_{o,t}^{BeneficialReuse}}

**Beneficial Reuse Capacity:** :math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{t \in T}`

If a beneficial reuse option is not selected (:math:`\textcolor{red}{y_{o,t}^{BeneficialReuse}} = 0`), the flow to it must be zero. Furthermore, the specified capacities of beneficial reuse options must be respected.

It is optional to specify capacities (:math:`\textcolor{green}{\sigma_{o,t}^{BeneficialReuse}}`) for reuse options. If a capcity is provided for reuse option :math:`\textcolor{blue}{o}`:

.. math::
    \textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}
        \leq \textcolor{green}{\sigma_{o,t}^{BeneficialReuse}} \cdot \textcolor{red}{y_{o,t}^{BeneficialReuse}}
        + \textcolor{red}{S_{o}^{BeneficialReuseCapacity}}

Otherwise:

.. math::
    \textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}
        \leq \textcolor{green}{M^{Flow}} \cdot \textcolor{red}{y_{o,t}^{BeneficialReuse}}
        + \textcolor{red}{S_{o}^{BeneficialReuseCapacity}}

**Total Beneficial Reuse Volume:**

.. math::
    \textcolor{red}{F^{TotalBeneficialReuse}}
    = \sum_{t \in T} \sum_{o \in O} \textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}


**Externally Sourced Water Cost:** :math:`\forall \textcolor{blue}{f \in F}, \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

For each external water source, for each completions pad, and for each time period, the sourcing cost is equal to all output from the source times the sourcing cost.

.. math::

    \textcolor{red}{C_{f,p,t}^{Sourced}}
        = (\textcolor{red}{F_{f,p,t}^{Sourced}}
        + \textcolor{red}{F_{f,p,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{f}^{Sourcing}}

.. math::
    \textcolor{red}{C^{TotalSourced}} = \sum_{t \in T}\sum_{(f,p) \in FCA}\textcolor{red}{C_{f,p,t}^{Sourced}}


**Total Externally Sourced Volume:**

The total externally sourced volume is the sum of externally sourced water movements by truck and pipeline over all time periods, completions pads, and external water sources.

.. math::

    \textcolor{red}{F^{TotalSourced}} = \sum_{t \in T}\sum_{f \in F}\sum_{p \in CP}(\textcolor{red}{F_{f,p,t}^{Sourced}} + \textcolor{red}{F_{f,p,t}^{Trucked}})


**Disposal Cost:** :math:`\forall \textcolor{blue}{k \in K}, \textcolor{blue}{t \in T}`

For each disposal site, for each time period, the disposal cost is equal to all water moved into the disposal site multiplied by the operational disposal cost. Total disposal cost is the sum of disposal costs over all time periods and all disposal sites.

.. math::

    \textcolor{red}{C_{k,t}^{Disposal}}
       = (\sum_{(l, k) \in LLA | l \in L}\textcolor{red}{F_{l,k,t}^{Piped}}
       + \sum_{(l, k) \in LLT | l \in L}\textcolor{red}{F_{l,k,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{k}^{Disposal}}

.. math::
    \textcolor{red}{C^{TotalDisposal}} = \sum_{t \in T}\sum_{k \in K}\textcolor{red}{C_{k,t}^{Disposal}}


**Total Disposed Volume:**

Total disposed volume over all time is the sum of all piped and trucked water to disposal summed over all time periods.

.. math::

    \textcolor{red}{F^{TotalDisposed}}
        = \sum_{t \in T}\sum_{k \in K}\textcolor{red}{F_{k,t}^{DisposalDestination}}


**Treatment Cost:** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{wt \in WT}, \textcolor{blue}{t \in T}`

For each treatment site, for each time period, the treatment cost is equal to all water moved to the treatment site multiplied by the operational treatment cost. But this should be true only when any treatment capacity is installed. Therefore simply writing: **

.. math::
    \textcolor{red}{C_{r,t}^{Treatment}}
        = (\sum_{(l, r) \in LLA | l \in L}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{(l, r) \in LLT | l \in L}\textcolor{red}{F_{l,r,t}^{Trucked}})
        \cdot \textcolor{green}{\pi_{r, wt}^{Treatment}}

is not sufficient. To ensure that treatment costs are only incurred when treatment capacity is installed (or :math:`\sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}} = 1`), we use the big-M parameter for the flow :math:`\textcolor{blue}{M^{Flow}}` that acts as a conditional switch. 

**Treatment Cost LHS**

.. math::

    \textcolor{red}{C_{r,t}^{Treatment}}
        \geq (\sum_{(l, r) \in LLA | l \in L}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{(l, r) \in LLT | l \in L}\textcolor{red}{F_{l,r,t}^{Trucked}}
        - \textcolor{green}{M^{Flow}}
        \cdot (1 - \sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}}))
        \cdot \textcolor{green}{\pi_{r, wt}^{Treatment}}

**Treatment Cost RHS**

.. math::

    \textcolor{red}{C_{r,t}^{Treatment}}
        \leq (\sum_{(l, r) \in LLA | l \in L}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{(l, r) \in LLT | l \in L}\textcolor{red}{F_{l,r,t}^{Trucked}}
        + \textcolor{green}{M^{Flow}}
        \cdot (1 - \sum_{j \in J}\textcolor{red}{y_{r,wt,j}^{Treatment}}))
        \cdot \textcolor{green}{\pi_{r, wt}^{Treatment}}

The total treatments cost is the sum of treatment costs over all time periods and all treatment sites.

.. math::
    \textcolor{red}{C^{TotalTreatment}} = \sum_{t \in T}\sum_{r \in R}\textcolor{red}{C_{r,t}^{Treatment}}


**Completions Reuse Cost:** :math:`\forall \textcolor{blue}{p \in P}, \textcolor{blue}{t \in T}`

Completions reuse water is all water that meets completions pad demand, excluding externally sourced water. Completions reuse cost is the volume of completions reused water multiplied by the cost for reuse.

.. math::

    \textcolor{red}{C_{p,t}^{CompletionsReuse}}
        = (\sum_{l \in L | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{l \in (L - F) | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        ) \cdot \textcolor{green}{\pi_{p}^{CompletionsReuse}}


.. note:: Externally sourced water is excluded from completions reuse costs.

.. math::

    \textcolor{red}{C^{TotalCompletionsReuse}} = \sum_{t \in T}\sum_{p \in CP}\textcolor{red}{C_{p,t}^{Reuse}}


**Total Completions Reuse Volume:**

The total reuse volume is the total volume of produced water reused, or the total water meeting completions pad demand over all time periods, excluding externally sourced water.

.. math::

    \textcolor{red}{F^{TotalCompletionsReused}}
        = \sum_{t \in T} \sum_{p \in CP}(\sum_{l \in L | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{l \in (L-F) | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}})


**Piping Cost:** :math:`\forall \textcolor{blue}{l \in (L - O - K)}, \forall \textcolor{blue}{\tilde{l} \in (L - F)}, \forall \textcolor{blue}{(l,\tilde{l}) \in LLA}, \textcolor{blue}{t \in T}`

Piping cost is the total volume of piped water multiplied by the cost for piping.

.. math::

    \textcolor{red}{C_{l,\tilde{l},t}^{Piped}}
        = (\textcolor{red}{F_{l \notin F,\tilde{l},t}^{Piped}}
        + \textcolor{red}{F_{l \in F,\tilde{l},t}^{Sourced}}) \cdot \textcolor{green}{\pi_{l,\tilde{l}}^{Pipeline}}

.. math::
    \textcolor{red}{C^{TotalPiping}} = \sum_{t \in T}\sum_{(l,\tilde{l}) \in LLA}\textcolor{red}{C_{l,\tilde{l},t}^{Piped}}


.. note:: The constraints above explicitly consider piping externally sourced water via :math:`\textcolor{blue}{FCA}` arcs.


**Storage Deposit Cost:** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

Cost of depositing into storage is equal to the total volume of water moved into storage multiplied by the storage operation cost rate.

.. math::

    \textcolor{red}{C_{s,t}^{Storage}}
        = (\sum_{(l, s) \in {LLA} | l \in L}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{(l, s) \in {LLT} | l \in L}\textcolor{red}{F_{l,s,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{s}^{Storage}}

.. math::
    \textcolor{red}{C^{TotalStorage}} = \sum_{t \in T}\sum_{s \in S}\textcolor{red}{C_{s,t}^{Storage}}


**Storage Withdrawal Credit:** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{t \in T}`

Credit from withdrawing from storage is equal to the volume of water moved out from storage multiplied by the storage operation credit rate.

.. math::
    \textcolor{red}{R_{s,t}^{Storage}}
        = (\sum_{(s, l) \in LLA | l \in L}\textcolor{red}{F_{s,l,t}^{Piped}}
        + \sum_{(s, l) \in LLT | l \in L}\textcolor{red}{F_{s,l,t}^{Trucked}}) \cdot \textcolor{green}{\rho_{s}^{Storage}}

.. math::
    \textcolor{red}{R^{TotalStorage}} = \sum_{t \in T}\sum_{s \in S}\textcolor{red}{R_{s,t}^{Storage}}


**Beneficial Reuse Cost:** :math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{t \in T}`

Processing cost for sending water to beneficial reuse is equal to the volume of water sent to beneficial reuse multiplied by the beneficial reuse cost rate.

.. math::
    \textcolor{red}{C_{o,t}^{BeneficialReuse}}
        = (\sum_{(l, o) \in LLA | l \in L}\textcolor{red}{F_{l,o,t}^{Piped}}
        + \sum_{(l, o) \in LLT | l \in L}\textcolor{red}{F_{l,o,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{o}^{BeneficialReuse}}

.. math::
    \textcolor{red}{C^{TotalBeneficialReuse}} = \sum_{t \in T}\sum_{o \in O}\textcolor{red}{C_{o,t}^{BeneficialReuse}}

**Beneficial Reuse Credit:** :math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{t \in T}`

Credit for sending water to beneficial reuse is equal to the volume of water sent to beneficial reuse multiplied by the beneficial reuse credit rate.

.. math::
    \textcolor{red}{R_{o,t}^{BeneficialReuse}}
        = (\sum_{(l, o) \in LLA | l \in L}\textcolor{red}{F_{l,o,t}^{Piped}}
        + \sum_{(l, o) \in LLT | l \in L}\textcolor{red}{F_{l,o,t}^{Trucked}}) \cdot \textcolor{green}{\rho_{o}^{BeneficialReuse}}

.. math::
    \textcolor{red}{R^{TotalBeneficialReuse}} = \sum_{t \in T}\sum_{o \in O}\textcolor{red}{R_{o,t}^{BeneficialReuse}}

..
    **Pad Storage Cost:** :math:`\forall \textcolor{blue}{l \in L}, \textcolor{blue}{\tilde{l} \in L}, \textcolor{blue}{t \in T}`

**Trucking Cost (Simplified)** :math:`\forall \textcolor{blue}{(l,\tilde{l}) \in LLT}, [\textcolor{blue}{t \in T}]`

Trucking cost between two locations for time period is equal to the trucking volume between locations in time :math:`\textcolor{blue}{t}` divided by the truck capacity [this gets # of truckloads] multiplied by the lead time between two locations and hourly trucking cost.

.. math::

    \textcolor{red}{C_{l,\tilde{l},t}^{Trucked}} = \textcolor{red}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{green}{1 / \delta^{Truck}}  \cdot\textcolor{green}{\tau_{l,\tilde{l}}^{Trucking}} \cdot \textcolor{green}{\pi_{l}^{Trucking}}

    \textcolor{red}{C^{TotalTrucking}} = \sum_{t \in T}\sum_{(l, \tilde{l}) \in LLT}\textcolor{red}{C_{l,\tilde{l},t}^{Trucked}}


.. note:: The constraints above explicitly consider trucking externally sourced water via :math:`\textcolor{blue}{FCT}` arcs.


**Total Trucking Volume:** :math:`\forall \textcolor{blue}{t \in T}`

The total trucking volume is estimated as the summation of trucking movements over all time periods and locations.

.. math::

    \textcolor{red}{F^{TotalTrucking}} = \sum_{t \in T}\sum_{(l,\tilde{l}) \in LLT}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}}


**Disposal Construction or Capacity Expansion Cost:**

Cost related to expanding or constructing new disposal capacity. Takes into consideration capacity increment, cost for selected capacity increment, and if the construction/expansion is selected to occur.

.. math::

    \textcolor{red}{C^{DisposalCapEx}} = \sum_{i \in I} \sum_{k \in K}\textcolor{green}{\kappa_{k,i}^{Disposal}} \cdot\textcolor{green}{\delta_{k,i}^{Disposal}} \cdot \textcolor{red}{y_{k,i}^{Disposal}}


**Storage Construction or Capacity Expansion Cost:**

Cost related to expanding or constructing new storage capacity. Takes into consideration capacity increment, cost for selected capacity increment, and if the construction/expansion is selected to occur.

.. math::

    \textcolor{red}{C^{StorageCapEx}} = \sum_{s \in S} \sum_{c \in C}\textcolor{green}{\kappa_{s,c}^{Storage}} \cdot \textcolor{green}{\delta_{c}^{Storage}} \cdot \textcolor{red}{y_{s,c}^{Storage}}


**Treatment Construction or Capacity Expansion Cost:**

Cost related to expanding or constructing new treatment capacity. Takes into consideration capacity increment, cost for selected capacity increment, and if the construction/expansion is selected to occur.

.. math::

    \textcolor{red}{C^{TreatmentCapEx}} = \sum_{r \in R}\sum_{j \in J}\sum_{wt \in WT}\textcolor{green}{\kappa_{r,wt,j}^{Treatment}} \cdot \textcolor{green}{\delta_{wt, j}^{Treatment}} \cdot \textcolor{red}{y_{r,wt,j}^{Treatment}}


**Pipeline Construction or Capacity Expansion Cost:**

Cost related to expanding or constructing new pipeline capacity is calculated differently depending on model configuration settings.


If the pipeline cost configuration is **capacity based**, pipeline expansion cost is calculated using capacity increments, cost for selected capacity increment, and if the construction/expansion is selected to occur.

.. math::

    \textcolor{red}{C^{PipelineCapEx}} = \sum_{l \in L}\sum_{\tilde{l} \in L}\sum_{d \in D}\textcolor{green}{\kappa_{l,\tilde{l},d}^{Pipeline}} \cdot \textcolor{green}{\delta_{d}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}

If the pipeline cost configuration is **distance based**, pipeline expansion cost is calculated using pipeline distances, pipeline diameters, cost per inch mile, and if the construction/expansion is selected to occur.

.. math::

    \textcolor{red}{C^{PipelineCapEx}} = \sum_{l \in L}\sum_{\tilde{l} \in L}\sum_{d \in D}\textcolor{green}{\kappa^{Pipeline} \cdot }\textcolor{green}{\mu_{d}^{Pipeline}} \cdot \textcolor{green}{\lambda_{l,\tilde{l}}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}

**Seismic Response Area - Disposal Operating Capacity Reduction:** :math:`\forall \textcolor{blue}{k \in K} \textcolor{blue}{t \in T}`

Seismic Response Areas (SRAs) can reduce the operating capacity at disposal wells. The operating capacity is set by the full built capacity and the max percentage of
capacity the disposal site is allowed to use.

.. math::

    \textcolor{red}{F_{k,t}^{DisposalDestination}} \leq \textcolor{green}{\epsilon_{k,t}^{DisposalOperatingCapacity}} \cdot \textcolor{red}{D_{k}^{Capacity}}

**Slack Costs:**

Weighted sum of the slack variables. In the case that the model is infeasible, these slack variables are used to determine where the infeasibility occurs (e.g. pipeline capacity is not sufficient).

.. math::

    \textcolor{red}{C^{Slack}}
        = \sum_{p \in CP}\sum_{t \in T}\textcolor{red}{S_{p,t}^{FracDemand}} \cdot \textcolor{green}{\psi^{FracDemand}}
        + \sum_{p \in PP}\sum_{t \in T}\textcolor{red}{S_{p,t}^{Production}} \cdot \textcolor{green}{\psi^{Production}}

        + \sum_{p \in CP}\sum_{t \in T}\textcolor{red}{S_{p,t}^{Flowback}} \cdot \textcolor{green}{\psi^{Flowback}}
        + \sum_{(l, \tilde{l}) \in LLA}\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}} \cdot \textcolor{green}{\psi^{PipeCapacity}}

        + \sum_{s \in S}\textcolor{red}{S_{s}^{StorageCapacity}} \cdot \textcolor{green}{\psi^{StorageCapacity}}
        + \sum_{k \in K}\textcolor{red}{S_{k}^{DisposalCapacity}} \cdot \textcolor{green}{\psi^{DisposalCapacity}}

        + \sum_{r \in R}\textcolor{red}{S_{r}^{TreatmentCapacity}} \cdot \textcolor{green}{\psi^{TreatmentCapacity}}
        + \sum_{o \in O}\textcolor{red}{S_{o}^{BeneficialReuseCapacity}} \cdot \textcolor{green}{\psi^{BeneficialReuseCapacity}}

**Logic Constraints:**

New pipeline or facility capacity constraints: e.g., only one injection capacity can be used for a given site.
The sets for capacity sizes may include the 0th case (e.g., 0 bbl) that indicates the choice to not expand capacity.

:math:`\forall \textcolor{blue}{k \in K}`

.. math::

    \sum_{i \in I}\textcolor{red}{y_{k,i,[t]}^{Disposal}} \leq 1

:math:`\forall \textcolor{blue}{s \in S}`

.. math::

    \sum_{c \in C}\textcolor{red}{y_{s,c,[t]}^{Storage}} \leq 1

:math:`\forall \textcolor{blue}{(l,\tilde{l}) \in LLA}`

.. math::

    \sum_{d \in D}\textcolor{red}{y_{l,\tilde{l},d,[t]}^{Pipeline}} \leq 1

:math:`\forall \textcolor{blue}{r \in R}`

.. math::

    \sum_{j \in J} \sum_{wt \in WT}\textcolor{red}{y_{r,wt,j}^{Treatment}} \leq 1


**Logic Constraints for Desalination:**

If a treatment site is specified for desalination, then non-desalination (clean brine) technology cannot be selected there.


:math:`\forall \textcolor{blue}{r \in R}`

if :math:`\textcolor{green}{\chi_{r}^{DesalinationSite}}`

.. math::

    \sum_{wt \in WT | \textcolor{green}{\chi_{wt}^{DesalinationTechnology}=0}} \sum_{j \in J} \textcolor{red}{y_{r,wt,j}^{Treatment}} = 0


If a treatment site is specified for clean brine (non-desalination), then desalination technology cannot be selected there.


:math:`\forall \textcolor{blue}{r \in R}`

if NOT :math:`\textcolor{green}{\chi_{r}^{DesalinationSite}}`

.. math::

    \sum_{wt \in WT | \textcolor{green}{\chi_{wt}^{DesalinationTechnology}=1}} \sum_{j \in J} \textcolor{red}{y_{r,wt,j}^{Treatment}} = 0


**Evaporation Flow Constraint**
Evaporation flow for a given time period and storage site is 0 if it is the first time period. Otherwise, evaporation
is a constant flow set by the parameter :math:`\textcolor{green}{\omega^{EvaporationRate}}`.

For :math:`t = 1`:

.. math::
    \textcolor{red}{F_{s,t}^{StorageEvaporationStream}} = 0

For :math:`t > 1`:

.. math::
    \textcolor{red}{F_{s,t}^{StorageEvaporationStream}} = \textcolor{green}{\omega^{EvaporationRate}} \cdot
        \sum_{j \in J, r \in R | (r,s) \in RSA} \textcolor{red}{y_{r,'CB-EV',j}^{Treatment}}

**Deliveries Destination Constraints:**

Completions reuse deliveries at a completions pad in time period :math:`\textcolor{blue}{t}` is equal to all piped and trucked water moved into the completions pad, excluding externally sourced water.
:math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{F_{p,t}^{CompletionsReuseDestination}}
        = \sum_{l \in L | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{l \in (L-F) | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        \textcolor{red}{+ F_{p,t}^{PadStorageIn}}
        \textcolor{red}{- F_{p,t}^{PadStorageOut}}

Disposal deliveries for disposal site :math:`\textcolor{blue}{k}` at time :math:`\textcolor{blue}{t}` is equal to all piped and trucked water moved to the disposal site :math:`\textcolor{blue}{k}`.
:math:`\forall \textcolor{blue}{k \in K}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{F_{k,t}^{DisposalDestination}}
        = \sum_{l \in L | (l, k) \in LLA}\textcolor{red}{F_{l,k,t}^{Piped}}
        + \sum_{l \in L | (l, k) \in LLT}\textcolor{red}{F_{l,k,t}^{Trucked}}

Beneficial reuse deliveries for beneficial reuse site :math:`\textcolor{blue}{o}` at time :math:`\textcolor{blue}{t}` is equal to all piped and trucked water moved to the beneficial reuse site :math:`\textcolor{blue}{o}`.
:math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}
        = \sum_{l \in L | (l, o) \in LLA}\textcolor{red}{F_{l,o,t}^{Piped}}
        + \sum_{l \in L | (l, o) \in LLT}\textcolor{red}{F_{l,o,t}^{Trucked}}

Completions deliveries destination for completions pad :math:`\textcolor{blue}{p}` at time :math:`\textcolor{blue}{t}` is equal to all piped and trucked water moved to the completions pad.
:math:`\forall \textcolor{blue}{p \in CP}, \textcolor{blue}{t \in T}`

.. math::

    \textcolor{red}{F_{p,t}^{CompletionsDestination}}
        = \sum_{l \in (L-F) | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{f \in F | (f, p) \in FCA}\textcolor{red}{F_{f,p,t}^{Sourced}}

        + \sum_{l \in (L-F) | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        + \sum_{f \in F | (f, p) \in FCT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        \textcolor{red}{- F_{p,t}^{PadStorageOut}} \textcolor{red}{+ F_{p,t}^{PadStorageIn}}


.. _strategic_model_water_quality_extension:

Strategic Model Water Quality Extension
---------------------------------------------------
An extension to this strategic optimization model measures the water quality across all locations over time. As of now, water quality is not a decision variable. It is calculated after optimization of the strategic model.
The process for calculating water quality is as follows: the strategic model is first solved to optimality, water quality variables and constraints are added, flow rates and storage levels are fixed to the solved values at optimality, and the water quality is calculated.

.. note:: Fixed variables are colored purple in the documentation.

Assumptions:

* Water quality of produced water from production pads and completions pads remains the same across all time periods
* When blending flows of different water quality, they blend linearly

**Water Quality Sets**

:math:`\textcolor{blue}{qc \in QC}`                       Water Quality Components (e.g., TDS)

:math:`\textcolor{blue}{p^{IntermediateNode} \in CP}`   Intermediate Completions Pad Nodes

:math:`\textcolor{blue}{p^{PadStorage} \in CP}`         Pad Storage

:math:`\textcolor{blue}{r^{TreatedWaterNodes} \in R}`         Treated Water Nodes

:math:`\textcolor{blue}{r^{ResidualWaterNodes} \in R}`         Residual Water Nodes


**Water Quality Parameters**

:math:`\textcolor{green}{\nu_{p,qc,[t]}}` =                Water quality at well pad

:math:`\textcolor{green}{\nu_{f,qc,[t]}}` =                Water quality of externally sourced water

:math:`\textcolor{green}{\xi_{s,qc}^{StorageSite}}` =    Initial water quality at storage

:math:`\textcolor{green}{\xi_{p,qc}^{PadStorage}}` =     Initial water quality at pad storage


**Water Quality Variables**

:math:`\textcolor{red}{Q_{l,qc,t}}` =                    Water quality at location


**Disposal Site Water Quality** :math:`\forall \textcolor{blue}{k \in K}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality of disposed water is dependent on the flow rates into the disposal site and the quality of each of these flows.

.. math::

    \sum_{n \in N | (n, k) \in NKA}\textcolor{purple}{F_{n,k,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}
        + \sum_{s \in S | (s, k) \in SKA}\textcolor{purple}{F_{s,k,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}
        + \sum_{r \in R | (r, k) \in RKA}\textcolor{purple}{F_{r,k,t}^{Piped}} \cdot \textcolor{red}{Q_{r,qc,t}}

        + \sum_{s \in S | (s, k) \in SKT}\textcolor{purple}{F_{s,k,t}^{Trucked}} \cdot \textcolor{red}{Q_{s,qc,t}}
        + \sum_{p \in P | (p, k) \in PKT}\textcolor{purple}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        + \sum_{p \in P | (p, k) \in CKT}\textcolor{purple}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}
        + \sum_{r \in R | (r, k) \in RKT}\textcolor{purple}{F_{r,k,t}^{Trucked}} \cdot \textcolor{red}{Q_{r,qc,t}}

        = \textcolor{purple}{F_{k,t}^{DisposalDestination}} \cdot \textcolor{red}{Q_{k,qc,t}}

**Storage Site Water Quality** :math:`\forall \textcolor{blue}{s \in S}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at storage sites is dependent on the flow rates into the storage site, the volume of water in storage in the previous time period, and the quality of each of these flows. Even mixing is assumed, so all outgoing flows have the same water quality. If it is the first time period, the initial storage level and initial water quality, respectively, replace the water stored and water quality in the previous time period.

For :math:`t = 1`:

.. math::

    \textcolor{green}{\lambda_{s,t=1}^{Storage}} \cdot \textcolor{green}{\xi_{s,qc}^{StorageSite}} 
        + \sum_{n \in N | (n, s) \in NSA}\textcolor{purple}{F_{n,s,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}

        + \sum_{r \in R | (r, s) \in RSA}\textcolor{purple}{F_{r,s,t}^{Piped}} \cdot \textcolor{red}{Q_{r,qc,t}}
        + \sum_{p \in P | (p, s) \in PST}\textcolor{purple}{F_{p,s,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}
        + \sum_{p \in P | (p, s) \in CST}\textcolor{purple}{F_{p,s,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        = \textcolor{red}{Q_{s,qc,t}} \cdot (\textcolor{purple}{L_{s,t}^{Storage}}
        + \sum_{n \in N | (s, n) \in SNA}\textcolor{purple}{F_{s,n,t}^{Piped}}
        + \sum_{p \in P | (s, p) \in SCA}\textcolor{purple}{F_{s,p,t}^{Piped}}
        + \sum_{k \in K | (s, k) \in SKA}\textcolor{purple}{F_{s,k,t}^{Piped}}

        + \sum_{r \in R | (s, r) \in SRA}\textcolor{purple}{F_{s,r,t}^{Piped}}
        + \sum_{o \in O | (s, o) \in SOA}\textcolor{purple}{F_{s,o,t}^{Piped}}
        + \sum_{p \in P | (s, p) \in SCT}\textcolor{purple}{F_{s,p,t}^{Trucked}}
        + \sum_{k \in K | (s, k) \in SKT}\textcolor{purple}{F_{s,k,t}^{Trucked}}
        + \textcolor{purple}{F_{s,t}^{StorageEvaporationStream}})

For :math:`t > 1`:

.. math::

    \textcolor{purple}{L_{s,t-1}^{Storage}} \cdot \textcolor{red}{Q_{s,qc,t-1}}
        + \sum_{n \in N | (n, s) \in NSA}\textcolor{purple}{F_{n,s,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}

        + \sum_{r \in R | (r, s) \in RSA}\textcolor{purple}{F_{r,s,t}^{Piped}} \cdot \textcolor{red}{Q_{r,qc,t}}
        + \sum_{p \in P | (p, s) \in PST}\textcolor{purple}{F_{p,s,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}
        + \sum_{p \in P | (p, s) \in CST}\textcolor{purple}{F_{p,s,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        = \textcolor{red}{Q_{s,qc,t}} \cdot (\textcolor{purple}{L_{s,t}^{Storage}}
        + \sum_{n \in N | (s, n) \in SNA}\textcolor{purple}{F_{s,n,t}^{Piped}}
        + \sum_{p \in P | (s, p) \in SCA}\textcolor{purple}{F_{s,p,t}^{Piped}}
        + \sum_{k \in K | (s, k) \in SKA}\textcolor{purple}{F_{s,k,t}^{Piped}}

        + \sum_{r \in R | (s, r) \in SRA}\textcolor{purple}{F_{s,r,t}^{Piped}}
        + \sum_{o \in O | (s, o) \in SOA}\textcolor{purple}{F_{s,o,t}^{Piped}}
        + \sum_{p \in P | (s, p) \in SCT}\textcolor{purple}{F_{s,p,t}^{Trucked}}
        + \sum_{k \in K | (s, k) \in SKT}\textcolor{purple}{F_{s,k,t}^{Trucked}}
        + \textcolor{purple}{F_{s,t}^{StorageEvaporationStream}})

**Treatment Feed Water Quality** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at treatment sites is dependent on the flow rates and qualities of the feed streams into the treatment site. Even mixing is assumed in calculating the quality of the combined feed stream.

.. math::

        \sum_{n \in N | (n, r) \in NRA}\textcolor{purple}{F_{n,r,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}
        + \sum_{s \in S | (s, r) \in SRA}\textcolor{purple}{F_{s,r,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}

        + \sum_{p \in P | (p, r) \in PRT}\textcolor{purple}{F_{p,r,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}
        + \sum_{p \in P | (p, r) \in CRT}\textcolor{purple}{F_{p,r,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        = \textcolor{red}{Q_{r,qc,t}} \cdot
         \textcolor{purple}{F_{r,t}^{TreatmentFeed}}


**Treated Water Quality** :math:`\forall \textcolor{blue}{r \in R}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

All treated water from a single treatment site and single time period will have the same water quality. The following constraints allow us to
easily track the water quality at treated water end points like desalinated water.

*Treated Water Quality General Constraint*

.. math::

        \textcolor{red}{Q_{r,qc,t}} \cdot \textcolor{purple}{F_{r,t}^{TreatmentFeed}}
        = \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}} \cdot
        \textcolor{purple}{F_{r,t}^{TreatedWater}}
        + \textcolor{red}{Q_{r^{ResidualWaterNodes},qc,t}} \cdot \textcolor{purple}{F_{r,t}^{ResidualWater}}

*Treated Water Quality Concentration-Based LHS Constraint*

.. math::

    \textcolor{red}{Q_{r,qc,t}} \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{TreatmentRemoval}})
    + \textcolor{green}{M^{Concentration}}
     \cdot (1 - \sum_{j \in J}\textcolor{purple}{y_{r,wt,j}^{Treatment}})
    \geq \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}}

*Treated Water Quality Concentration-Based RHS Constraint*

.. math::

    \textcolor{red}{Q_{r,qc,t}} \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{TreatmentRemoval}})
    - \textcolor{green}{M^{Concentration}}
     \cdot (1 - \sum_{j \in J}\textcolor{purple}{y_{r,wt,j}^{Treatment}})
    \leq \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}}

*Treated Water Quality Load-Based LHS Constraint*

.. math::

    \textcolor{red}{Q_{r,qc,t}} \cdot \textcolor{purple}{F_{r,t}^{TreatmentFeed}} \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{TreatmentRemoval}})
    + \textcolor{green}{M^{FlowConcentration}}
     \cdot (1 - \sum_{j \in J}\textcolor{purple}{y_{r,wt,j}^{Treatment}})
    \geq \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}} \cdot \textcolor{purple}{F_{r,t}^{TreatedWater}}

*Treated Water Quality Load-Based RHS Constraint*

.. math::

    \textcolor{red}{Q_{r,qc,t}} \cdot \textcolor{purple}{F_{r,t}^{TreatmentFeed}} \cdot (1 - \textcolor{green}{\epsilon_{r, wt}^{TreatmentRemoval}})
    - \textcolor{green}{M^{FlowConcentration}}
     \cdot (1 - \sum_{j \in J}\textcolor{purple}{y_{r,wt,j}^{Treatment}})
    \leq \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}} \cdot \textcolor{purple}{F_{r,t}^{TreatedWater}}



**Network Node Water Quality** :math:`\forall \textcolor{blue}{n \in N}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at nodes is dependent on the flow rates into the node and the water quality of the flows. Even mixing is assumed, so all outgoing flows have the same water quality.

.. math::

    \sum_{p \in P | (p, n) \in PNA}\textcolor{purple}{F_{p,n,t}^{Piped}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}
        + \sum_{p \in P | (p, n) \in CNA}\textcolor{purple}{F_{p,n,t}^{Piped}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        + \sum_{\tilde{n} \in N | (\tilde{n}, n) \in NNA}\textcolor{purple}{F_{\tilde{n},n,t}^{Piped}} \cdot \textcolor{red}{Q_{\tilde{n},qc,t}}
        + \sum_{s \in S | (s, n) \in SNA}\textcolor{purple}{F_{s,n,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}

        + \sum_{r \in R | (r, n) \in RNA}\textcolor{purple}{F_{r,n,t}^{Piped}} \cdot \textcolor{red}{Q_{r,qc,t}}

        = \textcolor{red}{Q_{n,qc,t}} \cdot
         (\sum_{\tilde{n} \in N | (n, \tilde{n}) \in NNA}\textcolor{purple}{F_{n,\tilde{n},t}^{Piped}}
        + \sum_{p \in P | (n, p) \in NCA}\textcolor{purple}{F_{n,p,t}^{Piped}}

        + \sum_{k \in K | (n, k) \in NKA}\textcolor{purple}{F_{n,k,t}^{Piped}}
        + \sum_{r \in R | (n, r) \in NRA}\textcolor{purple}{F_{n,r,t}^{Piped}}

        + \sum_{s \in S | (n, s) \in NSA}\textcolor{purple}{F_{n,s,t}^{Piped}}
        + \sum_{o \in O | (n, o) \in NOA}\textcolor{purple}{F_{n,o,t}^{Piped}})


**Completions Pad Intermediate Node Water Quality** :math:`\forall \textcolor{blue}{p \in P}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

.. admonition:: Water Quality at Completions Pads

    Water that is piped and trucked to a completions pad is mixed and split into two output streams: Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    This mixing happens at an intermediate node. Finally, water that meets completions demand comes from two inputs: The first input is output stream (1) from the intermediate step. The second is outgoing flow from the storage tank.

The water quality at the completions pad intermediate node is dependent on the flow rates of water from outside of the pad to the pad. Even mixing is assumed, so the water to storage and water to completions input have the same water quality.

.. math::

    \sum_{n \in N | (n, p) \in NCA}\textcolor{purple}{F_{n,p,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}
        + \sum_{\tilde{p} \in P | (\tilde{p}, p) \in PCA}\textcolor{purple}{F_{\tilde{p},p,t}^{Piped}} \cdot \textcolor{green}{\nu_{\tilde{p},qc,[t]}}
        + \sum_{s \in S | (s, p) \in SCA}\textcolor{purple}{F_{s,p,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}

        + \sum_{\tilde{p} \in P | (\tilde{p}, p) \in CCA}\textcolor{purple}{F_{\tilde{p},p,t}^{Piped}} \cdot \textcolor{green}{\nu_{\tilde{p},qc,[t]}}
        + \sum_{r \in R | (r, p) \in RCA}\textcolor{purple}{F_{r,p,t}^{Piped}} \cdot \textcolor{red}{Q_{r^{TreatedWaterNodes},qc,t}}
        + \sum_{f \in F | (f, p) \in FCA}\textcolor{purple}{F_{f,p,t}^{Sourced}} \cdot \textcolor{green}{\nu_{f,qc,[t]}}

        + \sum_{\tilde{p} \in P | (\tilde{p}, p) \in PCT}\textcolor{purple}{F_{\tilde{p},p,t}^{Trucked}} \cdot \textcolor{green}{\nu_{\tilde{p},qc,[t]}}
        + \sum_{s \in S | (s, p) \in SCT}\textcolor{purple}{F_{s,p,t}^{Trucked}} \cdot \textcolor{red}{Q_{s,qc,t}}
        + \sum_{\tilde{p} \in P | (\tilde{p}, p) \in CCT}\textcolor{purple}{F_{\tilde{p},p,t}^{Trucked}} \cdot \textcolor{green}{\nu_{\tilde{p},qc,[t]}}

        + \sum_{f \in F | (f, p) \in FCT}\textcolor{purple}{F_{f,p,t}^{Trucked}} \cdot \textcolor{green}{\nu_{f,qc,[t]}}
        = \textcolor{red}{Q_{p^{IntermediateNode},qc,t}} \cdot (\textcolor{purple}{F_{p,t}^{PadStorageIn}}
        + \textcolor{purple}{F_{p,t}^{CompletionsDestination}})


**Completions Pad Input Node Water Quality** :math:`\forall \textcolor{blue}{p \in P}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at the completions pad input is dependent on the flow rates of water from pad storage and water from the intermediate node. Even mixing is assumed, so all water into the pad is of the same water quality.

.. math::

    \textcolor{purple}{F_{p,t}^{PadStorageOut}} \cdot \textcolor{red}{Q_{p^{PadStorage},qc,t}}+\textcolor{purple}{F_{p,t}^{CompletionsDestination}} \cdot \textcolor{red}{Q_{p^{IntermediateNode},qc,t}}
        = \textcolor{red}{Q_{p,qc,t}} \cdot \textcolor{green}{\gamma_{p,t}^{Completions}}


**Completions Pad Storage Node Water Quality** :math:`\forall \textcolor{blue}{p \in P}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at pad storage sites is dependent on the flow rates into the pad storage site, the volume of water in pad storage in the previous time period, and the quality of each of these flows. Even mixing is assumed, so the outgoing flow to completions pad and water in storage at the end of the period have the same water quality. If it is the first time period, the initial storage level and initial water quality, respectively, replace the water stored and water quality in the previous time period.

For :math:`t = 1`:

.. math::

    \textcolor{green}{\lambda_{s,t=1}^{PadStorage}} \cdot \textcolor{green}{\xi_{p,qc}^{PadStorage}}
        + \textcolor{purple}{F_{p,t}^{PadStorageIn}} \cdot \textcolor{red}{Q_{p^{IntermediateNode},qc}}

        = \textcolor{red}{Q_{p^{PadStorage},qc,t}} \cdot (\textcolor{purple}{L_{s,t}^{PadStorage}}
        + \textcolor{purple}{F_{p,t}^{PadStorageOut}})

For :math:`t > 1`:

.. math::

    \textcolor{purple}{L_{s,t-1}^{PadStorage}} \cdot \textcolor{red}{Q_{p^{PadStorage},qc,t-1}}
        + \textcolor{purple}{F_{p,t}^{PadStorageIn}} \cdot \textcolor{red}{Q_{p^{IntermediateNode},qc}}

        = \textcolor{red}{Q_{p^{PadStorage},qc,t}} \cdot (\textcolor{purple}{L_{s,t}^{PadStorage}}
        + \textcolor{purple}{F_{p,t}^{PadStorageOut}})


**Beneficial Reuse Water Quality** :math:`\forall \textcolor{blue}{o \in O}, \textcolor{blue}{qc \in QC}, \textcolor{blue}{t \in T}`

The water quality at beneficial reuse sites is dependent on the flow rates into the site and the water quality of the flows.

.. math::

    \sum_{n \in N | (n, o) \in NOA}\textcolor{purple}{F_{n,o,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}}
        + \sum_{s \in S | (s, o) \in SOA}\textcolor{purple}{F_{s,o,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}
        + \sum_{p \in P | (p, o) \in POT}\textcolor{purple}{F_{p,o,t}^{Trucked}} \cdot \textcolor{green}{\nu_{p,qc,[t]}}

        = \textcolor{red}{Q_{o,qc,t}} \cdot \textcolor{purple}{F_{o,t}^{BeneficialReuseDestination}}


.. _strategic_model_discrete_water_quality_extension:

Strategic Model Discrete Water Quality Extension
---------------------------------------------------
In the previous chapter a model for tracking the water quality was shown. Without fixing the flows this model is non-linear. By discretizing the number of water qualities for all locations over time we can make the model linear again.

The discretization works as follows.

Take for example this term from the Disposal Site Water Quality:

.. math::

    \textcolor{red}{F_{k,t}^{DisposalDestination}} \cdot \textcolor{red}{Q_{k,qc,t}}

Both terms are continuous, so this is non-linear.

First we introduce a set, parameter, variables and constraints

**Discrete Water Quality Sets**

:math:`\textcolor{blue}{q \in Q}`			                     Discrete Water Qualities

**Discrete Water Quality Parameters**

:math:`\textcolor{green}{Q_{qc,q}^{DiscreteQuality}}` = 	        Values for discrete Water Qualities

**Discrete Water Quality Variables**

:math:`\textcolor{red}{Z_{l,t,qc,q}}` =           Binary decision variable for which discrete quality chosen

:math:`\textcolor{red}{F_{k,t,qc,q}^{DiscreteDisposalDestination}}` =           Water injected at disposal site for each discrete quality

**Only One Discrete Quality Per Location** ∀l \in L, t \in T, qc \in QC

For each location in time only one discrete water quality can be chosen for a water quality component.

.. math::
    \sum_{(q) \in Q}\textcolor{red}{Z_{l,t,qc,q}} = 1

**Discrete Max Disposal Destination** ∀l \in L, t \in T, qc \in QC, q \in Q

For each location in time only for one discrete quality there can be water injected at the disposal site and at most the capacity for that disposal site. For all the others it is equal to zero.

.. math::

    \textcolor{red}{F_{k,t,qc,q}^{DiscreteDisposalDestination}} \leq \textcolor{green}{D_{k,[t]}^{Capacity}} \cdot \textcolor{red}{Z_{l,t,qc,q}} 

**Sum Flow Discrete Disposal Destinations is Flow Disposal Destination** ∀l \in L, t \in T, qc \in QC

For each location in time the sum of the flows for all the discrete qualities is equal to the actual flow going to the disposal site.

.. math::

    \sum_{(q) \in Q}\textcolor{red}{F_{k,t,qc,q}^{DiscreteDisposalDestination}} = \textcolor{red}{F_{k,t}^{DisposalDestination}}


We can now rewrite the non linear equation showed before to:

.. math::

    \sum_{(q) \in Q}\textcolor{red}{F_{k,t,qc,q}^{DiscreteDisposalDestination}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

Rewriting the whole constraints goes as follows:

**Disposal Site Water Quality** ∀k \in K, qc \in QC, t \in T

The water quality of disposed water is dependent on the flow rates into the disposal site and the quality of each of these flows.

.. math::

    \sum_{n \in N | (n,k) \in NKA}\textcolor{red}{F_{n,k,t}^{Piped}} \cdot \textcolor{red}{Q_{n,qc,t}} +\sum_{s \in S | (s,k) \in SKA}\textcolor{red}{F_{s,k,t}^{Piped}} \cdot \textcolor{red}{Q_{s,qc,t}}+\sum_{r \in R | (r,k) \in RKA}\textcolor{red}{F_{r,k,t}^{Piped}} \cdot \textcolor{red}{Q_{r,qc,t}}

    +\sum_{s \in S | (s,k) \in SKT}\textcolor{red}{F_{s,k,t}^{Trucked}} \cdot \textcolor{red}{Q_{s,qc,t}}+\sum_{p \in P | (p,k) \in PKT}\textcolor{red}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{v_{p,qc,[t]}}

    +\sum_{p \in P | (p,k) \in CKT}\textcolor{red}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{v_{p,qc,[t]}}+\sum_{r \in R | (r,k) \in RKT}\textcolor{red}{F_{r,k,t}^{Trucked}} \cdot \textcolor{red}{Q_{r,qc,t}}

    =\textcolor{red}{F_{k,t}^{DisposalDestination}} \cdot \textcolor{red}{Q_{k,qc,t}}

Can be rewritten as

**Discrete Disposal Site Water Quality** ∀k \in K, qc \in QC, t \in T

The water quality of disposed water is dependent on the flow rates into the disposal site and the quality of each of these flows.

.. math::

    \sum_{n \in N | (n,k) \in NKA}\sum_{(q) \in Q}\textcolor{red}{F_{n,k,t,q}^{DiscretePiped}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

    +\sum_{s \in S | (s,k) \in SKA}\sum_{(q) \in Q}\textcolor{red}{F_{s,k,t,q}^{DiscretePiped}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

    +\sum_{r \in R | (r,k) \in RKA}\sum_{(q) \in Q}\textcolor{red}{F_{r,k,t,q}^{DiscretePiped}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

    +\sum_{s \in S | (s,k) \in SKT}\sum_{(q) \in Q}\textcolor{red}{F_{s,k,t,q}^{DiscreteTrucked}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

    +\sum_{p \in P | (p,k) \in PKT}\textcolor{red}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{v_{p,qc,[t]}}

    +\sum_{p \in P | (p,k) \in CKT}\textcolor{red}{F_{p,k,t}^{Trucked}} \cdot \textcolor{green}{v_{p,qc,[t]}}
   
    +\sum_{r \in R | (r,k) \in RKT}\sum_{(q) \in Q}\textcolor{red}{F_{r,k,t,q}^{DiscreteTrucked}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

    \leq \sum_{(q) \in Q}\textcolor{red}{F_{k,t,qc,q}^{DiscreteDisposalDestination}} \cdot \textcolor{green}{Q_{qc,q}^{DiscreteQuality}}

The constraints for the DiscretePiped and DiscreteTrucked are similar to the DiscreteDisposalDestination.

.. note:: The = sign in the original constraint is changed to :math:`\leq` sign in the discretized version.

.. _strategic_model_references:

References
----------

Cafaro, D. C., & Grossmann, I. (2021). Optimal design of water pipeline networks for the development of shale gas resources. AIChE Journal, 67(1), e17058.
