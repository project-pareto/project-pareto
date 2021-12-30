# stagedfright: Pre-commit detection of sensitive files

## Introduction

The main goal of this tool is to prevent sensitive files (SF) from being **unintentionally** committed to a Git repository.

### How it works

- Staged files are files that have been added to the Git index (a.k.a. *staging area*) by commands such as `git add` (aliased to `git stage` for recent versions of Git).
- When the script is installed as a pre-commit hook (see below), it will be run automatically by Git when a commit is initiated by the user, e.g. invoking the `git commit` command.
- The commit will be blocked (i.e. the `git commit` will terminate with an error, and no file will be committed) unless all of the staged files are *cleared for commit* by the script.

### Inspecting staged files

- By design, any staged file is considered *unguarded* by default and is only cleared for commit after passing all of the specified checks
- A staged file is cleared for commit if **either** of these condition is true:
  - The file passes all the checks defined in the `checks.py` file in this directory
  - A special *allowfile* is found in the repository. The allowfile must have the following properties:
    - It must be located in the same directory as the staged file
    - Its name must match the staged file's name, plus the special *allowfile suffix* `.stagedfright-allowed`
    - It must be a text file containing the staged file's fingerprint, defined as the SHA256 hash of the staged file's byte contents

For a more detailed breakdown of this script's limitations and capabilities, continue to the "Functionality" section.

## Getting started

**IMPORTANT** As this is still experimental, it is recommended to use a separate local clone of the repository to be used for testing, e.g. by doing a fresh `git clone` in a dedicated directory.

### Installing as a pre-commit hook

stagedfright is installed automatically as part of the `project-pareto` Python installation.

To use stagedfright as a pre-commit hook, PARETO developers can run this command in their developer environment after installing the developer dependencies defined in `requirements-dev.txt`:

```sh
pre-commit install
```

### Testing the script

1. Activate your development Conda environment
2. Navigate to the local clone of the repository to be used for testing
3. Create or modify files as needed to reproduce the desired scenario involving SFs ending up in the repo's working tree
4. Stage those changes using `git add`/`git stage`
5. Try to commit using `git commit`. The script should run, resulting in its output being displayed and (if needed) the commit being cancelled
6. To remove the staged files, use `git reset`/`git restore` (refer to [this How-To guide](https://git-scm.com/book/en/v2/Git-Basics-Undoing-Things) for more information)

## Functionality

If we think of stagedfright as a *filter* operating on staged files with the goal of detecting SFs, we can classify possible scenarios according to the following schema, based on whether an SF was set to be added to the repo (positive) or not (negative), and whether the commit operation was allowed to continue (GO) or not (NO GO).

- **True positive**: an SF was set to be added to the repo, and the operation was NO GO
- **False positive**: no SF was set to be added to the repo, but the operation was NO GO
- **True negative**: no SF was set to be added to the repo, and the operation was GO
- **False negative**: an SF was set to be added to the repo, but the operation was GO

In this perspective, the performance of this tool can be evaluated based on how well it satisfies the following requirements, in order of descending importance:

- Minimize **false negatives**
- Minimize **false positives**

### True positives

> Desired outcome: NO GO, actual outcome: NO GO

By design (i.e. if this is not true, it's a bug), the checks should be able to detect
 the following SFs after they end up in the repo and are staged:

- A binary file with a non-`py` extension 
  - **NO GO**: fails `has_py_path_suffix`
- A binary file accidentally saved with a `py` extension
  - **NO GO**: passes `has_py_path_suffix` but fails `is_text_file`
- A text file in a non-Python format (e.g. CSV, JSON) accidentally saved under a filename with `py` extension
  - **NO GO**: passes `has_py_path_suffix` and `is_text_file`, but fails `has_meaningful_python_code`
- A Python source file containing hard-coded data definitions of numerical data
  - **NO GO**: fails `py_module_does_not_contain_hardcoded_data` **if** the maximum number of allowed data definitions
    is required to be sufficiently low

### True negatives

> Desired outcome: GO, actual outcome: GO

By design, the checks should pass for the following staged files that are intended to be staged and committed:

- A binary file, after the corresponding allowfile has been created
  - **GO**, **if** the allowfile's content matches the current fingerprint (SHA256 has) of the staged file
- A normal python source file
  - **GO**, **if** the hardcoded data defined in it are below the maximum value required by the `py_module_does_not_contain_hardcoded_data` check

### False positives

> Desired outcome: GO, actual outcome: NO GO

These scenarios occur when a file was supposed to be cleared for commit (i.e. is not an SF),
but was erroneously flagged as unguarded.

In general, stagedfright operates under a "presumption of guilt" principle:
each staged file is considered unguarded (potentially sensitive) until proven otherwise.
In this sense, any staged file that is not actually sensitive but is not a Python source file with the characteristics described above
will result in a NO GO commit outcome by default.
This can be considered a "baseline" false positive resulting from 
the fundamental strictness/convenience tradeoff under which stagedfright operates.

To get around this and allow developers to stage and commit a desired file without bypassing the checks entirely,
stagedfright uses *allowfiles*, a sentinel file named after the staged file that informs stagedfright that the file has been staged intentionally.

To reduce the possibility of false negatives, allowfiles must match certain criteria to be detected correctly.
If an allowfile was created but does not match any of these criteria, the commit outcome will be NO GO even though
the developer intended the file to be committed.

In this sense, the following cases would be false positives in a stricter sense,
although this is still completely within stagedfright's intended behavior.
Assuming that the file to be commited is `pareto/data/sample-data.csv`:

- The allowfile `pareto/data/sample-data.stagedfright-allowed` exists
  - **NO GO**: the allowfile's name must contain the full name of the staged file, including its original extension
- The allowfile `pareto/sample-data.csv.stagedfright-allowed` exists
  - **NO GO**: the allowfile must be placed in the same subdirectory as the staged file
- The allowfile `pareto/data/sample-data.csv.stagedfright-allowed` exists, but is empty
  - **NO GO**: the allowfile must contain a string that matches the staged file's current fingerprint,
    defined as the SHA256 hash of the file's binary content
  - The current fingerprint can be obtained by running the `sha256sum <path>` command on Unix or `CertUtil -hashfile <path> SHA256` on Windows
- The allowfile `pareto/data/sample-data.csv.stagedfright-allowed` exists and contains a SHA256 hash,
  but the staged file has been modified since the hash was computed, i.e. the allowfile contains an outdated fingerprint
  for the staged file
  - **NO GO**: the fingerprint in the allowfile must match the staged file's *current* content
  - To address this, compute again the staged file's fingerprint and modify or recreate the allowfile with the new value

**NOTE**: As a convenience, at the end of the inspection procedure, stagedfright will display the list of unguarded staged files together with the name of the allowfile and the fingerprint, which can be used to (manually, by design) create the allowfile
  
### False negatives

> Desired outcome: NO GO, actual outcome: GO

By design (i.e., again, assuming stagedfright operates as intended), sensitive data can still make its way in the repository in two general scenarios:

- Sensitive data is inserted in a Python source file that passes all of stagedfright's checks: the definition of "sensitive data" is very broad and can potentially include e.g. a single number or string, which would pass the current check for hardcoded numeric constants defined in a Python module
  - To mitigate this, the checks and their parameters should be carefully designed and optimized based on the expected features of sensitive data being handled, while keeping in mind that stricter selection criteria typically results in an increase of false positives over true negatives
- Wrong allowfile being created: for example, if the repo contains both `a.txt` (which should be committed) and `b.txt` (which should not be committed), the allowfile `b.txt.stagedfright-allowed` exists and it contains the correct fingerprint for `b.txt`, then if `b.txt` is staged and the commit operation will not be blocked

## Limitations

Last but not least, it is important to remark that stagedfright can only be effective if it is correctly configured in the repo, and, more importantly that there are still countless scenarios that stagedfright is unable to prevent.

The best way to think about stagedfright is as one among many many layers of protection in the "swiss cheese" model of incident prevention, for which following the protocol is critical for optimal performance.
