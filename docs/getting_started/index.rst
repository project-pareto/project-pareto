Getting Started
===============

.. _PARETO Installation:

Installation
------------

To install the PARETO framework on Windows operating systems, follow the set of instructions below
that are appropriate for your needs. If you need assistance please contact start a new discussion on
our `GitHub Discussion form <https://github.com/project-pareto/project-pareto/discussions>`_ or send
an email to |support-email|.

Developer Role
^^^^^^^^^^^^^^

The installation instructions vary slightly depending on the role you will have with Project Pareto.
Below are the roles we've identified:

**Users**: Use the PARETO platform to develop models, but never contribute to
development of the framework (i.e. never commit changes to the project-pareto
repo). This includes people who only work with protected data.

**Core-dev**: Work primarily on PARETO platform development and never handle
protected data.

**Hybrid**: Handle protected data, but also commit changes to the project-pareto
repo (even occasionally) - needs approval from PhD. Markus Drouven

+------------------+-----------------------------+
| Developer Role   | Installation Section        |
+==================+=============================+
| Users            | :ref:`min_install_users`    |
+------------------+-----------------------------+
| Core-dev         | :ref:`min_install_core-dev` |
+------------------+-----------------------------+
| Hybrid           | :ref:`min_install_hybrid`   |
+------------------+-----------------------------+

**Install Miniconda (optional)**

1. Download: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
2. Install anaconda from the downloaded file in (1).
3. Open the Anaconda Prompt (Start -> "Anaconda Prompt").

.. warning:: If you are using Python for other complex projects, you may want to
            consider using environments of some sort to avoid conflicting
            dependencies.  There are several good options including conda
            environments if you use Anaconda.

.. _min_install_users:

Users
-----
**Non-git tracked option**

1. Create a Conda environment, named e.g. ``pareto-env``::

    conda create --yes --name pareto-env python=3.9

2. Activate the ``pareto-env`` Conda environment. This command must be run every time a new console/terminal window is opened::

    conda activate pareto-env

3. Install PARETO with pip by one of the following methods

  a. To get the latest release::

      pip install project-pareto

  b. To get a specific release, for example 1.6.3::

      pip install project-pareto==1.6.3

  c. If you need unreleased cutting-edge development versions of PARETO, you
     can install PARETO directly from the GitHub repo either from the main
     PARETO repo or a developer's fork and branch (this installs from GitHub
     but does not create a local git clone/workspace)::

      pip install "git+https://github.com/project-pareto/project-pareto.git"
      pip install "git+https://github.com/ksbeattie/project-pareto@feature_1"

4. After installing PARETO, install the open-source solvers provided by the IDAES project::

    idaes get-extensions --verbose

.. _min_install_core-dev:

Core-dev
--------

.. important:: For more developer resources, see the `PARETO Wiki on GitHub <https://github.com/project-pareto/project-pareto/wiki>`_.

1. Fork the repo on GitHub (your copy of the main repo)

2. Clone your fork locally, with only one of the following commands, creating a
   workspace (replacing ``<githubid>`` with your github user id)::

    git clone https://github.com/<githubid>/project-pareto
    git clone git@github.com:<githubid>/project-pareto

3. Create a dedicated Conda environment for development work::

    conda create --name pareto-dev python=3.9 --yes

4. Activate the ``pareto-dev`` Conda environment. This command must be run every time a new console/terminal window is opened::

    conda activate pareto-dev

5. Navigate into the new ``project-pareto`` directory, then run the following command to install 
   PARETO in editable mode and the development-only dependencies::

    pip install -r requirements-dev.txt

6. After installing PARETO, install the open-source solvers provided by the IDAES project::

    idaes get-extensions --verbose

7. (Recommended) install the pre-commit checks that will run automatically whenever ``git commit`` is used, preventing the commit from being created if any of the checks fail::

    pre-commit install

   .. note:: ``pre-commit`` can cause commits to fail for reasons unrelated to the pre-commit checks. For more information, check the `related GitHub issue(s) <https://github.com/project-pareto/project-pareto/issues?q=is%3Aissue+is%3Aopen+label%3Apre-commit>`_.

.. _min_install_hybrid:

Hybrid
------

**User that can edit the base code**

.. important::
    Unlike a local clone of the repository, ZIP archives of the repository are static snapshots that cannot be automatically updated, track changes, or publish (push) through Git, while still allowing to modify the PARETO codebase locally.

1. Create and activate environment::

    conda create -n pareto-env python=3.9 pip --yes
    conda activate pareto-env

2. Download a ZIP file containing a snapshot of the ``main`` branch of the repository by navigating to the following URL: ``https://github.com/project-pareto/project-pareto/archive/refs/heads/main.zip``

   .. note::
    The URL can be modified to create a ZIP file for other repositories, branches or commits. e.g. for the fork belonging to the user ``myuser`` and the branch ``mybranch``, the URL would be ``https://github.com/myuser/project-pareto/archive/refs/heads/mybranch.zip``.

3. Unpack zip files (select directory)

4. Navigate to the directory where the ZIP files were extracted

5. Install pareto-project (non-git tracked repo)::

    pip install -r requirements-dev.txt

6. After installing PARETO, install the open-source solvers provided by the IDAES project::

    idaes get-extensions --verbose

