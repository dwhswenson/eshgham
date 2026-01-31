# Tests for the models classes: Status and Result

from types import SimpleNamespace

import pytest

from eshgham import Result, Status


class TestResult:
    @pytest.mark.parametrize("status", [Status.OK, Status.FAILED])
    def test_output_url_uses_run_link(self, status):
        run_url = "https://github.com/owner/repo/actions/runs/42"
        result = Result(
            repo="owner/repo",
            workflow_name="ci",
            status=status,
            workflow=SimpleNamespace(
                html_url="unused", path=".github/workflows/ci.yml"
            ),
            last_scheduled_run=SimpleNamespace(html_url=run_url),
        )

        assert result.output_url == run_url

    @pytest.mark.parametrize("status", [Status.INACTIVATED, Status.NO_SCHEDULED_RUNS])
    def test_output_url_builds_workflow_link(self, status):
        repo = "owner/repo"
        workflow_path = ".github/workflows/ci.yml"
        workflow = SimpleNamespace(
            html_url=f"https://github.com/{repo}/blob/main/{workflow_path}",
            path=workflow_path,
        )
        result = Result(
            repo=repo,
            workflow_name="ci",
            status=status,
            workflow=workflow,
            last_scheduled_run=None,
        )

        expected = f"https://github.com/{repo}/actions/workflows/ci.yml"
        assert result.output_url == expected

    def test_output_url_missing_expected_structure(self):
        workflow = SimpleNamespace(
            html_url="https://example.com/workflow.yml", path="ci.yml"
        )
        result = Result(
            repo="owner/repo",
            workflow_name="ci",
            status=Status.INACTIVATED,
            workflow=workflow,
            last_scheduled_run=None,
        )

        assert "Unable to get actions URL" in result.output_url
