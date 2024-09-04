.. _how-to-install-ui-locally-page:

=========================
How To Install UI Locally
=========================

These installation instructions are targeted towards developers and those who wish to deploy the desktop application.


**Prerequisites**

- Miniconda
- npm


Installing the UI
-----------------

1. Fork the repo on GitHub (your copy of the main repo)

2. Clone your fork locally, creating a workspace (replacing ``<githubid>`` with your github user id)::

    git clone https://github.com/<githubid>/pareto-ui

3. Create a dedicated Conda environment for development work::

    conda env create --file environment.yml

4. Activate the ``pareto-ui-env`` Conda environment. This command must be run every time a new console/terminal window is opened::

    conda activate pareto-ui-env

5. Navigate into the new ``pareto-ui/electron`` directory, then run the following command to install 
   the electron javascript dependencies::

    npm clean-install

6. Navigate into the new ``pareto-ui/electron/ui`` directory, then run the following command to install 
   the frontend dependencies::

    npm clean-install

7. Install the open-source solvers provided by the IDAES project::

    idaes get-extensions --verbose


Running the UI
--------------

1. Navigate into the new ``pareto-ui/electron`` directory, then run the following command::

    npm run electron-start