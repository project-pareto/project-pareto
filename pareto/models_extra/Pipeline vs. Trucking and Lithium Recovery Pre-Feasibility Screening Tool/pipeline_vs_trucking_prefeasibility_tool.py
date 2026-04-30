import streamlit as st
import numpy as np
import plotly.graph_objects as go


st.set_page_config(
    page_title="Produced Water long haul Pipeline vs Trucking | Pre-Feasibility",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .stApp {
        background: linear-gradient(160deg, #0d1117 0%, #111827 60%, #0f1923 100%);
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] {
        background: #0a0f1a !important;
        border-right: 1px solid #1e3a5f;
    }

    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stNumberInput label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #dbe7f5 !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label p {
        color: #e2e8f0 !important;
        font-size: 0.98rem !important;
        font-weight: 600 !important;
        line-height: 1.45 !important;
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #cbd5e1 !important;
    }

    .header-band {
        background: linear-gradient(135deg, #0f3460 0%, #1a5276 50%, #0e6251 100%);
        border-radius: 12px;
        padding: 28px 36px;
        margin-bottom: 24px;
        border: 1px solid #1e5f74;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .header-band h1 {
        margin: 0 0 4px 0;
        font-size: 2rem;
        font-weight: 700;
        color: #f0f9ff;
        letter-spacing: -0.02em;
    }

    .header-band p {
        margin: 0;
        color: #d7f3ea;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    .section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #4cc9f0;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        border-bottom: 1px solid #1e3a5f;
        padding-bottom: 8px;
        margin: 24px 0 14px 0;
    }

    .insight-box {
        background: rgba(14,165,233,0.09);
        border-left: 3px solid #38bdf8;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        color: #d6e2ef;
        font-size: 0.90rem;
        margin: 10px 0 16px 0;
        line-height: 1.65;
    }

    .sidebar-section {
        color: #4cc9f0 !important;
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin: 18px 0 6px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #1e3a5f;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #111827;
        border-radius: 8px 8px 0 0;
        gap: 2px;
        padding: 4px;
        border: 1px solid #1e3a5f;
        border-bottom: none;
    }

    .stTabs [data-baseweb="tab"] {
        color: #dbe7f5;
        font-size: 0.88rem;
        font-weight: 700;
        padding: 8px 18px;
        border-radius: 6px;
    }

    .stTabs [aria-selected="true"] {
        background: #0f3460 !important;
        color: #e0f2fe !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background: #0d1117;
        border: 1px solid #1e3a5f;
        border-radius: 0 8px 8px 8px;
        padding: 20px;
    }

    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 14px 16px;
    }

    [data-testid="stMetric"] label {
        color: #dbe7f5 !important;
        font-size: 0.80rem !important;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.82rem !important;
    }

    .verdict-attractive, .verdict-marginal, .verdict-unattractive {
        display: inline-block;
        border-radius: 20px;
        padding: 6px 18px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    .verdict-attractive {
        background: rgba(16,185,129,0.15);
        color: #34d399;
        border: 1px solid #10b981;
    }

    .verdict-marginal {
        background: rgba(245,158,11,0.15);
        color: #fbbf24;
        border: 1px solid #f59e0b;
    }

    .verdict-unattractive {
        background: rgba(239,68,68,0.15);
        color: #f87171;
        border: 1px solid #ef4444;
    }

    .stNumberInput input {
        background: #1e2a3a !important;
        border: 1px solid #2d4a6a !important;
        color: #f1f5f9 !important;
        border-radius: 6px !important;
        font-size: 1rem !important;
    }

    hr {
        border-color: #1e3a5f !important;
        margin: 20px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Unit conversions and display settings

BBL_TO_L = 158.987
LI_TO_LCE = 5.323

COLORS = {
    "baseline": "#f87171",
    "pipeline": "#34d399",
    "lithium": "#a78bfa",
    "combined": "#38bdf8",
    "accent": "#38bdf8",
    "orange": "#fb923c",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,17,23,0.85)",
    font=dict(family="IBM Plex Sans", color="#dbe7f5", size=14),
    title_font=dict(color="#f8fafc", size=18, family="IBM Plex Sans"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0", size=13)),
    xaxis=dict(
        gridcolor="#2a4365",
        linecolor="#2a4365",
        tickfont=dict(color="#cbd5e1", size=13),
        title_font=dict(color="#e2e8f0", size=14),
    ),
    yaxis=dict(
        gridcolor="#2a4365",
        linecolor="#2a4365",
        tickfont=dict(color="#cbd5e1", size=13),
        title_font=dict(color="#e2e8f0", size=14),
    ),
    margin=dict(l=60, r=20, t=55, b=55),
)


# Formatting and finance utilities


def fmt_money(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}k"
    return f"${val:.0f}"


def fmt_num(val: float, digits: int = 1) -> str:
    return f"{val:,.{digits}f}"


def safe_payback(capex: float, annual_benefit: float):
    if annual_benefit <= 0:
        return None
    return capex / annual_benefit


def capital_recovery_factor(r: float, n: int) -> float:
    if n <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return 1.0 / n
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def npv_from_constant_cashflow(
    capex: float, annual_cashflow: float, r: float, n: int
) -> float:
    if n <= 0:
        return -capex
    if abs(r) < 1e-12:
        return -capex + annual_cashflow * n
    pv_factor = (1 - (1 + r) ** (-n)) / r
    return -capex + annual_cashflow * pv_factor


def verdict_from_payback(payback):
    if payback is None:
        return "Not Attractive Under Current Assumptions", "unattractive"
    if payback <= 5:
        return "Economically Attractive", "attractive"
    if payback <= 10:
        return "Marginal — Conduct Detailed Study", "marginal"
    return "Not Attractive Under Current Assumptions", "unattractive"


# Cost and recovery calculations


def annual_throughput(q_bpd: float) -> float:
    return q_bpd * 365.0


def calc_baseline(
    q_bpd: float,
    f_trucked: float,
    d_baseline: float,
    c_truck_mile: float,
    c_disp: float,
):
    q_annual_bbl = annual_throughput(q_bpd)
    q_trucked_annual = q_annual_bbl * f_trucked

    cost_truck_baseline = q_trucked_annual * d_baseline * c_truck_mile
    cost_disp_baseline = q_trucked_annual * c_disp
    cost_baseline_total = cost_truck_baseline + cost_disp_baseline

    return {
        "q_annual_bbl": q_annual_bbl,
        "q_trucked_annual": q_trucked_annual,
        "cost_truck_baseline": cost_truck_baseline,
        "cost_disp_baseline": cost_disp_baseline,
        "cost_baseline_total": cost_baseline_total,
    }


def calc_pipeline(
    q_trucked_annual: float,
    capex_pipe: float,
    c_pipe_opex: float,
    d_local: float,
    c_haul_mile: float,
    c_truck_mile: float,
    c_disp: float,
    d_baseline: float,
    r: float,
    n: int,
    oandm_fixed: float,
    pipeline_utilization: float,
):
    q_pipeline_annual = q_trucked_annual * pipeline_utilization
    q_residual_annual = q_trucked_annual - q_pipeline_annual

    crf = capital_recovery_factor(r, n)
    capex_annualized = capex_pipe * crf

    cost_local_gather = q_pipeline_annual * d_local * c_haul_mile
    cost_pipeline_var = q_pipeline_annual * c_pipe_opex
    cost_residual_truck = q_residual_annual * d_baseline * c_truck_mile
    cost_residual_disp = q_residual_annual * c_disp

    cost_pipeline_total = (
        capex_annualized
        + cost_local_gather
        + cost_pipeline_var
        + cost_residual_truck
        + cost_residual_disp
        + oandm_fixed
    )

    return {
        "q_pipeline_annual": q_pipeline_annual,
        "q_residual_annual": q_residual_annual,
        "crf": crf,
        "capex_annualized": capex_annualized,
        "cost_local_gather": cost_local_gather,
        "cost_pipeline_var": cost_pipeline_var,
        "cost_residual_truck": cost_residual_truck,
        "cost_residual_disp": cost_residual_disp,
        "cost_pipeline_total": cost_pipeline_total,
    }


def calc_lithium(
    q_for_lithium_annual_bbl: float,
    li_mgL: float,
    eta_li: float,
    p_lce: float,
    c_lce_proc: float,
    f_operator: float,
):
    q_annual_L = q_for_lithium_annual_bbl * BBL_TO_L
    li_mass_mg = q_annual_L * li_mgL
    li_mass_tonnes_in_brine = li_mass_mg / 1e9
    li_mass_tonnes_recovered = li_mass_tonnes_in_brine * eta_li
    lce_tonnes = li_mass_tonnes_recovered * LI_TO_LCE

    revenue_li_gross = lce_tonnes * p_lce
    cost_li_processing = lce_tonnes * c_lce_proc
    value_li_net_pre_share = revenue_li_gross - cost_li_processing
    value_li_net = value_li_net_pre_share * f_operator

    return {
        "q_annual_L": q_annual_L,
        "li_mass_tonnes_in_brine": li_mass_tonnes_in_brine,
        "li_mass_tonnes_recovered": li_mass_tonnes_recovered,
        "lce_tonnes": lce_tonnes,
        "revenue_li_gross": revenue_li_gross,
        "cost_li_processing": cost_li_processing,
        "value_li_net_pre_share": value_li_net_pre_share,
        "value_li_net": value_li_net,
    }


def calc_mvc_reverse_engineering(
    q_bpd_available: float,
    throughput_pct: float,
    mvc_pct: float,
    capex_pipe: float,
    c_pipe_opex: float,
    oandm_fixed: float,
    r: float,
    n: int,
    target_margin_pct: float,
    shortfall_penalty: float,
    candidate_tariff: float,
):
    q_available_annual = annual_throughput(q_bpd_available)
    q_actual_annual = q_available_annual * throughput_pct / 100.0
    q_mvc_annual = q_available_annual * mvc_pct / 100.0
    q_shortfall_annual = max(q_mvc_annual - q_actual_annual, 0.0)

    crf = capital_recovery_factor(r, n)
    annualized_capex = capex_pipe * crf
    variable_opex = q_actual_annual * c_pipe_opex
    annual_cost = annualized_capex + variable_opex + oandm_fixed

    target_revenue = annual_cost * (1 + target_margin_pct / 100.0)
    shortfall_revenue = q_shortfall_annual * shortfall_penalty

    if q_actual_annual > 0:
        required_tariff = max(
            (target_revenue - shortfall_revenue) / q_actual_annual, 0.0
        )
    else:
        required_tariff = None

    tariff_revenue = q_actual_annual * candidate_tariff
    total_revenue_with_candidate = tariff_revenue + shortfall_revenue
    annual_margin_with_candidate = total_revenue_with_candidate - annual_cost
    npv_with_candidate = npv_from_constant_cashflow(
        capex_pipe, total_revenue_with_candidate - variable_opex - oandm_fixed, r, n
    )
    payback_with_candidate = safe_payback(
        capex_pipe, total_revenue_with_candidate - variable_opex - oandm_fixed
    )

    return {
        "q_available_annual": q_available_annual,
        "q_actual_annual": q_actual_annual,
        "q_mvc_annual": q_mvc_annual,
        "q_shortfall_annual": q_shortfall_annual,
        "annualized_capex": annualized_capex,
        "variable_opex": variable_opex,
        "annual_cost": annual_cost,
        "target_revenue": target_revenue,
        "shortfall_revenue": shortfall_revenue,
        "required_tariff": required_tariff,
        "tariff_revenue": tariff_revenue,
        "total_revenue_with_candidate": total_revenue_with_candidate,
        "annual_margin_with_candidate": annual_margin_with_candidate,
        "npv_with_candidate": npv_with_candidate,
        "payback_with_candidate": payback_with_candidate,
    }


def calc_driver_summary(baseline_total, annual_savings, capex, lithium_net):
    drivers = []

    savings_ratio = annual_savings / baseline_total if baseline_total > 0 else 0

    if savings_ratio > 0.25:
        drivers.append(
            "High baseline trucking and disposal cost is creating strong savings potential."
        )
    elif savings_ratio > 0.10:
        drivers.append("Transport savings are meaningful, but not dominant.")
    else:
        drivers.append("Transport savings are modest relative to the baseline.")

    if capex > 5 * max(abs(annual_savings), 1):
        drivers.append("Upfront pipeline CAPEX is the main economic constraint.")
    else:
        drivers.append("CAPEX is manageable relative to annual savings.")

    if lithium_net > 0.25 * max(abs(annual_savings), 1):
        drivers.append("Lithium is a material upside driver under current assumptions.")
    elif lithium_net > 0:
        drivers.append(
            "Lithium provides incremental upside, but is not the primary value driver."
        )
    else:
        drivers.append("Lithium does not improve economics under current assumptions.")

    return drivers[:3]


# User inputs

with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:12px 0 4px;">'
        '<span style="font-size:1.5rem">💧</span>'
        '<span style="color:#0ea5e9;font-weight:700;font-size:1rem;margin-left:8px;">Produced Water Screening</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="text-align:center;color:#cbd5e1;font-size:0.72rem;margin-bottom:16px;">'
        "Pre-Feasibility Screening Tool</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown(
        '<div class="sidebar-section">Volume & Existing Operations</div>',
        unsafe_allow_html=True,
    )
    q_bpd = st.number_input(
        "Produced Water Volume (bbl/day)",
        min_value=100,
        max_value=1_000_000,
        value=20_000,
        step=1000,
    )
    f_trucked_pct = st.slider("Fraction Currently Trucked (%)", 0, 100, 80)
    d_baseline = st.number_input(
        "Baseline Long-Haul Distance (miles)",
        min_value=0.0,
        value=220.0,
        step=1.0,
        format="%.1f",
    )
    c_truck_mile = st.number_input(
        "Baseline Trucking Cost ($/bbl-mile)",
        min_value=0.0,
        value=0.03,
        step=0.005,
        format="%.3f",
    )
    c_disp = st.number_input(
        "Disposal Cost ($/bbl)", min_value=0.0, value=1.25, step=0.05, format="%.2f"
    )
    truck_capacity_bbl = st.slider("Truck Capacity (bbl/truck)", 50, 200, 130, 5)

    st.markdown(
        '<div class="sidebar-section">Pipeline Scenario</div>', unsafe_allow_html=True
    )
    capex_pipe = st.number_input(
        "Pipeline CAPEX ($)",
        min_value=100_000,
        max_value=5_000_000_000,
        value=600_000_000,
        step=500_000,
    )
    c_pipe_opex = st.number_input(
        "Pipeline OPEX ($/bbl)", min_value=0.0, value=1.00, step=0.05, format="%.2f"
    )
    d_local = st.number_input(
        "First-Mile Gathering Distance (miles)",
        min_value=0.0,
        value=20.0,
        step=0.5,
        format="%.1f",
    )
    c_haul_mile = st.number_input(
        "Local Hauling Cost ($/bbl-mile)",
        min_value=0.0,
        value=0.30,
        step=0.01,
        format="%.2f",
    )
    pipeline_utilization_pct = st.slider(
        "Pipeline Utilization of Currently Trucked Volume (%)", 0, 100, 100
    )
    f_residual_pct = 100 - pipeline_utilization_pct
    st.caption(f"Residual fraction automatically set to: {f_residual_pct}%")
    oandm_fixed = st.number_input(
        "Fixed Annual O&M ($/year)", min_value=0, value=0, step=50_000
    )

    st.markdown(
        '<div class="sidebar-section">Project Economics</div>', unsafe_allow_html=True
    )
    discount_rate_pct = st.slider("Discount Rate (%)", 0, 25, 10)
    project_life = st.slider("Project Life (years)", 1, 30, 15)

    st.markdown(
        '<div class="sidebar-section">MVC Reverse Engineering</div>',
        unsafe_allow_html=True,
    )
    mvc_available_bpd = st.number_input(
        "Available Volume to CTP (bbl/day)",
        min_value=100,
        max_value=1_000_000,
        value=6150,
        step=100,
    )
    mvc_throughput_pct = st.slider(
        "Expected Throughput to CTP (% of available)", 0, 100, 100
    )
    mvc_level_pct = st.slider("MVC Level (% of available)", 0, 150, 100)
    shortfall_penalty = st.number_input(
        "Shortfall Penalty ($/bbl)", min_value=0.0, value=0.0, step=0.10, format="%.2f"
    )
    target_margin_pct = st.slider("Target Margin on Annual Cost (%)", 0, 100, 15)
    candidate_tariff = st.number_input(
        "Candidate Tariff ($/bbl)", min_value=0.0, value=1.00, step=0.05, format="%.2f"
    )

    st.markdown(
        '<div class="sidebar-section">Lithium Recovery Module</div>',
        unsafe_allow_html=True,
    )
    li_mgL = st.number_input(
        "Lithium Concentration (mg/L)",
        min_value=0.0,
        value=80.0,
        step=5.0,
        format="%.1f",
    )
    eta_li_pct = st.slider("DLE Recovery Efficiency (%)", 0, 100, 75)
    p_lce = st.number_input(
        "LCE Price ($/tonne LCE)", min_value=0, value=18_000, step=500
    )
    c_lce_proc = st.number_input(
        "DLE Processing Cost ($/tonne LCE)", min_value=0, value=6_000, step=250
    )
    f_operator_pct = st.slider(
        "Operator / Project Share of Lithium Value (%)", 0, 100, 100
    )
    lithium_basis = st.radio(
        "Lithium Basis",
        options=[
            "Pipeline-handled volume only",
            "Currently trucked volume",
            "Total produced water volume",
        ],
        index=0,
    )

    st.divider()
    st.markdown(
        '<div style="color:#cbd5e1;font-size:0.70rem;text-align:center;line-height:1.5;">'
        "Screening estimates only.<br>Requires engineering and commercial validation."
        "</div>",
        unsafe_allow_html=True,
    )


# Input conversions

f_trucked = f_trucked_pct / 100.0
pipeline_utilization = pipeline_utilization_pct / 100.0
r = discount_rate_pct / 100.0
eta_li = eta_li_pct / 100.0
f_operator = f_operator_pct / 100.0


baseline = calc_baseline(q_bpd, f_trucked, d_baseline, c_truck_mile, c_disp)

pipeline = calc_pipeline(
    q_trucked_annual=baseline["q_trucked_annual"],
    capex_pipe=capex_pipe,
    c_pipe_opex=c_pipe_opex,
    d_local=d_local,
    c_haul_mile=c_haul_mile,
    c_truck_mile=c_truck_mile,
    c_disp=c_disp,
    d_baseline=d_baseline,
    r=r,
    n=project_life,
    oandm_fixed=oandm_fixed,
    pipeline_utilization=pipeline_utilization,
)

if lithium_basis == "Pipeline-handled volume only":
    q_for_lithium = pipeline["q_pipeline_annual"]
elif lithium_basis == "Currently trucked volume":
    q_for_lithium = baseline["q_trucked_annual"]
else:
    q_for_lithium = baseline["q_annual_bbl"]

lithium = calc_lithium(
    q_for_lithium_annual_bbl=q_for_lithium,
    li_mgL=li_mgL,
    eta_li=eta_li,
    p_lce=p_lce,
    c_lce_proc=c_lce_proc,
    f_operator=f_operator,
)

savings_pipeline_only = (
    baseline["cost_baseline_total"] - pipeline["cost_pipeline_total"]
)
benefit_combined = savings_pipeline_only + lithium["value_li_net"]

payback_pipeline = safe_payback(capex_pipe, savings_pipeline_only)
payback_combined = safe_payback(capex_pipe, benefit_combined)

npv_pipeline = npv_from_constant_cashflow(
    capex_pipe, savings_pipeline_only, r, project_life
)
npv_combined = npv_from_constant_cashflow(capex_pipe, benefit_combined, r, project_life)

trucked_bbl_displaced = baseline["q_trucked_annual"] - pipeline["q_residual_annual"]
truck_trips_displaced = (
    trucked_bbl_displaced / truck_capacity_bbl if truck_capacity_bbl > 0 else 0
)
truck_miles_avoided = truck_trips_displaced * max(d_baseline - d_local, 0)

verdict_text, verdict_cls = verdict_from_payback(payback_pipeline)
drivers = calc_driver_summary(
    baseline["cost_baseline_total"],
    savings_pipeline_only,
    capex_pipe,
    lithium["value_li_net"],
)

mvc = calc_mvc_reverse_engineering(
    q_bpd_available=mvc_available_bpd,
    throughput_pct=mvc_throughput_pct,
    mvc_pct=mvc_level_pct,
    capex_pipe=capex_pipe,
    c_pipe_opex=c_pipe_opex,
    oandm_fixed=oandm_fixed,
    r=r,
    n=project_life,
    target_margin_pct=target_margin_pct,
    shortfall_penalty=shortfall_penalty,
    candidate_tariff=candidate_tariff,
)


# HEADER

st.markdown(
    """
    <div class="header-band">
      <h1>💧 Produced Water Pipeline vs. Trucking &amp; Lithium Recovery</h1>
      <p>
        <b>Pre-Feasibility Screening Tool</b> — Compare trucking, long haul pipeline transport,
        minimum volume commitment tariff requirements, and optional lithium recovery under user-defined assumptions.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# Summary metrics

st.markdown(
    '<div class="section-header">Executive Summary</div>', unsafe_allow_html=True
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Baseline Annual Cost", fmt_money(baseline["cost_baseline_total"]))
with c2:
    st.metric("Pipeline Annual Cost", fmt_money(pipeline["cost_pipeline_total"]))
with c3:
    st.metric("Annual Savings", fmt_money(savings_pipeline_only))
with c4:
    st.metric(
        "Pipeline Payback",
        f"{payback_pipeline:.1f} yrs" if payback_pipeline else "No payback",
    )
with c5:
    st.metric("Annual Lithium Net Value", fmt_money(lithium["value_li_net"]))
with c6:
    st.metric(
        "Combined Payback",
        f"{payback_combined:.1f} yrs" if payback_combined else "No payback",
    )

badge_html = f'<span class="verdict-{verdict_cls}">{verdict_text}</span>'
st.markdown(
    f"<div style='margin:12px 0 4px;'>{badge_html}</div>", unsafe_allow_html=True
)

if payback_pipeline and payback_combined:
    reduction = payback_pipeline - payback_combined
    if reduction > 0:
        combined_delta_text = (
            f"Lithium reduces simple payback by {reduction:.1f} years."
        )
    elif reduction < 0:
        combined_delta_text = (
            f"Lithium worsens simple payback by {abs(reduction):.1f} years."
        )
    else:
        combined_delta_text = (
            "Lithium does not change simple payback under current assumptions."
        )
else:
    combined_delta_text = "Combined payback is not achieved under current assumptions."

st.markdown(
    f"""
    <div class="insight-box">
    <b>Decision readout:</b> The current baseline cost is <b>{fmt_money(baseline["cost_baseline_total"])}/yr</b>.
    The pipeline case changes annual cost to <b>{fmt_money(pipeline["cost_pipeline_total"])}/yr</b>,
    creating <b>{fmt_money(savings_pipeline_only)}/yr</b> in transport-related savings.
    Lithium adds <b>{fmt_money(lithium["value_li_net"])}/yr</b> of net upside.
    {combined_delta_text}
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-header">Top Economic Drivers</div>', unsafe_allow_html=True
)
driver_cols = st.columns(3)
for i, d in enumerate(drivers):
    with driver_cols[i]:
        st.markdown(f'<div class="insight-box">{d}</div>', unsafe_allow_html=True)


# TABS

tabs = st.tabs(
    [
        "📊 Cost Comparison",
        "🛢️ Baseline Case",
        "🔧 Pipeline Case",
        "⚗️ Lithium Module",
        "🔀 Combined Case",
        "🏗️ MVC Reverse Engineering",
        "📈 Sensitivity",
    ]
)


# Cost comparison

with tabs[0]:
    st.markdown(
        '<div class="insight-box">This section compares baseline cost, pipeline cost, and combined economics. '
        "The pipeline must create enough annual savings to justify capital investment. Lithium is shown as an optional value uplift.</div>",
        unsafe_allow_html=True,
    )

    categories = ["Baseline", "Pipeline", "Pipeline + Lithium Offset"]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Trucking / Variable Transport",
            x=categories,
            y=[
                baseline["cost_truck_baseline"],
                pipeline["cost_pipeline_var"] + pipeline["cost_residual_truck"],
                pipeline["cost_pipeline_var"] + pipeline["cost_residual_truck"],
            ],
            marker_color=COLORS["baseline"],
        )
    )
    fig.add_trace(
        go.Bar(
            name="Disposal / Gathering / Fixed O&M",
            x=categories,
            y=[
                baseline["cost_disp_baseline"],
                pipeline["cost_local_gather"]
                + pipeline["cost_residual_disp"]
                + oandm_fixed,
                pipeline["cost_local_gather"]
                + pipeline["cost_residual_disp"]
                + oandm_fixed,
            ],
            marker_color=COLORS["orange"],
        )
    )
    fig.add_trace(
        go.Bar(
            name="Annualized CAPEX",
            x=categories,
            y=[0, pipeline["capex_annualized"], pipeline["capex_annualized"]],
            marker_color="#94a3b8",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Lithium Net Credit",
            x=categories,
            y=[0, 0, -max(lithium["value_li_net"], 0)],
            marker_color=COLORS["lithium"],
        )
    )
    fig.update_layout(
        barmode="relative",
        title="Annual Cost Comparison",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    wf = go.Figure(
        go.Waterfall(
            measure=["absolute", "relative", "relative", "total"],
            x=[
                "Baseline Cost",
                "Pipeline Savings",
                "Lithium Uplift",
                "Net Combined Cost",
            ],
            y=[
                baseline["cost_baseline_total"],
                -savings_pipeline_only,
                -max(lithium["value_li_net"], 0),
                0,
            ],
            connector={"line": {"color": "#2a4365"}},
            decreasing={"marker": {"color": COLORS["pipeline"]}},
            increasing={"marker": {"color": COLORS["baseline"]}},
            totals={"marker": {"color": COLORS["combined"]}},
        )
    )
    wf.update_layout(
        title="Annual Cost Bridge",
        yaxis_title="USD",
        **CHART_LAYOUT,
    )
    st.plotly_chart(wf, use_container_width=True)


# Baseline case

with tabs[1]:
    st.markdown(
        '<div class="insight-box">Estimate current annual trucking and disposal cost for the selected trucked fraction.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Annual Volume", f"{fmt_num(baseline['q_annual_bbl'], 0)} bbl")
    with c2:
        st.metric(
            "Currently Trucked Volume",
            f"{fmt_num(baseline['q_trucked_annual'], 0)} bbl/yr",
        )
    with c3:
        st.metric("Annual Trucking Cost", fmt_money(baseline["cost_truck_baseline"]))
    with c4:
        st.metric("Annual Disposal Cost", fmt_money(baseline["cost_disp_baseline"]))

    pie = go.Figure(
        go.Pie(
            labels=["Trucking", "Disposal"],
            values=[baseline["cost_truck_baseline"], baseline["cost_disp_baseline"]],
            marker=dict(
                colors=[COLORS["baseline"], COLORS["orange"]],
                line=dict(color="#0d1117", width=2),
            ),
            hole=0.5,
            textfont=dict(color="#f8fafc", size=14),
        )
    )
    pie.update_layout(title="Baseline Cost Breakdown", **CHART_LAYOUT)
    st.plotly_chart(pie, use_container_width=True)

    st.markdown(
        f"""
        <div class="insight-box">
        Baseline cost is driven by <b>{fmt_num(f_trucked_pct, 0)}%</b> of produced water currently moving by truck over
        <b>{fmt_num(d_baseline, 1)} miles</b> at <b>${c_truck_mile:.3f}/bbl-mile</b>.
        Under current assumptions, that creates <b>{fmt_money(baseline["cost_baseline_total"])}/yr</b> in trucking and disposal cost.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Pipeline case

with tabs[2]:
    st.markdown(
        '<div class="insight-box">Annualize pipeline CAPEX and add gathering, pipeline OPEX, residual trucking/disposal, and fixed O&M.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Annualized CAPEX", fmt_money(pipeline["capex_annualized"]))
    with c2:
        st.metric("Annual Pipeline OPEX", fmt_money(pipeline["cost_pipeline_var"]))
    with c3:
        st.metric("Annual Gathering Cost", fmt_money(pipeline["cost_local_gather"]))
    with c4:
        st.metric(
            "Total Pipeline Annual Cost", fmt_money(pipeline["cost_pipeline_total"])
        )

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric(
            "Pipeline-Handled Volume",
            f"{fmt_num(pipeline['q_pipeline_annual'], 0)} bbl/yr",
        )
    with d2:
        st.metric(
            "Residual Volume", f"{fmt_num(pipeline['q_residual_annual'], 0)} bbl/yr"
        )
    with d3:
        st.metric("Residual Fraction", f"{fmt_num(f_residual_pct, 0)}%")
    with d4:
        st.metric("NPV (Pipeline Only)", fmt_money(npv_pipeline))

    cost_labels = [
        "Annualized CAPEX",
        "Pipeline OPEX",
        "Gathering",
        "Residual Trucking",
        "Residual Disposal",
        "Fixed O&M",
    ]
    cost_vals = [
        pipeline["capex_annualized"],
        pipeline["cost_pipeline_var"],
        pipeline["cost_local_gather"],
        pipeline["cost_residual_truck"],
        pipeline["cost_residual_disp"],
        oandm_fixed,
    ]
    bar = go.Figure(
        go.Bar(
            x=cost_labels,
            y=cost_vals,
            marker_color=[
                "#94a3b8",
                COLORS["pipeline"],
                COLORS["orange"],
                COLORS["baseline"],
                "#fbbf24",
                "#cbd5e1",
            ],
            text=[fmt_money(v) for v in cost_vals],
            textposition="outside",
            textfont=dict(color="#f8fafc", size=13),
        )
    )
    bar.update_layout(
        title="Pipeline Cost Breakdown",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(bar, use_container_width=True)

    if savings_pipeline_only > 0:
        st.markdown(
            f"""
            <div class="insight-box">
            The pipeline creates <b>{fmt_money(savings_pipeline_only)}/yr</b> in annual savings versus the baseline.
            Simple payback is <b>{payback_pipeline:.1f} years</b>, and NPV over <b>{project_life} years</b> at <b>{discount_rate_pct}%</b> discount rate is <b>{fmt_money(npv_pipeline)}</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="insight-box">
            Under current assumptions, the pipeline case does not outperform the baseline.
            Check utilization, CAPEX, trucking cost, gathering cost, and residual handling assumptions.
            </div>
            """,
            unsafe_allow_html=True,
        )


# Lithium recovery

with tabs[3]:
    st.markdown(
        '<div class="insight-box">Lithium output is calculated from selected water throughput, lithium concentration, and recovery efficiency.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Water Basis for Lithium", f"{fmt_num(q_for_lithium, 0)} bbl/yr")
    with c2:
        st.metric(
            "Recovered Li", f"{fmt_num(lithium['li_mass_tonnes_recovered'], 1)} t Li/yr"
        )
    with c3:
        st.metric("LCE Produced", f"{fmt_num(lithium['lce_tonnes'], 1)} t LCE/yr")
    with c4:
        st.metric("Net Lithium Value", fmt_money(lithium["value_li_net"]))

    d1, d2, d3 = st.columns(3)
    with d1:
        st.metric("Gross Revenue", fmt_money(lithium["revenue_li_gross"]))
    with d2:
        st.metric("Processing Cost", fmt_money(lithium["cost_li_processing"]))
    with d3:
        st.metric("Operator Share", f"{fmt_num(f_operator_pct, 0)}%")

    rev = go.Figure(
        go.Bar(
            x=["Gross Revenue", "Processing Cost", "Net Value"],
            y=[
                lithium["revenue_li_gross"],
                -lithium["cost_li_processing"],
                lithium["value_li_net"],
            ],
            marker_color=[COLORS["lithium"], COLORS["baseline"], COLORS["combined"]],
            text=[
                fmt_money(lithium["revenue_li_gross"]),
                fmt_money(-lithium["cost_li_processing"]),
                fmt_money(lithium["value_li_net"]),
            ],
            textposition="outside",
            textfont=dict(color="#f8fafc", size=13),
        )
    )
    rev.update_layout(
        title="Lithium Value Bridge",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(rev, use_container_width=True)

    conc_range = np.linspace(5, max(li_mgL * 4, 200), 100)
    conc_net = []
    for conc in conc_range:
        tmp = calc_lithium(q_for_lithium, conc, eta_li, p_lce, c_lce_proc, f_operator)
        conc_net.append(tmp["value_li_net"])

    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=conc_range,
            y=conc_net,
            mode="lines",
            line=dict(color=COLORS["lithium"], width=3),
            fill="tozeroy",
            fillcolor="rgba(167,139,250,0.12)",
            name="Net Lithium Value",
        )
    )
    fig2.add_vline(
        x=li_mgL,
        line=dict(color=COLORS["accent"], dash="dash"),
        annotation_text=f"Current: {li_mgL} mg/L",
        annotation_font_color="#f8fafc",
    )
    fig2.update_layout(
        title="Lithium Net Value vs. Concentration",
        xaxis_title="Li Concentration (mg/L)",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig2, use_container_width=True)


# Combined case

with tabs[4]:
    st.markdown(
        '<div class="insight-box">Add net lithium value to pipeline transport savings and compare the combined economics.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pipeline Annual Savings", fmt_money(savings_pipeline_only))
    with c2:
        st.metric("Lithium Net Value", fmt_money(lithium["value_li_net"]))
    with c3:
        st.metric("Combined Annual Benefit", fmt_money(benefit_combined))
    with c4:
        st.metric("Combined NPV", fmt_money(npv_combined))

    e1, e2 = st.columns(2)
    with e1:
        st.metric(
            "Pipeline-Only Payback",
            f"{payback_pipeline:.1f} yrs" if payback_pipeline else "No payback",
        )
    with e2:
        if payback_pipeline and payback_combined:
            delta = payback_pipeline - payback_combined
            st.metric(
                "Combined Payback",
                f"{payback_combined:.1f} yrs",
                delta=f"-{delta:.1f} yrs" if delta > 0 else f"+{abs(delta):.1f} yrs",
                delta_color="normal" if delta > 0 else "inverse",
            )
        else:
            st.metric("Combined Payback", "No payback")

    years = np.arange(0, project_life + 1)
    pipe_cf = [-capex_pipe + savings_pipeline_only * y for y in years]
    comb_cf = [-capex_pipe + benefit_combined * y for y in years]

    cf = go.Figure()
    cf.add_trace(
        go.Scatter(
            x=years,
            y=pipe_cf,
            name="Pipeline Only",
            line=dict(color=COLORS["pipeline"], width=3),
        )
    )
    cf.add_trace(
        go.Scatter(
            x=years,
            y=comb_cf,
            name="Pipeline + Lithium",
            line=dict(color=COLORS["combined"], width=3, dash="dash"),
        )
    )
    cf.add_hline(y=0, line=dict(color="#94a3b8", width=1, dash="dot"))
    cf.update_layout(
        title="Cumulative Cash Flow (Simple, Undiscounted)",
        xaxis_title="Year",
        yaxis_title="USD",
        **CHART_LAYOUT,
    )
    st.plotly_chart(cf, use_container_width=True)

    if payback_pipeline and payback_combined:
        delta = payback_pipeline - payback_combined
        if delta > 0:
            txt = f"Lithium reduces payback from <b>{payback_pipeline:.1f}</b> to <b>{payback_combined:.1f}</b> years, a reduction of <b>{delta:.1f} years</b>."
        elif delta < 0:
            txt = f"Lithium worsens payback from <b>{payback_pipeline:.1f}</b> to <b>{payback_combined:.1f}</b> years."
        else:
            txt = "Lithium does not change payback under current assumptions."
    elif payback_combined and not payback_pipeline:
        txt = f"Lithium is the difference-maker: the combined case achieves payback in <b>{payback_combined:.1f} years</b> while the pipeline-only case does not."
    else:
        txt = "The combined case still does not achieve payback under current assumptions."

    st.markdown(f'<div class="insight-box">{txt}</div>', unsafe_allow_html=True)


# MVC tariff analysis

with tabs[5]:
    st.markdown(
        '<div class="insight-box">Estimate the delivered-volume tariff needed to support pipeline investment under selected throughput, MVC, penalty, and margin assumptions.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Available Volume", f"{fmt_num(mvc_available_bpd, 0)} bbl/day")
    with c2:
        st.metric(
            "Expected Throughput", f"{fmt_num(mvc['q_actual_annual']/365.0, 0)} bbl/day"
        )
    with c3:
        st.metric("MVC Level", f"{fmt_num(mvc['q_mvc_annual']/365.0, 0)} bbl/day")
    with c4:
        st.metric("Shortfall", f"{fmt_num(mvc['q_shortfall_annual']/365.0, 0)} bbl/day")

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("Annual Cost", fmt_money(mvc["annual_cost"]))
    with d2:
        st.metric("Target Revenue", fmt_money(mvc["target_revenue"]))
    with d3:
        st.metric(
            "Required Tariff",
            "N/A"
            if mvc["required_tariff"] is None
            else f"${mvc['required_tariff']:.2f}/bbl",
        )
    with d4:
        st.metric("Candidate Tariff", f"${candidate_tariff:.2f}/bbl")

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        st.metric("Tariff Revenue", fmt_money(mvc["tariff_revenue"]))
    with e2:
        st.metric("Shortfall Revenue", fmt_money(mvc["shortfall_revenue"]))
    with e3:
        st.metric("Total Revenue", fmt_money(mvc["total_revenue_with_candidate"]))
    with e4:
        st.metric("Annual Margin", fmt_money(mvc["annual_margin_with_candidate"]))

    shortfall_note = ""
    if mvc["q_shortfall_annual"] > 0:
        shortfall_note = (
            f" With current assumptions, throughput is below MVC by "
            f"{fmt_num(mvc['q_shortfall_annual']/365.0, 0)} bbl/day, creating "
            f"{fmt_money(mvc['shortfall_revenue'])}/yr of shortfall revenue at "
            f"${shortfall_penalty:.2f}/bbl."
        )

    req_tariff_text = (
        "N/A"
        if mvc["required_tariff"] is None
        else f"${mvc['required_tariff']:.2f}/bbl"
    )

    st.markdown(
        f"""
        <div class="insight-box">
        <b>Reverse-engineering readout:</b> To cover annualized CAPEX, fixed O&amp;M, variable OPEX, and a target margin of
        <b>{target_margin_pct}%</b>, the required delivered-volume tariff is <b>{req_tariff_text}</b> under the current average-throughput assumption.
        This is based on expected throughput of <b>{fmt_num(mvc['q_actual_annual']/365.0, 0)} bbl/day</b>.{shortfall_note}
        </div>
        """,
        unsafe_allow_html=True,
    )

    rev_fig = go.Figure()
    rev_fig.add_trace(
        go.Bar(
            name="Tariff Revenue",
            x=["Candidate Revenue", "Target Revenue"],
            y=[
                mvc["tariff_revenue"],
                max(mvc["target_revenue"] - mvc["shortfall_revenue"], 0),
            ],
            marker_color=COLORS["combined"],
        )
    )
    rev_fig.add_trace(
        go.Bar(
            name="Shortfall Revenue",
            x=["Candidate Revenue", "Target Revenue"],
            y=[mvc["shortfall_revenue"], mvc["shortfall_revenue"]],
            marker_color=COLORS["orange"],
        )
    )
    rev_fig.update_layout(
        barmode="stack",
        title="Revenue Needed vs. Revenue from Candidate Tariff",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(rev_fig, use_container_width=True)

    cost_fig = go.Figure(
        go.Bar(
            x=[
                "Annualized CAPEX",
                "Variable OPEX",
                "Fixed O&M",
                "Target Margin",
                "Total Target Revenue",
            ],
            y=[
                mvc["annualized_capex"],
                mvc["variable_opex"],
                oandm_fixed,
                mvc["target_revenue"] - mvc["annual_cost"],
                mvc["target_revenue"],
            ],
            marker_color=[
                "#94a3b8",
                COLORS["pipeline"],
                COLORS["orange"],
                COLORS["lithium"],
                COLORS["combined"],
            ],
            text=[
                fmt_money(v)
                for v in [
                    mvc["annualized_capex"],
                    mvc["variable_opex"],
                    oandm_fixed,
                    mvc["target_revenue"] - mvc["annual_cost"],
                    mvc["target_revenue"],
                ]
            ],
            textposition="outside",
            textfont=dict(color="#f8fafc", size=13),
        )
    )
    cost_fig.update_layout(
        title="Target Revenue Build-Up",
        yaxis_title="USD / year",
        **CHART_LAYOUT,
    )
    st.plotly_chart(cost_fig, use_container_width=True)

    tariff_range = np.linspace(
        0.0, max(candidate_tariff * 3, (mvc["required_tariff"] or 1.0) * 2, 5.0), 80
    )
    margin_vals = []
    for tariff in tariff_range:
        test = calc_mvc_reverse_engineering(
            q_bpd_available=mvc_available_bpd,
            throughput_pct=mvc_throughput_pct,
            mvc_pct=mvc_level_pct,
            capex_pipe=capex_pipe,
            c_pipe_opex=c_pipe_opex,
            oandm_fixed=oandm_fixed,
            r=r,
            n=project_life,
            target_margin_pct=target_margin_pct,
            shortfall_penalty=shortfall_penalty,
            candidate_tariff=tariff,
        )
        margin_vals.append(
            test["annual_margin_with_candidate"]
            - (test["target_revenue"] - test["annual_cost"])
        )

    tariff_fig = go.Figure()
    tariff_fig.add_trace(
        go.Scatter(
            x=tariff_range,
            y=margin_vals,
            mode="lines",
            name="Revenue gap vs target",
            line=dict(color=COLORS["combined"], width=3),
        )
    )
    tariff_fig.add_hline(y=0, line=dict(color="#94a3b8", width=1, dash="dot"))
    tariff_fig.add_vline(
        x=candidate_tariff,
        line=dict(color=COLORS["accent"], width=1, dash="dash"),
        annotation_text="Candidate",
    )
    if mvc["required_tariff"] is not None:
        tariff_fig.add_vline(
            x=mvc["required_tariff"],
            line=dict(color=COLORS["pipeline"], width=1, dash="dot"),
            annotation_text="Required",
        )
    tariff_fig.update_layout(
        title="Tariff Sensitivity Relative to Target Revenue",
        xaxis_title="Tariff ($/bbl)",
        yaxis_title="Annual revenue above / below target ($/yr)",
        **CHART_LAYOUT,
    )
    st.plotly_chart(tariff_fig, use_container_width=True)

# Sensitivity analysis
with tabs[6]:
    st.markdown(
        '<div class="insight-box">Evaluate how payback changes as one input varies.</div>',
        unsafe_allow_html=True,
    )

    sens_var = st.selectbox(
        "Select sensitivity variable",
        [
            "Produced Water Volume (bbl/day)",
            "Baseline Trucking Cost ($/bbl-mile)",
            "Pipeline CAPEX ($)",
            "Pipeline OPEX ($/bbl)",
            "Li Concentration (mg/L)",
            "LCE Price ($/tonne LCE)",
        ],
    )

    def recompute(var_name, val):
        _q_bpd = q_bpd
        _c_truck_mile = c_truck_mile
        _capex = capex_pipe
        _c_pipe_opex = c_pipe_opex
        _li_mgL = li_mgL
        _p_lce = p_lce

        if var_name == "Produced Water Volume (bbl/day)":
            _q_bpd = val
        elif var_name == "Baseline Trucking Cost ($/bbl-mile)":
            _c_truck_mile = val
        elif var_name == "Pipeline CAPEX ($)":
            _capex = val
        elif var_name == "Pipeline OPEX ($/bbl)":
            _c_pipe_opex = val
        elif var_name == "Li Concentration (mg/L)":
            _li_mgL = val
        elif var_name == "LCE Price ($/tonne LCE)":
            _p_lce = val

        _baseline = calc_baseline(_q_bpd, f_trucked, d_baseline, _c_truck_mile, c_disp)
        _pipeline = calc_pipeline(
            q_trucked_annual=_baseline["q_trucked_annual"],
            capex_pipe=_capex,
            c_pipe_opex=_c_pipe_opex,
            d_local=d_local,
            c_haul_mile=c_haul_mile,
            c_truck_mile=_c_truck_mile,
            c_disp=c_disp,
            d_baseline=d_baseline,
            r=r,
            n=project_life,
            oandm_fixed=oandm_fixed,
            pipeline_utilization=pipeline_utilization,
        )

        if lithium_basis == "Pipeline-handled volume only":
            _q_for_li = _pipeline["q_pipeline_annual"]
        elif lithium_basis == "Currently trucked volume":
            _q_for_li = _baseline["q_trucked_annual"]
        else:
            _q_for_li = _baseline["q_annual_bbl"]

        _lithium = calc_lithium(
            _q_for_li, _li_mgL, eta_li, _p_lce, c_lce_proc, f_operator
        )

        _savings = _baseline["cost_baseline_total"] - _pipeline["cost_pipeline_total"]
        _combined = _savings + _lithium["value_li_net"]

        _pb = safe_payback(_capex, _savings)
        _cpb = safe_payback(_capex, _combined)

        return (
            50 if _pb is None else min(_pb, 50),
            50 if _cpb is None else min(_cpb, 50),
        )

    if sens_var == "Produced Water Volume (bbl/day)":
        x_vals = np.linspace(max(q_bpd * 0.25, 500), q_bpd * 2.5, 60)
        x_current = q_bpd
    elif sens_var == "Baseline Trucking Cost ($/bbl-mile)":
        x_vals = np.linspace(0.005, max(c_truck_mile * 3, 0.10), 60)
        x_current = c_truck_mile
    elif sens_var == "Pipeline CAPEX ($)":
        x_vals = np.linspace(capex_pipe * 0.25, capex_pipe * 3, 60)
        x_current = capex_pipe
    elif sens_var == "Pipeline OPEX ($/bbl)":
        x_vals = np.linspace(0.05, max(c_pipe_opex * 4, 2.0), 60)
        x_current = c_pipe_opex
    elif sens_var == "Li Concentration (mg/L)":
        x_vals = np.linspace(5, max(li_mgL * 4, 200), 60)
        x_current = li_mgL
    else:
        x_vals = np.linspace(5000, max(p_lce * 2.5, 40000), 60)
        x_current = p_lce

    pb_pipe = []
    pb_comb = []
    for x in x_vals:
        pb, cpb = recompute(sens_var, x)
        pb_pipe.append(pb)
        pb_comb.append(cpb)

    sens_fig = go.Figure()
    sens_fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=pb_pipe,
            name="Pipeline Payback",
            line=dict(color=COLORS["pipeline"], width=3),
        )
    )
    sens_fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=pb_comb,
            name="Combined Payback",
            line=dict(color=COLORS["combined"], width=3, dash="dash"),
        )
    )
    sens_fig.add_hline(
        y=5, line=dict(color="#34d399", width=1, dash="dot"), annotation_text="5 yr"
    )
    sens_fig.add_hline(
        y=10, line=dict(color="#f59e0b", width=1, dash="dot"), annotation_text="10 yr"
    )
    sens_fig.add_vline(
        x=x_current,
        line=dict(color=COLORS["accent"], width=1, dash="dash"),
        annotation_text="Current",
    )

    sens_layout = CHART_LAYOUT.copy()
    sens_layout["yaxis"] = {**CHART_LAYOUT["yaxis"], "range": [0, 35]}

    sens_fig.update_layout(
        title=f"Payback Period vs. {sens_var}",
        xaxis_title=sens_var,
        yaxis_title="Simple payback (years)",
        **sens_layout,
    )
    st.plotly_chart(sens_fig, use_container_width=True)

    st.markdown(
        '<div class="section-header">Break-Even Heatmap</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="insight-box">Map payback across produced-water volume and trucking-cost assumptions.</div>',
        unsafe_allow_html=True,
    )

    vol_range = np.linspace(max(q_bpd * 0.2, 500), q_bpd * 2.5, 25)
    truck_range = np.linspace(0.005, max(c_truck_mile * 3, 0.10), 25)
    Z = np.zeros((len(truck_range), len(vol_range)))

    for i, tc in enumerate(truck_range):
        for j, vol in enumerate(vol_range):
            _baseline = calc_baseline(vol, f_trucked, d_baseline, tc, c_disp)
            _pipeline = calc_pipeline(
                q_trucked_annual=_baseline["q_trucked_annual"],
                capex_pipe=capex_pipe,
                c_pipe_opex=c_pipe_opex,
                d_local=d_local,
                c_haul_mile=c_haul_mile,
                c_truck_mile=tc,
                c_disp=c_disp,
                d_baseline=d_baseline,
                r=r,
                n=project_life,
                oandm_fixed=oandm_fixed,
                pipeline_utilization=pipeline_utilization,
            )
            _save = _baseline["cost_baseline_total"] - _pipeline["cost_pipeline_total"]
            _pb = safe_payback(capex_pipe, _save)
            Z[i, j] = 30 if _pb is None else min(_pb, 30)

    heat = go.Figure(
        go.Heatmap(
            x=vol_range,
            y=truck_range,
            z=Z,
            colorscale=[
                [0, "#10b981"],
                [0.33, "#34d399"],
                [0.5, "#f59e0b"],
                [0.7, "#ef4444"],
                [1, "#7f1d1d"],
            ],
            zmin=0,
            zmax=30,
            colorbar=dict(
                title=dict(text="Payback (yr)", font=dict(color="#f8fafc", size=14)),
                tickfont=dict(color="#e2e8f0", size=13),
            ),
        )
    )
    heat.update_layout(
        title="Payback Heatmap: Volume vs. Trucking Cost",
        xaxis_title="Produced water volume (bbl/day)",
        yaxis_title="Baseline trucking cost ($/bbl-mile)",
        **CHART_LAYOUT,
    )
    st.plotly_chart(heat, use_container_width=True)

# Operational metrics
st.markdown(
    '<div class="section-header">Operational Insights</div>', unsafe_allow_html=True
)
o1, o2, o3 = st.columns(3)
with o1:
    st.metric("Truck Trips Displaced", f"{fmt_num(truck_trips_displaced, 0)} trucks/yr")
with o2:
    st.metric("Truck-Miles Avoided", f"{fmt_num(truck_miles_avoided, 0)}")
with o3:
    st.metric("Pipeline Utilization", f"{fmt_num(pipeline_utilization_pct, 0)}%")

st.markdown(
    f"""
    <div class="insight-box">
    Under current assumptions, the project displaces approximately <b>{fmt_num(truck_trips_displaced, 0)} truck trips per year</b>
    and avoids roughly <b>{fmt_num(truck_miles_avoided, 0)} annual truck-miles</b> relative to the baseline haul distance.
    Use these metrics to compare operational and logistics impacts.
    </div>
    """,
    unsafe_allow_html=True,
)

# Footer
st.divider()
st.markdown(
    '<div style="text-align:center;color:#cbd5e1;font-size:0.75rem;padding:12px 0;">'
    "💧 <b>Produced Water Pre-Feasibility Tool</b> &nbsp;|&nbsp; "
    "Screening estimates only. Requires engineering, subsurface, and commercial validation."
    "</div>",
    unsafe_allow_html=True,
)
