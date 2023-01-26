Case Studies
============

Network schematics
------------------

.. figure:: ../img/strategic_toy_network.png
    :width: 600
    :align: center
    :alt: Strategic toy case study network schematic

    Strategic toy case study network.

.. figure:: ../img/strategic_small_network.png
    :width: 1000
    :align: center
    :alt: Strategic small case study network schematic

    Strategic small case study network.

.. figure:: ../img/strategic_treatment_demo_network.png
    :width: 1000
    :align: center
    :alt: Strategic treatment demo network schematic

    Strategic treatment demo network.

Comparison table
----------------
.. |br| raw:: html

  <br/>

.. list-table::
   :header-rows: 1

   * -
     - Strategic model toy case study
     - Strategic model small case study
     - Strategic model treatment demo
     - Operational model case study
   * - **Input file**
     - ``strategic_toy_case_study.xlsx``
     - ``strategic_small_case_study.xlsx``
     - ``strategic_treatment_demo.xlsx``
     - ``operational_generic_case_study.xlsx``
   * - **Model type**
     - Strategic
     - Strategic
     - Strategic
     - Operational
   * - **Description**
     - A very small, toy-sized network. |br|
       Useful for testing and debugging.
     - Larger network, but "small" in the |br|
       sense that disposal and pipeline |br|
       expansion are not allowed, so the |br|
       model solves quickly.
     - Larger network, and disposal and |br|
       pipeline expansion are allowed. |br|
       Takes a bit longer to solve. This |br|
       can be seen as the "default" case |br|
       study for the strategic model.
     - Generic case study for the |br|
       operational model. Note that this |br|
       case study cannot currently be run |br|
       in PARETO UI - it can only be run |br|
       using the Python command line |br|
       interface.
   * - **Decision period**
     - Week
     - Week
     - Week
     - Day
   * - **Decision horizon**
     - 52 weeks
     - 52 weeks
     - 52 weeks
     - 5 days
   * - **Network nodes**
     - 9
     - 28
     - 28
     - 0
   * - **Production pads**
     - 4
     - 15
     - 14
     - 5
   * - **Production tanks**
     - N/A
     - N/A
     - N/A
     - 14
   * - **Completions pads**
     - 1
     - 4
     - 3
     - 1
   * - **External completions pads** [#]_
     - 0
     - 0
     - 1 (CP03)
     - N/A
   * - **Disposal sites (SWD)**
     - 2
     - 3
     - 5
     - 2
   * - **Disposal expansion allowed?** [#]_
     - No
     - No
     - Yes, for K03 and K05
     - No
   * - **Storage sites**
     - 1
     - 2
     - 3
     - 0
   * - **Storage expansion allowed?**
     - Yes
     - No
     - Yes
     - No
   * - **Completions pad**
     - No
     - Yes
     - No
     - Yes
   * - **Treatment sites**
     - 2 |br|
       Non-desalination site: R02 |br|
       Desalination site: R01 |br|
       Both sites have zero initial |br|
       treatment capacity
     - 2 |br|
       Both are non-desalination sites |br|
       Both sites have nonzero initial |br|
       treatment capcity
     - 6 |br|
       Non-desalination sites: R02, R04, R05 |br|
       Desalination sites: R01, R03, R06 |br|
       All sites have zero initial treatment |br|
       capacity
     - 2
   * - **Treatment technologies**
     - Non-desalination: CB, CB-EV |br|
       Desalination: MVC, MD, OARO
     - Non-desalination: CB
     - Non-desalination: CB, CB-EV |br|
       Desalination: FF, HDH
     - N/A
   * - **Treatment expansion allowed?**
     - Yes
     - Yes (but only one capacity option)
     - Yes
     - No
   * - **Pipeline expansion allowed?**
     - Yes
     - No
     - Yes
     - No
   * - **Hydraulics settings**
     - Roughness factor: 110 |br|
       Head loss: 0.03
     - Roughness factor: 110 |br|
       Head loss: 0.03
     - Roughness factor: 110 |br|
       Head loss: 0.03
     - N/A
   * - **Economics**
     - Discount rate: 8% |br|
       CAPEX lifetime: 20 years
     - Discount rate: 8% |br|
       CAPEX lifetime: 20 years
     - Discount rate: 8% |br|
       CAPEX lifetime: 20 years
     - N/A
   * - **Notes**
     -
     -
     - Recommend solving with Gurobi.
     -

.. [#] In the strategic model, external completions pads can be used to model opportunities for water sharing outside of the main network.
.. [#] In the strategic model, disposal capacity expansion is only allowed for SWD sites for which the initial disposal capacity is 0.

Abbreviations
^^^^^^^^^^^^^

* CB: Clean brine treatment
* CB-EV: Clean brine treatment with enhanced evaporation
* FF: Falling film evaporation
* HDH: Humidification-dehumidification
* MD: Membrane distillation
* MVC: Mechanical vapor compression
* OARO: Osmotically assisted reverse osmosis
* SWD: Salt water disposal
