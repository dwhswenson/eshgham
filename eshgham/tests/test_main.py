import json
import sys
from dataclasses import dataclass

import github
import pytest
import yaml

import eshgham
from eshgham import Status


@dataclass
class FakeRun:
    conclusion: str
    html_url: str


class FakeWorkflow:
    def __init__(
        self,
        repo_full_name,
        filename,
        *,
        state,
        runs,
        enable_behavior=False,
    ):
        self.state = state
        self.path = f".github/workflows/{filename}"
        self.html_url = f"https://github.com/{repo_full_name}/blob/main/{self.path}"
        self._runs = runs
        self._enable_behavior = enable_behavior

    def get_runs(self, event):
        assert event == "schedule"
        return iter(self._runs)

    def enable(self):
        if isinstance(self._enable_behavior, Exception):
            raise self._enable_behavior
        return self._enable_behavior


class FakeRepo:
    def __init__(self, full_name, workflows):
        self.full_name = full_name
        self._workflows = workflows

    def get_workflow(self, name):
        return self._workflows[name]


class FakeGithub:
    def __init__(self, token, repos):
        self.token = token
        self._repos = repos

    def get_repo(self, repo_name):
        return self._repos[repo_name]


@pytest.mark.parametrize("output_format", ["json", "color", "quiet"])
def test_main(output_format, tmp_path, monkeypatch, capsys):
    repo_full_name = "owner/repo"
    workflows = {
        "ci.yml": FakeWorkflow(
            repo_full_name,
            "ci.yml",
            state="active",
            runs=[FakeRun("success", "https://runs/ci")],
        ),
        "lint.yml": FakeWorkflow(
            repo_full_name,
            "lint.yml",
            state="active",
            runs=[FakeRun("failure", "https://runs/lint")],
        ),
        "docs.yml": FakeWorkflow(
            repo_full_name,
            "docs.yml",
            state="inactive",
            runs=[],
        ),
    }
    fake_repo = FakeRepo(repo_full_name, workflows)

    fake_repos = {repo_full_name: fake_repo}

    def fake_github_factory(token):
        return FakeGithub(token, fake_repos)

    monkeypatch.setattr(eshgham.github, "Github", fake_github_factory)

    workflow_yaml = {repo_full_name: list(workflows.keys())}
    workflow_file = tmp_path / "workflows.yml"
    workflow_file.write_text(yaml.safe_dump(workflow_yaml))

    argv = [
        "eshgham",
        str(workflow_file),
        "--token",
        "cli-token",
        "--exit-code",
        "7",
    ]
    if output_format == "json":
        argv.append("--json")
    elif output_format == "quiet":
        argv.append("--quiet")

    monkeypatch.setattr(sys, "argv", argv)

    exit_code = eshgham.main()
    captured = capsys.readouterr()

    assert exit_code == 7

    if output_format == "json":
        payload = json.loads(captured.out)
        assert payload[Status.OK.name][0]["url"] == "https://runs/ci"
        assert payload[Status.FAILED.name][0]["url"] == "https://runs/lint"
        assert payload[Status.INACTIVATED.name][0]["url"].endswith("docs.yml")
    elif output_format == "color":
        out = captured.out
        assert f"{repo_full_name}: ci.yml:" in out
        assert f"{repo_full_name}: lint.yml:" in out
        assert "LINKS TO INACTIVE WORKFLOWS" in out
        assert "LINKS TO FAILED RUNS" in out
        assert "Checked 3 workflows." in out
    else:
        assert captured.out == ""
    assert captured.err == ""


def test_main_all_ok_returns_zero(tmp_path, monkeypatch, capsys):
    repo_full_name = "owner/repo"
    workflows = {
        "ci.yml": FakeWorkflow(
            repo_full_name,
            "ci.yml",
            state="active",
            runs=[FakeRun("success", "https://runs/ci")],
        ),
    }
    fake_repo = FakeRepo(repo_full_name, workflows)

    fake_repos = {repo_full_name: fake_repo}

    def fake_github_factory(token):
        return FakeGithub(token, fake_repos)

    monkeypatch.setattr(eshgham.github, "Github", fake_github_factory)

    workflow_yaml = {repo_full_name: list(workflows.keys())}
    workflow_file = tmp_path / "workflows.yml"
    workflow_file.write_text(yaml.safe_dump(workflow_yaml))

    argv = [
        "eshgham",
        str(workflow_file),
        "--token",
        "cli-token",
        "--json",
    ]

    monkeypatch.setattr(sys, "argv", argv)

    exit_code = eshgham.main()
    captured = capsys.readouterr()

    assert exit_code == 0

    payload = json.loads(captured.out)
    assert payload[Status.OK.name][0]["url"] == "https://runs/ci"
    assert payload[Status.FAILED.name] == []
    assert payload[Status.INACTIVATED.name] == []
    assert payload[Status.NO_SCHEDULED_RUNS.name] == []
    assert captured.err == ""


def test_main_reenabled_workflow_returns_zero(tmp_path, monkeypatch, capsys):
    repo_full_name = "owner/repo"
    workflows = {
        "docs.yml": FakeWorkflow(
            repo_full_name,
            "docs.yml",
            state="inactive",
            runs=[],
            enable_behavior=True,
        ),
    }
    fake_repo = FakeRepo(repo_full_name, workflows)

    fake_repos = {repo_full_name: fake_repo}

    def fake_github_factory(token):
        return FakeGithub(token, fake_repos)

    monkeypatch.setattr(eshgham.github, "Github", fake_github_factory)

    workflow_yaml = {repo_full_name: list(workflows.keys())}
    workflow_file = tmp_path / "workflows.yml"
    workflow_file.write_text(yaml.safe_dump(workflow_yaml))

    argv = [
        "eshgham",
        str(workflow_file),
        "--token",
        "cli-token",
        "--json",
    ]

    monkeypatch.setattr(sys, "argv", argv)

    exit_code = eshgham.main()
    captured = capsys.readouterr()

    assert exit_code == 0

    payload = json.loads(captured.out)
    assert payload[Status.REENABLED.name][0]["url"].endswith("docs.yml")
    assert payload[Status.INACTIVATED.name] == []
    assert payload[Status.FAILED.name] == []
    assert captured.err == ""


def test_main_enable_exception_marks_inactivated(tmp_path, monkeypatch, capsys):
    repo_full_name = "owner/repo"
    workflows = {
        "docs.yml": FakeWorkflow(
            repo_full_name,
            "docs.yml",
            state="inactive",
            runs=[],
            enable_behavior=github.GithubException(
                403,
                {"message": "rate limited"},
                None,
            ),
        ),
    }
    fake_repo = FakeRepo(repo_full_name, workflows)

    fake_repos = {repo_full_name: fake_repo}

    def fake_github_factory(token):
        return FakeGithub(token, fake_repos)

    monkeypatch.setattr(eshgham.github, "Github", fake_github_factory)

    workflow_yaml = {repo_full_name: list(workflows.keys())}
    workflow_file = tmp_path / "workflows.yml"
    workflow_file.write_text(yaml.safe_dump(workflow_yaml))

    argv = [
        "eshgham",
        str(workflow_file),
        "--token",
        "cli-token",
        "--json",
        "--exit-code",
        "7",
    ]

    monkeypatch.setattr(sys, "argv", argv)

    with pytest.warns(UserWarning, match="Unable to re-enable workflow docs.yml"):
        exit_code = eshgham.main()
    captured = capsys.readouterr()

    assert exit_code == 7

    payload = json.loads(captured.out)
    assert payload[Status.INACTIVATED.name][0]["url"].endswith("docs.yml")
    assert payload[Status.REENABLED.name] == []
    assert captured.err == ""
