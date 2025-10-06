from types import SimpleNamespace

import pytest
from colorama import Fore

from eshgham import ColorOutputter, Result, Status


def _make_result(status, *, repo="owner/repo", workflow_name="ci", run_url=None):
    workflow_path = f".github/workflows/{workflow_name}.yml"
    workflow = SimpleNamespace(
        html_url=f"https://github.com/{repo}/blob/main/{workflow_path}",
        path=workflow_path,
    )
    last_run = None
    if status in {Status.OK, Status.FAILED}:
        run_url = run_url or f"https://github.com/{repo}/actions/runs/{workflow_name}"
        last_run = SimpleNamespace(html_url=run_url)
    return Result(
        repo=repo,
        workflow_name=workflow_name,
        status=status,
        workflow=workflow,
        last_scheduled_run=last_run,
    )


class TestColorOutputter:
    @pytest.mark.parametrize(
        "status,expected_text,expected_color",
        [
            (Status.OK, "OK", Fore.GREEN),
            (Status.INACTIVATED, "INACTIVE", Fore.YELLOW),
            (Status.FAILED, "FAIL", Fore.RED),
            (Status.NO_SCHEDULED_RUNS, "NO SCHEDULED RUNS", Fore.YELLOW),
        ],
    )
    def test_after_workflow_parametrized(
        self, capsys, status, expected_text, expected_color
    ):
        result = _make_result(
            status,
            workflow_name="build",
            run_url="https://github.com/owner/repo/actions/runs/123"
            if status in {Status.OK, Status.FAILED}
            else None,
        )

        ColorOutputter().after_workflow(result)

        captured = capsys.readouterr().out
        expected = f"{result.repo}: {result.workflow_name}: {expected_color}{expected_text}{Fore.RESET}\n"
        assert captured == expected

    def test_after_workflow(self, capsys):
        result = _make_result(
            Status.FAILED,
            workflow_name="build",
            run_url="https://github.com/owner/repo/actions/runs/123",
        )

        ColorOutputter().after_workflow(result)

        captured = capsys.readouterr().out
        expected = (
            f"{result.repo}: {result.workflow_name}: {Fore.RED}FAIL{Fore.RESET}\n"
        )
        assert captured == expected

    def test_with_sorted_results(self, capsys):
        ok = _make_result(Status.OK, run_url="https://runs/ok")
        inactive = _make_result(Status.INACTIVATED, workflow_name="slow")
        failing = _make_result(
            Status.FAILED, workflow_name="lint", run_url="https://runs/lint"
        )

        sorted_results = {
            Status.OK: [ok],
            Status.INACTIVATED: [inactive],
            Status.FAILED: [failing],
            Status.NO_SCHEDULED_RUNS: [],
        }

        ColorOutputter().with_sorted_results(sorted_results)

        out = capsys.readouterr().out
        assert "LINKS TO INACTIVE WORKFLOWS" in out
        assert (
            f"* {inactive.repo}:{inactive.workflow_name} page:\n{inactive.output_url}"
        ) in out
        assert "LINKS TO FAILED RUNS" in out
        assert (
            f"* {failing.repo}:{failing.workflow_name} failure: \n  "
            f"{failing.output_url}"
        ) in out
        assert "Checked 3 workflows." in out
        assert f"{Fore.GREEN}1 passing.{Fore.RESET}" in out
        assert f"{Fore.YELLOW}1 inactive.{Fore.RESET}" in out
        assert f"{Fore.RED}1 failing.{Fore.RESET}" in out
