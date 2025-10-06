from types import SimpleNamespace

import pytest

from eshgham import Status, get_token, get_workflow_result


@pytest.mark.parametrize(
    "state,runs,status",
    [
        ("inactive", [], Status.INACTIVATED),
        ("active", [], Status.NO_SCHEDULED_RUNS),
        (
            "active",
            [SimpleNamespace(conclusion="failure", html_url="https://runs/fail")],
            Status.FAILED,
        ),
        (
            "active",
            [SimpleNamespace(conclusion="success", html_url="https://runs/success")],
            Status.OK,
        ),
    ],
)
def test_get_workflow_result(state, runs, status):
    workflow = SimpleNamespace(
        state=state,
        path=".github/workflows/ci.yml",
        html_url="https://github.com/owner/repo/blob/main/.github/workflows/ci.yml",
    )

    def get_runs(event):
        assert event == "schedule"
        return iter(runs)

    workflow.get_runs = get_runs

    repo = SimpleNamespace(full_name="owner/repo")

    def get_workflow(name):
        assert name == "ci.yml"
        return workflow

    repo.get_workflow = get_workflow

    result = get_workflow_result(repo, "ci.yml")

    assert result.repo == "owner/repo"
    assert result.workflow is workflow
    assert result.status is status
    if runs and status in {Status.FAILED, Status.OK}:
        assert result.last_scheduled_run == runs[0]
    else:
        assert result.last_scheduled_run is None


@pytest.mark.parametrize("source", ["cli", "yaml", "file", "env"])
def test_get_token(source, tmp_path, monkeypatch):
    workflow_dict = {}
    arg_token = None
    expected = f"{source}-token"

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    if source == "cli":
        workflow_dict["token"] = "yaml-token"
        arg_token = expected
    elif source == "yaml":
        workflow_dict["token"] = expected
    elif source == "file":
        token_file = tmp_path / ".githubtoken"
        token_file.write_text(expected)
    elif source == "env":
        monkeypatch.setenv("GITHUB_TOKEN", expected)

    token = get_token(arg_token, workflow_dict)

    assert token == expected
    assert "token" not in workflow_dict


def test_get_token_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ValueError):
        get_token(None, {})
