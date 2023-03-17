Getting Started
===============

.. _PARETO Installation:

Installation
------------

To install the PARETO framework on Windows operating systems, follow the set of instructions below
that are appropriate for your needs. If you need assistance please contact start a new discussion on
our `GitHub Discussion form <https://github.com/project-pareto/project-pareto/discussions>`_ or send
an email to `pareto-support@project-pareto.org <mailto: pareto-support@project-pareto.org>`_.

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

2. Clone your fork locally, with only one of the following commands, creating a
   workspace (replacing ``<githubid>`` with your github user id)::

    git clone https://github.com/<githubid>/project-pareto
    git clone git@github.com:<githubid>/project-pareto

3. In this new project-pareto directory, run the following command which
   installs PARETO in editable mode so that developers can make changes and
   push to their fork/branch::

    pip install -e .

.. _min_install_hybrid:

Hybrid
-------
**User that can edit the base code**

1. Create environment::

    conda create -n pareto-env python=3.8 pip --yes
    conda activate pareto-env

2. Download zip files (project-pareto-main)

3. Unpack zip files (select directory)

4. Install pareto-project (non-git tracked repo)::

    pip install -r requirements-dev.txt

Building Documentation
----------------------

We use `Sphinx <https://www.sphinx-doc.org/>`_ for writing and building our on-line documentation.
This is a tool that translates a set of plain text `.rst` (`reStructuredText
<https://docutils.sourceforge.io/rst.html>`_) files into various output formats, such as HTML or PDF
(via Latex).

After installing as a :ref:`min_install_core-dev` or :ref:`min_install_users` (as described above)
you can build the documentation locally on your system by running the `make` command in the `docs`
folder, as follows::

    $ cd project-pareto/docs/
    $ make html

Visit the `Sphinx Style Guide <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_ for information on
syntax rules, tips, and FAQ.
