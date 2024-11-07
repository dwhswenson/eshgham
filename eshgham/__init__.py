#!/usr/bin/env python

import argparse
import enum
import json
import os
import re
import sys
import typing

import github
import yaml
from colorama import Fore

__all__ = [
    "Status", "Result", "Outputter", "JSONOutputter", "ColorOutputter",
    "Harness", "get_workflow_result" "attempt_to_reactivate" "get_token",
    "make_parser", "main", "make_json_ready"
]

from .version import short_version

class Status(enum.Enum):
    OK = 0
    INACTIVATED = 2
    FAILED = 1


class Result(typing.NamedTuple):
    repo: str
    workflow_name: str
    status: Status
    workflow: github.Workflow.Workflow
    last_scheduled_run: github.WorkflowRun.WorkflowRun

    @property
    def output_url(self):
        """URL for last run. For inactive workflow, URL of workflow"""
        if self.status is not Status.INACTIVATED:
            return self.last_scheduled_run.html_url

        # unfortuately, we kind of have to guess here; the URL we want isn't
        # included in API information for inactive workflows
        html_url = self.workflow.html_url
        repo = self.repo
        start = f"https://github.com/{repo}/blob"
        end = self.workflow.path
        if not (html_url.startswith(start) and html_url.endswith(end)):
            url = ("Unable to get actions URL for action at:\n  "
                   + html_url)
        else:
            file = end.split('/')[-1]
            url = f"https://github.com/{repo}/actions/workflows/{file}"

        return url


def get_workflow_result(
    repo: github.Repository.Repository,
    workflow_name: str
):
    """Create :class:`.Result` for a single workflow.
    """
    workflow = repo.get_workflow(workflow_name)
    if workflow.state != "active":
        status = Status.INACTIVATED
        last_scheduled_run = None
    else:
        last_scheduled_run = next(iter(workflow.get_runs(event='schedule')))
        if last_scheduled_run.conclusion != "success":
            status = Status.FAILED
        else:
            status = Status.OK

    return Result(
        repo=repo.full_name,
        workflow_name=workflow_name,
        status=status,
        workflow=workflow,
        last_scheduled_run=last_scheduled_run
    )


def attempt_to_reactivate(result):
    ...


def get_token(arg_token, workflow_dict):
    # order of precedence (first listed trumps anything below)
    # 1. CLI argument
    # 2. yaml config
    # 3. File ~/.githubtoken
    # 3. env var GITHUB_TOKEN
    token = None
    if 'token' in workflow_dict:
        token = workflow_dict.pop('token')
    if arg_token:
        token = arg_token
    if not token:
        token_file = os.path.expanduser("~/.githubtoken")
        if os.path.exists(token_file):
            with open(token_file) as file:
                token = file.read().strip()

    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("Missing 'token' parameter")
    return token

def make_parser():
    parser = argparse.ArgumentParser(
        prog="eshgham",
        description=(
            "ESHGHAM: The Executive Summarizer of Health for GitHub "
            "Actions Monitoring. "
            "A dashboard for your neglected GitHub Actions "
            f"workflows. Version {short_version}.")
    )
    parser.add_argument(
        'workflows_yaml', type=str,
        help=(
            "Workflows in YAML format. This is provided with repository "
            "'owner/repo_name' as a string key, and a list of workflow "
            "filenames as the value. The special key 'token' may be used "
            "for the GitHub personal access token."
        )
    )
    parser.add_argument(
        '--token', type=str,
        help=(
            "GitHub personal access token. May also be provided using "
            "'token' as a key in the workflow YAML file, or in the "
            "environment variable `GITHUB_TOKEN`. The command argument "
            "takes precedence, followed bythe environment variable, and "
            "finally the YAML specification."
        )
    )
    parser.add_argument(
        '--json', action="store_const", dest="runtype", const="json",
        default="color",
        help=(
            "Output as JSON instead of outputting to screen. The JSON "
            "object has keys 'OK', 'INACTIVATED', and 'FAILED', with a "
            "list of workflows as values. Each workflow "
            "has the repository name, the workflow name, and a URL. For "
            "passing/failing workflows, this URL points to the last run. "
            "For inactive workflows, the URL points to the workflow itself."
        )
    )
    parser.add_argument(
        '--exit-code', type=int, default=1,
        help=(
            "Exit code to return if there are any inactive/failing "
            "workflows. Runs with no inactive/failing workflows always "
            "exit with 0."
        )
    )
    return parser


class Outputter:
    """Abstract base for output handling with the :class:`.Harness`
    """
    def before_any(self):
        return None

    def before_repo(self, repo, workflow_names):
        return None

    def before_workflow(self, repo, workflow_name):
        return None

    def after_workflow(self, result):
        return None

    def after_repo(self, results):
        return None

    def after_all(self, results):
        return None

    def with_sorted_results(self, sorted_results):
        return None


class Harness:
    """Generic harness to loop over all workflows in a workflow dict.
    """
    def __init__(self, outputter: Outputter):
        self.out = outputter

    def __call__(
        self,
        gh: github.Github,
        workflow_dict: dict[str, list[str]]
    ):
        """
        """
        self.out.before_any()

        results = []

        for repo_name, workflow_list in workflow_dict.items():
            self.out.before_repo(repo_name, workflow_list)

            repo = gh.get_repo(repo_name)
            repo_results = []

            for workflow_name in workflow_list:
                self.out.before_workflow(repo_name, workflow_name)
                result = get_workflow_result(repo, workflow_name)
                self.out.after_workflow(result)
                repo_results.append(result)

            self.out.after_repo(repo_results)
            results.extend(repo_results)
        self.out.after_all(results)
        sorted_results = {Status.OK: [], Status.INACTIVATED: [],
                          Status.FAILED: []}
        for res in results:
            sorted_results[res.status].append(res)

        self.out.with_sorted_results(sorted_results)
        return sorted_results


def make_json_ready(grouped_results):
    def workflow_info(workflow):
        return {
            'repo': workflow.repo,
            'workflow_name': workflow.workflow_name,
            'url': workflow.output_url,
        }

    json_ready = {
        status.name: [workflow_info(w) for w in workflows]
        for status, workflows in grouped_results.items()
    }
    return json_ready


class JSONOutputter(Outputter):
    """Outputter for JSON output"""
    def with_sorted_results(self, sorted_results):
        json_ready = make_json_ready(sorted_results)
        print(json.dumps(json_ready))


class ColorOutputter(Outputter):
    """Outputter for colorama-based screen output"""
    @staticmethod
    def _wrap_status_color(text, status):
        color = {
            Status.OK: Fore.GREEN,
            Status.INACTIVATED: Fore.YELLOW,
            Status.FAILED: Fore.RED
        }[status]
        return f"{color}{text}{Fore.RESET}"

    def after_workflow(self, result):
        text = {
            Status.OK: "OK",
            Status.INACTIVATED: "INACTIVE",
            Status.FAILED: "FAIL"
        }[result.status]
        stylized = self._wrap_status_color(text, result.status)
        print(f"{result.repo}: {result.workflow_name}: {stylized}")

    def with_sorted_results(self, sorted_results):
        if inactives := sorted_results[Status.INACTIVATED]:
            print("\nLINKS TO INACTIVE WORKFLOWS")
            for result in inactives:
                print(f"* {result.repo}:{result.workflow_name} page:\n"
                      f"{result.output_url}")

        if failures := sorted_results[Status.FAILED]:
            print("\nLINKS TO FAILED RUNS")
            for result in failures:
                print(f"* {result.repo}:{result.workflow_name} failure: "
                      f"\n  {result.output_url}")

        total = sum(len(ll) for ll in sorted_results.values())

        def _summary_string(sorted_results, status, text):
            return self._wrap_status_color(
                f"{len(sorted_results[status])} {text}.",
                status
            )

        print(
            f"\nChecked {total} workflows. "
            + _summary_string(sorted_results, Status.OK, "passing") + " "
            + _summary_string(sorted_results, Status.INACTIVATED,
                              "inactive") + " "
            + _summary_string(sorted_results, Status.FAILED, "failing")
        )


def main() -> int:
    """Returns the exit code"""
    parser = make_parser()
    args = parser.parse_args()
    with open(args.workflows_yaml) as file:
        workflow_dict = yaml.load(file, Loader=yaml.FullLoader)

    token = get_token(args.token, workflow_dict)
    gh = github.Github(token)

    outputter = {
        'json': JSONOutputter(),
        'color': ColorOutputter(),
    }[args.runtype]

    runner = Harness(outputter)
    sorted_results = runner(gh, workflow_dict)

    # TODO: try to reactivate here?

    if sorted_results[Status.FAILED] or sorted_results[Status.INACTIVATED]:
        return args.exit_code

    return 0
