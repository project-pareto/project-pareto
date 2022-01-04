import ast
import collections
from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Optional, Union, Iterable, Iterator, List, Tuple

import pytest
from _pytest.terminal import TerminalReporter


NAME = "stagedfright"
__version__ = "2021.12.20"
__author__ = "Ludovico Bianchi <lbianchi@lbl.gov>"


_logger = logging.getLogger(NAME)


ALLOWFILE_SUFFIX = ".stagedfright-allowed"


class RepoOperationError(RuntimeError):
    @classmethod
    def from_subprocess_run(cls, completed_process):
        return cls(
            f"Repository operation with args {completed_process.args} did not succeed.\n"
            f"returncode={completed_process.returncode}\n"
            f"stderr={completed_process.stderr}"
        )


def _get_git_output(args: Iterable[str], git_exe: os.PathLike = "git") -> str:
    args = [git_exe] + list(args)
    _logger.debug(f"subprocess args: {args}")
    res = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if res.returncode != 0:
        raise RepoOperationError.from_subprocess_run(res)
    return res.stdout


def get_repo_root_dir() -> Path:
    try:
        path = _get_git_output(["rev-parse", "--show-toplevel"]).strip()
    except RepoOperationError as e:
        _logger.exception("Could not obtain repository root from git.")
        raise e
    return Path(path).resolve()


def get_git_staged_paths() -> List[Path]:
    try:
        lines = _get_git_output(["diff", "--staged", "--name-only"]).splitlines()
    except RepoOperationError as e:
        _logger.exception("Could not get staged files from git.")
        raise e

    return [Path(p) for p in lines]


_BasePathType = type(Path())


class StagedFile(_BasePathType):
    @property
    def fingerprint(self) -> str:
        h = hashlib.sha256()
        h.update(self.read_bytes())
        return h.hexdigest()

    @property
    def text_content(self) -> Union[str, None]:
        try:
            return self.read_text()
        except UnicodeDecodeError:
            return None

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> Iterator["StagedFile"]:
        for path in paths:
            if not path.is_file():
                _logger.warning(
                    f'Trying to instantiate {cls} from "{path}", but it is not an existing file'
                )
            else:
                yield cls(path)

    @classmethod
    def from_git_staged(cls) -> Iterator["StagedFile"]:
        yield from cls.from_paths(get_git_staged_paths())


class AllowFile(_BasePathType):
    @classmethod
    def from_path(cls, path: Path) -> "AllowFile":
        return cls(path.with_name(path.name + ALLOWFILE_SUFFIX))

    @property
    def fingerprint(self) -> str:
        return self.read_text().strip()


@dataclass
class ASTNodes:
    @classmethod
    def from_source(cls, src: str, **kwargs):
        return cls(root=ast.parse(src), **kwargs)

    root: ast.AST
    essential_types: Optional[Tuple[type]] = (ast.Assign, ast.Import, ast.ImportFrom)
    literal_types: Optional[Tuple[type]] = ast.Constant

    essential: Optional[List[ast.AST]] = None
    literal: Optional[List[ast.AST]] = None

    def __iter__(self):
        yield from ast.walk(self.root)

    def __post_init__(self):
        self.essential = [n for n in self if isinstance(n, self.essential_types)]
        self.literal = [n for n in self if isinstance(n, self.literal_types)]

    @property
    def literal_values(self) -> List:
        return [n.value for n in self.literal]


@dataclass
class PyContent:
    source: str
    ast_nodes: Optional[ASTNodes] = None
    objects: Optional[dict] = None

    def __post_init__(self):
        if self.ast_nodes is None:
            self.ast_nodes = ASTNodes.from_source(self.source)


class StagedFright:
    def __init__(self, items=None):
        self.test_reports = collections.defaultdict(list)
        self._items = list(items or [])
        self.current = None

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_makereport(self, item, call) -> None:
        outcome = yield
        rep = outcome.get_result()
        self.test_reports[self.current].append(rep)

    def pytest_generate_tests(self, metafunc) -> None:
        # if
        if "staged" in metafunc.fixturenames:
            metafunc.parametrize("staged", self._items, ids=str, indirect=True)

    @pytest.fixture(scope="module")
    # @pytest.fixture(scope="module", params=list(StagedFile.from_git_staged()), ids=os.fspath)
    def staged(self, request) -> StagedFile:
        staged = request.param
        self.current = staged
        yield staged

    @pytest.fixture
    def skip_if_matching_allowfile(self, staged: StagedFile) -> None:
        allowfile = AllowFile.from_path(staged)
        if not allowfile.exists():
            return
        if staged.fingerprint == allowfile.fingerprint:
            pytest.skip(f'Matching allowfile found for "{staged}"')

    @pytest.fixture
    def allowfile(self, staged: StagedFile) -> AllowFile:
        af = AllowFile.from_path(staged)
        if not af.exists():
            pytest.skip(f"No allowfile found for {staged}")
        return af

    @pytest.fixture
    def staged_pycontent(self, staged: StagedFile) -> PyContent:
        if staged.text_content is None:
            pytest.xfail(f"{staged} is not a text file")
        return PyContent(staged.text_content)

    @property
    def with_failing_tests(self) -> List:
        return [
            entry
            for entry, reports in self.test_reports.items()
            if not all([rep.outcome in {"passed", "skipped"} for rep in reports])
        ]

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        tr = terminalreporter
        tr.section(NAME)

        to_report = self.with_failing_tests
        if not to_report:
            tr.write_line("No failed checks among the inspected staged files.")
            return

        tr.write_line(
            f"The following {len(to_report)} inspected staged file(s) failed one or more checks:"
        )
        for staged in to_report:
            tr.write_line(f"\t{staged}")

        tr.write_line(
            "For each of these files, REVIEW IT CAREFULLY:"
            "\n- If it *SHOULD NOT* be cleared for commit, unstage it immediately."
            "\n- If instead it should, create an allowfile in the same directory, "
            f'with the same name (including file extension) plus the "{ALLOWFILE_SUFFIX}" suffix, '
            "containing the fingerprint (SHA256 hash) of the file."
        )

        tr.ensure_newline()
        tr.write_line("\te.g.:")
        for staged in self.with_failing_tests:
            allowfile = AllowFile.from_path(staged)
            tr.write_line(
                f'\tFor staged file "{staged}", create "{allowfile}" with content: {staged.fingerprint}'
            )


def pytest_run(
    to_inspect: Iterable[Path],
    testpath: os.PathLike,
    verbose: bool = True,
    ignore_ini_file: bool = True,
    collect_all: bool = True,
) -> pytest.ExitCode:

    items = list(StagedFile.from_paths(to_inspect))

    testpath = Path(testpath).resolve()

    _logger.info(
        f"Inspecting {len(items)} staged items using checks collected from {testpath}"
    )

    sf = StagedFright(items)

    pytest_args = [
        os.fspath(testpath),
        "-s",
    ]

    if collect_all:
        pytest_args += ["-o", "python_files=*.py"]

    if ignore_ini_file:
        null_target = "NUL" if sys.platform.startswith("win") else "/dev/null"
        pytest_args += ["-c", null_target]

    pytest_args += ["-v"] if verbose else ["-qq"]

    _logger.debug(f"Calling pytest.main with args: {pytest_args}")

    return pytest.main(
        pytest_args,
        plugins=[sf],
    )


class ExitCode:
    no_unguarded_detected: int = 0
    unguarded_detected: int = 1
    internal_error: int = 2
    no_inspection_performed: int = 5


def notify_exit(code: int, log: Callable[[str], None] = _logger.info):
    log(f"{NAME} will now exit with code: {code}")
    return code


def main(args: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.DEBUG)

    _logger.info(f"{NAME}, version: {__version__}")

    args = args or sys.argv[1:]
    _logger.debug(f"args={args}")

    try:
        root_dir = get_repo_root_dir()
    except RepoOperationError:
        _logger.critical("Could not determine the root of the repository. ")
        return notify_exit(ExitCode.internal_error)
    else:
        _logger.info(f"Starting inspection for repository directory: {root_dir}")

    try:
        staged_paths = get_git_staged_paths()
    except RepoOperationError:
        _logger.critical(f"Could not determine staged files for this repository.")
        return notify_exit(ExitCode.internal_error)
    else:
        _logger.info(f"{len(staged_paths)} items are currently staged")
        if _logger.isEnabledFor(logging.DEBUG):
            for path in staged_paths:
                _logger.debug(f"\t{path}")

    if not staged_paths:
        _logger.warning(f"No staged files detected.")
        return notify_exit(ExitCode.no_inspection_performed)

    # TODO add properly parsed arguments
    testfile = args[0]

    try:
        pytest_run_res = pytest_run(staged_paths, testfile, verbose=True)
    except Exception as e:
        _logger.exception("Unexpected error occurred during inspection.")
        _logger.critical(
            "Inspection could not be completed because of an internal error."
        )
        return notify_exit(ExitCode.internal_error)

    _logger.debug(f"pytest run result: {pytest_run_res}")
    _logger.info("Inspection completed successfully.")

    if pytest_run_res == 0:
        _logger.info("No unguarded files have been detected.")
        return notify_exit(ExitCode.no_unguarded_detected)

    _logger.error("Unguarded files have been detected.")
    return notify_exit(ExitCode.unguarded_detected)


if __name__ == "__main__":
    sys.exit(main())
