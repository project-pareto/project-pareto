================
How To Deploy UI
================

The PARETO UI is deployed using Electron.js. Visit `their site <https://www.electronjs.org/docs/latest/>`_ for complete documentation.

The deployment process is dependent on the operating system in use. We currently support :ref:`windows_guide_start` and :ref:`mac_guide_start`.

**Prerequisites**

- Miniconda
- npm
- Active conda environment with PARETO UI installed locally. To install the PARETO UI locally, follow the steps in our guide :ref:`how-to-install-ui-locally-page`


.. _windows_guide_start:

Windows
-------

.. _windows_build_requirements:

**1. Install build requirements**

With your conda environment active, install the proper build requirements. Navigate to ``<pareto-ui>/backend`` and run the following command::

    pip install -r requirements-build.txt


.. _windows_application_build:

**2. Build the application**

To build the application installer, navigate to ``<pareto-ui>/electron`` and run the following command::

    npm run dist:win

The application build handles 3 substeps - building the backend, building the frontned, and building the electron package. 


.. _windows_code_sign:

**3. Codesign the application**

For a complete guide to codesigning electron applications, see their `codesigning guide <https://www.electronjs.org/docs/latest/tutorial/code-signing>`_.

The general steps required to codesign a Windows application are as follows:

* Purchase a codesigning certificate. 

    * This can be a standard certificate or an extended validation (EV) certificate. 

* Implement the certificate key. 

    * Using a hardware device such as a USB token OR

    * Using an HSM or cloud hosted vault such as Azure Key Vault

Our team has taken the approach of purchasing an EV certificate from GlobalSign and hosting the key in Azure Key Vault. For a complete tutorial on this process, visit  this `blog post <https://melatonin.dev/blog/how-to-code-sign-windows-installers-with-an-ev-cert-on-github-actions/>`_ To code sign the deployed application in this manner, see the following steps:

**Acquire an API key:**

Reach out to the LBL team.

**Install Azure Signtool:**

Run the following command::

    dotnet tool install --global AzureSignTool

**Sign the application:**

Run the following command, replacing the keywords inside angular brackets (<>) with the appropriate values::

    AzureSignTool sign -kvu "<AZURE_KEY_VAULT_URI>" -kvi "<AZURE_CLIENT_ID>" -kvt "<AZURE_TENANT_ID>" -kvs "<AZURE_CLIENT_SECRET>" -kvc $<AZURE_CERT_NAME> -tr http://timestamp.digicert.com -v <path-to-application>

.. _mac_guide_start:

MacOS (ARM64)
-------------

.. _mac_build_requirements:

**1. Install the build requirements**

With your conda environment active, install the proper build requirements. Navigate to ``<pareto-ui>/backend`` and run the following command::

    pip install -r requirements-build.txt


.. _mac_application_build:

**2. Build the application**

To build the application installer, navigate to ``<pareto-ui>/electron`` and run the following command::

    npm run dist:mac

The application build handles 3 substeps - building the backend, building the frontned, and building the electron package. 


.. _mac_code_sign:

**3. Codesign the application**

For a complete guide to codesigning electron MacOS applications, see their `mac app store submission guide <https://www.electronjs.org/docs/latest/tutorial/mac-app-store-submission-guide>`_.

Codesigning Mac applications requires an `Apple developer account <https://developer.apple.com/>`_. 