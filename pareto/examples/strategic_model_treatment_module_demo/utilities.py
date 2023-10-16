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

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    solve_model,
)
from pareto.utilities.results import (
    generate_report,
    OutputUnits,
)
from pareto.utilities.results import (
    is_feasible,
    nostdout,
)
from pyomo.environ import units, value
from ipywidgets import FloatText, Button, Layout, GridspecLayout, ToggleButtons, Output
from IPython.display import display
import pandas as pd


def solve_and_check_feasibility(model, options=None):
    """
    Solve model, check solution feasibility, and return optimization results as
    a dictionary
    """
    if options is None:
        options = {
            "solver": ("gurobi", "cbc"),
            "deactivate_slacks": True,
            "scale_model": False,
            "scaling_factor": 1000000,
            "running_time": 300,
            "gap": 0,
            "gurobi_numeric_focus": 1,
        }
    results_obj = solve_model(model=model, options=options)
    termination_message = results_obj.solver.termination_message

    # Check feasibility of the solved model
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")

    # Generate dictionary of reports to return
    _, results_dict = generate_report(
        model,
        results_obj=results_obj,
        is_print=None,
        output_units=OutputUnits.user_units,
        fname=None,
    )

    return results_dict, termination_message


def get_R01_results(results_dict):
    """
    Extract R01 buildout results
    """
    for datapt in results_dict["vb_y_Treatment_dict"][1:]:
        site, technology, capacity, built = datapt
        if site == "R01" and built == 1:
            return technology, capacity


def create_widgets(model):
    """
    Create and display widgets
    """
    # Store default treatment costs (in user units)
    default_costs = {
        "MVC": {"opex": 0.5, "capex": 1000},
        "MD": {"opex": 1, "capex": 500},
        "OARO": {"opex": 0.7, "capex": 800},
    }

    # Create text input widgets to allow user to change treatment cost parameters
    txt_inputs = {}
    for tech in default_costs:
        txt_inputs[tech] = {}
        txt_inputs[tech]["opex"] = FloatText(
            value=default_costs[tech]["opex"],
            layout=Layout(width="150px"),
        )
        txt_inputs[tech]["capex"] = FloatText(
            value=default_costs[tech]["capex"],
            layout=Layout(width="150px"),
        )

    # Create toggle buttons widget to select which constraint to use
    toggle = ToggleButtons(
        options=["No", "MVC", "MD", "OARO"],
        description="Choose desalination technology for R01?",
    )
    toggle.value = "No"  # No constraints are activated by default

    # Create apply button
    apply_button = Button(
        description="APPLY VALUES TO MODEL", layout=Layout(width="auto", height="auto")
    )

    # Create optimize button
    optimize_button = Button(
        description="RUN OPTIMIZATION", layout=Layout(width="auto", height="auto")
    )

    # Create reset button
    reset_button = Button(
        description="RESET DEFAULT VALUES", layout=Layout(width="auto", height="auto")
    )

    # Create output widget
    out = Output(layout={"border": "1px solid black"})

    # Get units for CAPEX/OPEX unit conversions
    capex_model_units = units.get_units(model.p_kappa_Treatment)
    capex_user_units = units.USD / (units.oil_bbl / units.day)
    opex_model_units = units.get_units(model.p_pi_Treatment)
    opex_user_units = units.USD / units.oil_bbl

    # Define callback function to excecute when apply button is pressed
    # Apply values in the widgets to the Pyomo model
    def apply(b=None):
        table_data = []

        # Iterate over all desalination technologies
        for tech in default_costs:
            # Extract user-specified OPEX and CAPEX values from input widgets
            opex_user_value = txt_inputs[tech]["opex"].value
            capex_user_value = txt_inputs[tech]["capex"].value

            # Convert to model units
            opex_converted = units.convert_value(
                opex_user_value, from_units=opex_user_units, to_units=opex_model_units
            )
            capex_converted = units.convert_value(
                capex_user_value,
                from_units=capex_user_units,
                to_units=capex_model_units,
            )

            # Change Pyomo model parameter values
            model.p_pi_Treatment[:, tech] = opex_converted
            model.p_kappa_Treatment[:, tech, :] = capex_converted

            # Save data so it can be printed in the output
            table_data.append([tech, opex_user_value, capex_user_value])

        # Activate the correct constraint (if any)
        model.ForceMvcCon.deactivate()
        model.ForceMdCon.deactivate()
        model.ForceOaroCon.deactivate()
        if toggle.value == "MVC":
            model.ForceMvcCon.activate()
        elif toggle.value == "MD":
            model.ForceMdCon.activate()
        elif toggle.value == "OARO":
            model.ForceOaroCon.activate()

        return table_data

    # Link callback function to optimize button
    apply_button.on_click(apply)

    # Define callback function to excecute when optimize button is pressed
    def optimize(b=None):
        # Clear existing text from the output widget
        out.clear_output()

        # Apply input from widgets to Pyomo model
        table_data = apply()

        with out:
            print("---------------------------------------------")
            print("Running optimization")
            print("---------------------------------------------")
            print(f"Desalination chosen for R01: {toggle.value}")
            print("Treatment costing parameters:")
            print(
                pd.DataFrame(
                    table_data,
                    columns=["Technology", "OPEX [$/bbl]", "Capex [$/bbl]"],
                    index=["", "", ""],
                )
            )
            print()

        # Solve the model and check feasibility of solution
        results_dict, termination_message = solve_and_check_feasibility(model)

        # Extract results for optimal treatment buildout at R01
        technology, capacity = get_R01_results(results_dict)

        with out:
            print("---------------------------------------------")
            print("Optimization results")
            print("---------------------------------------------")
            print(termination_message)
            print(f"R01 buildout: {technology}, {capacity}")
            print(f"Objective function value [k$]: {value(model.v_Z)}")

    # Link callback function to optimize button
    optimize_button.on_click(optimize)

    # Define callback function to excecute when reset button is pressed
    def reset(b=None):
        for tech in default_costs:
            # Reset the displayed values in the input widgets
            txt_inputs[tech]["opex"].value = default_costs[tech]["opex"]
            txt_inputs[tech]["capex"].value = default_costs[tech]["capex"]

        # Reset the toggle to the default value
        toggle.value = "No"

        # Apply values in the widgets (now the default values) to the Pyomo model
        apply()

    # Link callback function to reset button
    reset_button.on_click(reset)

    # Call reset to ensure the model and all widgets begin with default values
    reset()

    # Display widgets in a grid format
    def create_label_button(label):
        return Button(description=label, button_style="primary")

    grid = GridspecLayout(8, 4, width="615px")
    grid[0, 1] = create_label_button("MVC")
    grid[0, 2] = create_label_button("MD")
    grid[0, 3] = create_label_button("OARO")
    grid[1, 0] = create_label_button("OPEX [$/bbl]")
    grid[2, 0] = create_label_button("CAPEX [$/(bbl/day)]")
    grid[1, 1] = txt_inputs["MVC"]["opex"]
    grid[1, 2] = txt_inputs["MD"]["opex"]
    grid[1, 3] = txt_inputs["OARO"]["opex"]
    grid[2, 1] = txt_inputs["MVC"]["capex"]
    grid[2, 2] = txt_inputs["MD"]["capex"]
    grid[2, 3] = txt_inputs["OARO"]["capex"]
    grid[3, :] = toggle
    grid[5, :] = apply_button
    grid[6, :] = optimize_button
    grid[7, :] = reset_button
    display(grid)
    display(out)
