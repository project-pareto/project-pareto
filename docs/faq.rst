Frequently Asked Questions
==========================

How to ...
-----------

... Run examples?
    PARETO project provides examples to run the operational produced water management model
    and the strategic produced water management model (see pareto/case_studies/).
    To run the examples, go to:

    * pareto/operatinal_water_management/run_operational_model.py
    * pareto/strategic_water_management/run_strategic_model.py

... Get more help?
    Use the website to `register <https://pareto.org/register/>`_ for the PARETO support mailing list.
    Then you can send questions to pareto-support@pareto.org. For more specific technical questions, we recommend
    our new `PARETO discussions board on Github <https://github.com/project-pareto/discussions>`_.

Troubleshooting
---------------

Missing win32api DLL
    For Python 3.8 and maybe others, you can get an error when running Jupyter on Windows 10 about
    missing the win32api DLL. There is a relatively easy fix::

        pip uninstall pywin32
        pip install pywin32==225
