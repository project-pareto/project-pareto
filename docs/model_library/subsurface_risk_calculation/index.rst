Subsurface Risk Calculation
===========================

Overview
-----------

Subsurface risk calculation requires the following additional parameters (worksheets in the input Excel file):

- SWDSites (:math:`s`):
  List of all SWD site IDs in column A.
- SWDDeep (:math:`d`):
  Two-column table with SWD sites and for each, the depth category (0 for shallow and 1 for deep). Typically, "deep" is defined as deeper than the Wolfcamp formation in the Permian basin. For Texas SWDs, the top of the injection interval (to determine depth) and well locations can be found in Texas Railroad Commission (RRC) databases.
- SWDAveragePressure (:math:`p`):
  Two-column table with SWD sites and for each, the average bottomhole pressure/depth of surrounding wells in the immediate vicinity in units of psi/ft as determined for the top of the injection zone. Sources of bottomhole data include industry engineering firms and oil company records.
- SWDProxPAWell (:math:`D_o`):
  Two-column table with SWD sites and for each, its proximity to the closest orphaned or abandoned well, in miles. A list of "currently" orphaned or abandoned wells can be downloaded from the Texas RRC website and GIS software can be used to determine distances from SWD sites.
- SWDProxInactiveWell (:math:`D_i`):
  Two-column table with SWD sites and for each, its proximity to the closest inactive/temporarily abandoned formerly producing well completed prior to 2000, in miles. A list of qualifying wells can be obtained by downloading and querying Texas RRC well file databases and GIS software can be used to determine distances from SWD sites.
- SWDProxEQ (:math:`D_e`):
  Two-column table with SWD sites and for each, their proximity in miles to the closest earthquake (as measured in terms of 2D surface location, not reflective of depth) with a Richter Local magnitude (ML) of 3.0 or greater. PARETO includes an API which can be used to extract necessary earthquake data (including latitude and longitude) from both the TexNet and USGS earthquake databases. See :doc:`/utilities/Earthquake_Distance`.
- SWDProxFault (:math:`D_f`):
  Two-column table with SWD sites and for each, their proximity to the closest part of the closest known fault (as determined from surface locations, not reflective of depth) in miles. Fault locations can be obtained from the Texas Railroad Commission as shapefiles. Basement faults need not be distinguished from shallow faults (basement faults are well known and publicly available, whereas shallow faults are usually held as proprietary and not generally available). Oil companies typically have their own proprietary fault databases which could also be used.
- SWDProxHpOrLpWell (:math:`P`):
  Two-column table with SWD sites and for each, its proximity in miles to the closest high-bottomhole pressure (over 0.7 psi/ft) or low-bottomhole pressure (under 0.5 psi/ft), as defined by the top of the injection interval.
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

These inputs give the user flexibility in customizing risk thresholds and weighting factors, should they so desire.

Each SWD well location is assessed for the above ten risk factors. Input risk values are normalized, and the distance and severity risk factors are multiplied with input actual values for each considered location, resulting in a weighted total aggregate risk factor for each SWD, with a high value equating to low risk, and a low value equating to high risk. The values are reversed to make them more intuitive (i.e., a high number corresponds to high risk). The final risk metric is between 0 (essentially no risk) and 1 (highest possible risk). The final risk factor for a given well is obtained by multiplying its risk factor by the injection rate for the well. That is, greater injection in any given SWD results in proportionally more overall risk.

The algorithm recognizes orphan and abandoned well risk is acute for shallow wells, but negligible for deep wells.

The distance risk factors (1.86 miles and 5.59 miles by default) should be interpreted as generally safe distances from potential risk factors: (i.e. at this distance or greater, risk from this particular concern is minimal). These distance values (input in linear miles) were taken from Texas RRC policies which publish “safe” distances from earthquakes and faults used in Texas RRC seismic risk grading algorithms, available on their web site.

The specific calculations are described below.

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

    \hat{r}=\sum_{x\in\{o, i, e, f, p\}}r_{xd}\bar{r}_{xd}\bar{r}_{xs}

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
