================
How To Deploy UI
================

PARETO UI Deployment
--------------------
The PARETO UI is deployed using Electron.js. For the complete documentation, visit their site `here <https://www.electronjs.org/docs/latest/>`_.

The deployment process is dependent on the operating system in use. We currently support :ref:`windows_guide_start` and :ref:`mac_guide_start`.

**Prerequisites**

- Miniconda
- npm
- Active conda environment with PARETO UI installed locally. To install the PARETO UI locally, follow the steps in our guide :ref:`how-to-install-ui-locally-page`


.. _windows_guide_start:

Windows
-------

.. _windows_build_requirements:

**Build requirements**

With your conda environment active, install the proper build requirements. Navigate to ``<pareto-ui>/backend`` and run the following command::

    pip install -r requirements-build.txt


.. _windows_application_build:

**Application build**

To build the application installer, navigate to ``<pareto-ui>/electron`` and run the following command::

    npm run dist:win

The application build handles 3 substeps - building the backend, building the frontned, and building the electron package. 


.. _windows_code_sign:

**Code sign the application**


.. _mac_guide_start:

MacOS (ARM64)
-------------

.. _mac_build_requirements:

**Build requirements**

With your conda environment active, install the proper build requirements. Navigate to ``<pareto-ui>/backend`` and run the following command::

    pip install -r requirements-build.txt


.. _mac_application_build:

**Application build**

To build the application installer, navigate to ``<pareto-ui>/electron`` and run the following command::

    npm run dist:mac

The application build handles 3 substeps - building the backend, building the frontned, and building the electron package. 


.. _mac_code_sign:

**Code sign the application**