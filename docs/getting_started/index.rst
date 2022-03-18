Getting Started
===============

.. _PARETO Installation:

Installation
------------
To install the PARETO framework on Windows operating systems, follow the set
of instructions below that are appropriate for your needs. If you need assistance
please contact `pareto-support@pareto.org`.

**Users**: Use the PARETO platform to develop models, but never contribute to
development of the framework (i.e. never commit changes to the project-pareto
repo). This includes people who only work with protected data.

**Core-dev**: Work primarily on PARETO platform development and never handle
protected data.

**Hybrid**: Handle protected data, but also commit changes to the project-pareto
repo (even occasionally) - needs approval from PhD. Markus Drouven

+------------------+-----------------------------+
| Developer Role   | Section                     |
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

1. Install PARETO with pip by one of the following methods

  a. To get the latest release::

      pip install project-pareto

  b. To get a specific release, for example 1.6.3::

      pip install project-pareto==1.6.3

  c. If you need unreleased cutting-edge development versions of PARETO, you
     can install PARETO directly from the GitHub repo either from the main
     PARETO repo or a developer's fork and branch (this installs from GitHub
     but does not create a local git clone/workspace)::

      pip install git+https://github.com/project-pareto/project-pareto.git
      pip install git+https://github.com/ksbeattie/project-pareto@feature_1

.. _min_install_core-dev:

Core-dev
--------

1. Fork the repo on GitHub (your copy of the main repo)

2. Clone your fork locally, creating a workspace (github id is "myusername,")::

    git clone https://github.com/myusername/project-pareto
    git clone git@github.com:myusername/project-pareto.

3. In this new project-pareto directory, run the following command which
   installs PARETO in editable mode so that developers can make changes and
   push to their fork/branch::

    pip install -e

.. _min_install_hybrid:

Hybrid
-------
**User that can edit the base code**

1. Create environment::

    conda create -n pareto-env python=3.8pip --yes
    conda activate pareto-env

2. Download zip files (project-pareto-main)

3. Unpack zip files (select directory)

4. Install pareto-project (non-git tracked repo)::

    pip install -r requirements-dev.txt

Building Documentation
----------------------

A convenient way of building documentation is to use Sphinx,
which is able to translate a set of plain text source files into various output formats, such as a series HTML or PDF (via Latex) files.
In addition to following the `Sphinx Quickstart <https://www.sphinx-doc.org/en/master/usage/quickstart.html>`_
and `Installation Guide <https://www.sphinx-doc.org/en/master/usage/installation.html>`_,
the following libraries are needed in order to use Sphinx (these packages have been included in the requirements-dev.txt file).::

    pip install -U sphinx

    pip install myst-parser

    pip install sphinx_rtd_theme

    pip install nbsphinx

To build the project documentation locally in your system, users must go to the docs folder and run the make file::

    $ cd project-pareto/docs/

    $ make html

Visit the `Sphinx Style Guide <https://gdal.org/contributing/rst_style.html>`_ for information on syntax rules, tips, and FAQ.
