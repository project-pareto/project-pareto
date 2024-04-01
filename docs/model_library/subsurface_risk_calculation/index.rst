Subsurface Risk Calculation
===========================

Overview
-----------

Subsurface risk calculation requires the following additional parameters (worksheets in the input Excel file):

- SWDSites (:math:`s`):
  List of all SWD site IDs in column A.
- SWDDeep (:math:`d`):
  Two-column table with SWD sites and their depths (0 for shallow and 1 for deep).
- SWDAveragePressure (:math:`p`):
  Two-column table with SWD sites and their average pressure/depth in vicinity of well in psi/ft.
- SWDProxPAWell (:math:`D_o`):
  Two-column table with SWD sites and their proximity to orphaned or abandoned well in miles.
- SWDProxInactiveWell (:math:`D_i`):
  Two-column table with SWD sites and their proximity to inactive/temporarily abandoned formerly producing well completed prior to 2000 in miles.
- SWDProxEQ (:math:`D_e`):
  Two-column table with SWD sites and their proximity to earthquakes greater than or equal to a magnitude of 3 in miles.
- SWDProxFault (:math:`D_f`):
  Two-column table with SWD sites and their proximity to fault in miles.
- SWDProxHpOrLpWell (:math:`P`):
  Two-column table with SWD sites and their proximity to high-pressure or low-pressure injection well in miles.
- SWDRiskFactors:
  Two-column table with subsurface risk factor names and their values. These factors are

  * orphan_well_distance_risk_factor (:math:`r_{od}`)
  * orphan_well_severity_risk_factor (:math:`r_{os}`)
  * inactive_well_distance_risk_factor (:math:`r_{id}`)
  * inactive_well_severity_risk_factor (:math:`r_{is}`)
  * EQ_distance_risk_factor (:math:`r_{ed}`)
  * EQ_severity_risk_factor (:math:`r_{ed}`)
  * fault_distance_risk_factor (:math:`r_{fd}`)
  * fault_severity_risk_factor (:math:`r_{fd}`)
  * HP_LP_distance_risk_factor (:math:`r_{pd}`)
  * HP_LP_severity_risk_factor (:math:`r_{pd}`)
  * HP_threshold (:math:`p_h`) in psi/ft
  * LP_threshold (:math:`p_l`) in psi/ft

+---------------------------------------+
| Section                               |
+=======================================+
| :ref:`normalization_of_risk_factors`  |
+---------------------------------------+
| :ref:`calculation_of_subsurface_risk` |
+---------------------------------------+

.. _normalization_of_risk_factors:

Normalization of risk factors
-----------------------------

The ten risk factors (:math:`r_\cdot`) are categorized by type of object---orphan well (subscript :math:`o`), inactive well (subscript :math:`i`), earthquake (subscript :math:`e`), fault (subscript :math:`f`), and high-/low-pressure (:math:subscript `p`)---considered in subsurface risk calculation and thresholds for high-/low-pressure are specified by HP_threshold (:math:`p_h`) and LP_threshold (:math:`p_l`). The risk factors are normalized by type of risk (:math:`\hat{r}_{\cdot\cdot}`)---distance (subscript :math:`d`) and severity (subscript :math:`s`). For example, the five distance risk factors (:math:`r_{\cdot d}`) are divided by the sum of them.

.. math::

    \bar{r}_{xd}=\frac{r_{xd}}{\sum_{y\in\{o, i, e, f, p\}}r_{yd}}\qquad\text{for }x\in\{o, i, e, f, p\}

Similarly, the five severity risk factors are divided by their sum.

.. math::

    \bar{r}_{xs}=\frac{r_{xs}}{\sum_{y\in\{o, i, e, f, p\}}r_{ys}}\qquad\text{for }x\in\{o, i, e, f, p\}

The maximum risk factor for the lowest risk (:math:`\hat{r}`) is then calculated by adding all multiplications of the distance-based risk factor and both normalized factors for each type of object.

.. math::

    \hat{r}=\sum_{x\in\{o, i, e, f, p\}}r_{xd}\bar{r}_{xd}\bar{r}_xs

.. _calculation_of_subsurface_risk:

Calculation of subsurface risk for individual SWD sites
-------------------------------------------------------

For each SWD site, if its average pressure/depth (:math:`p`) is outside the range of :math:`[p_l, p_h]`, it is excluded from further consideration. For those sites who satisfy this pressure condition, the overall subsurface risk (`r`) is calculated as follows:

.. math::

    r=1-\frac{\sum_{x\in\{o, i, e, f, p\}}r'_x}{\hat{r}}

.. math::

    r'_x=\sum_{x\in\{o, i\}}f_d(d, D_x, r_{xd})\bar{r}_{xd}+\sum_{x\in\{e, f, p\}}\min(D_x, r_{xd})

.. math::

    f_d(d, D_\cdot, r_{\cdot d})=\begin{cases}r_{\cdot d}&\text{if }d=1\text{ (deep site)}\\\min(D_\cdot, r_{\cdot d})&\text{otherwise}\end{cases}
