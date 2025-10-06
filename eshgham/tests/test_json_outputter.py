import json
from types import SimpleNamespace
from unittest.mock import Mock, call

import eshgham
from eshgham import (
    JSONOutputter,
    Result,
    Status,
    make_json_ready,
)


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


def test_make_json_ready():
    ok = _make_result(Status.OK, run_url="https://runs/ok")
    inactive = _make_result(Status.INACTIVATED)
    grouped = {
        Status.OK: [ok],
        Status.INACTIVATED: [inactive],
        Status.FAILED: [],
        Status.NO_SCHEDULED_RUNS: [],
    }

    json_ready = make_json_ready(grouped)

    assert json_ready == {
        "OK": [
            {
                "repo": ok.repo,
                "workflow_name": ok.workflow_name,
                "url": ok.output_url,
            }
        ],
        "INACTIVATED": [
            {
                "repo": inactive.repo,
                "workflow_name": inactive.workflow_name,
                "url": inactive.output_url,
            }
        ],
        "FAILED": [],
        "NO_SCHEDULED_RUNS": [],
    }


class TestJSONOutputter:
    def test_with_sorted_results(self, capsys):
        ok = _make_result(Status.OK, run_url="https://runs/ok")
        sorted_results = {
            Status.OK: [ok],
            Status.INACTIVATED: [],
            Status.FAILED: [],
            Status.NO_SCHEDULED_RUNS: [],
        }

        JSONOutputter().with_sorted_results(sorted_results)

        expected = json.dumps(make_json_ready(sorted_results))
        captured = capsys.readouterr()
        assert captured.out.strip() == expected
