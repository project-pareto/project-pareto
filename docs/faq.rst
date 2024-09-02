Frequently Asked Questions
==========================

How to ...
-----------

**... Run examples?**
    PARETO project provides examples to run the operational produced water management model
    and the strategic produced water management model (see pareto/case_studies/).
    To run the examples, go to:

    * pareto/operatinal_water_management/run_operational_model.py
    * pareto/strategic_water_management/run_strategic_model.py


**... Get more help?**
    You can reach out by email to |support-email|. For more specific technical questions, we recommend
    our new `PARETO discussions board on Github <https://github.com/project-pareto/discussions>`_.

Troubleshooting
---------------

**No available solver found among choices: (('cbc',),)**

  If you encounter the error message "No available solver found among choices: (('cbc',),)," 
  it typically means that the solver CBC is not installed or not correctly configured in 
  your environment. Here are steps to resolve this issue:

  1. **Solver Installation**

    Ensure that the CBC solver is installed on your system. You can install it using the following methods:

    * **For Windows Users:**
      The easiest way to get CBC on Windows is to download an archive from https://github.com/coin-or/Cbc/releases.

    * **For Mac OS users:**

      .. code-block:: bash

          $ brew tap coin-or-tools/coinor
          $ brew install coin-or-tools/coinor/cbc

    * **For Ubuntu users:**

      .. code-block:: bash

          $ sudo apt-get install coinor-cbc

  2. **Verify Installation and Configure Solver in Your Code**

    Ensure your code correctly specifies the solver. For example, in Pyomo::

        from pyomo.environ import SolverFactory
        solver = SolverFactory("cbc")
        if not solver.available():
            raise Exception("Solver 'cbc' is not available.")

  3. **Update Path Environment Variable**

    If the solver is installed but not found, you might need to add it to your system's PATH environment variable.

    * **For Windows:**

      1. Open the Start Search, type in "env", and select "Edit the system environment variables".
      2. Click the "Environment Variables" button.
      3. Under "System variables", find the "Path" variable, select it, and click "Edit".
      4. Add the path to the `bin` directory containing the cbc.exe executable.

    * **For Mac/Ubuntu:**

      1. Open your terminal.
      2. Edit your shell profile file (e.g., ~/.bashrc, ~/.zshrc):

          .. code-block:: bash

              export PATH=$PATH:/path/to/cbc

      3. Reload the profile:

          .. code-block:: bash

              source ~/.zshrc  # or ~/.bashrc for Ubuntu

**Missing win32api DLL**

    For Python 3.8 and maybe others, you can get an error when running Jupyter on Windows 10 about
    missing the win32api DLL. There is a relatively easy fix::

        pip uninstall pywin32
        pip install pywin32==225
