================
How To Deploy UI
================

The PARETO UI is deployed using `Electron.js <https://www.electronjs.org/docs/latest/>`_.

The deployment process is dependent on the operating system in use. We currently support :ref:`windows_guide_start` and :ref:`mac_guide_start`.

**Prerequisites**

- `Miniforge <https://github.com/conda-forge/miniforge>`_ 
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

The application build handles 3 substeps - building the backend, building the frontend, and building the electron package. 


.. _windows_code_sign:

**3. Code sign the application**

For a complete guide to code signing electron applications, see their `code signing guide <https://www.electronjs.org/docs/latest/tutorial/code-signing>`_.

The general steps required to obtaining and implementing a code signing certificate are as follows:

* Purchase a code signing certificate. 

    * This can be a standard certificate or an extended validation (EV) certificate
    * For a list of certificate authorities, check out `Microsoft's documentation on managing code signing certificates <https://learn.microsoft.com/en-us/windows-hardware/drivers/dashboard/code-signing-cert-manage#get-or-renew-a-code-signing-certificate>`_

* Implement the certificate key

    * Using a hardware device such as a USB token OR
    * Using an HSM or cloud hosted vault such as Azure Key Vault

* Sign the Electron application

    * with a CLI tool such as Microsoft SignTool if using a USB token
    * with a CLI tool such as AzureSignTool if using Azure Key Vault

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

The application build handles 3 substeps - building the backend, building the frontend, and building the electron package. 


.. _mac_code_sign:

**3. Code sign the application**

For a complete guide to code signing electron MacOS applications, see the `Mac App Store Submission Guide <https://www.electronjs.org/docs/latest/tutorial/mac-app-store-submission-guide>`_.


The general steps required to obtaining and implementing an Apple code signing certificate are as follows:

* Create an `Apple developer account <https://developer.apple.com/>`_.
* Attain a `Developer ID Application certificate <https://developer.apple.com/help/account/create-certificates/create-developer-id-certificates/>`_ and add it to your Keychain
* Create a ``.env`` file in the ``<pareto-ui>/electron`` directory with the following variables:

    * APPLE_ID
    * APPLE_ID_PASSWORD
    * TEAM_ID
    * NOTARIZE_TOOL_

* Build the application (step 2)

.. _NOTARIZE_TOOL:

\*MacOS applications can be notarized with Apple as an additional step after being signed. This allows Apple to scan the application, provide feedback about any vulnerabilties or issues, and, if approved, provide a reputation to the application so that it will be trusted by other Mac users. The TEAM_ID, which is connected to your developer account, and the NOTARIZE_TOOL, which should be set to a CLI tool such as "notarytool", are necessary for this notarization process to run.