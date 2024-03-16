# ESHGHAM

*The Executive Summarizer of Health for GitHub Actions Monitoring (ESHGHAM,
which is also a Farsi term of endearment translating as "my love") is a
dashboard to check on the status of your neglected GitHub Actions.*

Do you maintain a lot of GitHub repositories? Projects you want to keep alive,
even if they aren't very active?

Do you worry that you'll miss one of the warning emails GitHub sends you when a
scheduled workflow becomes inactive? Have you missed them before, only
discovering that CI hadn't been running for months after a user complained
about incompatibility with a new release of a dependency?

Do you worry that a colleague may be responsible for the latest merge, and
could be ignoring notifications of failing CI?

**Then ESGHAM is for you!**

ESHGHAM is a little command line utility to check on your scheduled workflows.

Here's what it looks like in practice:

![The command eshgham config.yaml tells if your GitHub actions are inactive or
failing](eshgham.gif)

When workflows are failing or inactive, the summary ends with links for failing
or inactive workflows. For failing workflows, this will link to a report of the
failing workflow run. For inactive workflows, this will link to the workflow
page where you can click the "Enable Workflow" button to reactivate it.

## Installation

```text
python -m pip install eshgham
```

## Usage

```text
usage: eshgham [-h] [--token TOKEN] [--json] [--exit-code EXIT_CODE]
               workflows_yaml

ESHGHAM: The Executive Summarizer of Health for GitHub Actions Monitoring. A
dashboard for your neglected GitHub Actions workflows. Version 0.1.0.dev0.

positional arguments:
  workflows_yaml        Workflows in YAML format. This is provided with
                        repository 'owner/repo_name' as a string key, and a
                        list of workflow filenames as the value. The special
                        key 'token' may be used for the GitHub personal access
                        token.

options:
  -h, --help            show this help message and exit
  --token TOKEN         GitHub personal access token. May also be provided
                        using 'token' as a key in the workflow YAML file, or
                        in the environment variable `GITHUB_TOKEN`. The
                        command argument takes precedence, followed bythe
                        environment variable, and finally the YAML
                        specification.
  --json                Output as JSON instead of outputting to screen. The
                        JSON object has keys 'OK', 'INACTIVATED', and
                        'FAILED', with a list of workflows as values. Each
                        workflow has the repository name, the workflow name,
                        and a URL. For passing/failing workflows, this URL
                        points to the last run. For inactive workflows, the
                        URL points to the workflow itself.
  --exit-code EXIT_CODE
                        Exit code to return if there are any inactive/failing
                        workflows. Runs with no inactive/failing workflows
                        always exit with 0.

```

## YAML config

The YAML config is a mapping of repository names to lists of workflow YAML file
names. It also allows (optionally) the key `token`, which would have the value
of your GitHub personal access token.

Here's my config file, for illustration (obviously, my GitHub token is removed).

```yaml
openpathsampling/openpathsampling:
  - tests.yml
  - check-openmm-rc.yml
openpathsampling/openpathsampling-cli:
  - test-suite.yml
openpathsampling/ops_tutorial:
  - ci.yml
openpathsampling/ops_additional_examples:
  - tests.yml
dwhswenson/contact_map:
  - unit-tests.yml
dwhswenson/autorelease:
  - unit-tests.yml
dwhswenson/ops-storage-notebooks:
  - tests.yml
dwhswenson/conda-rc-check:
  - example_use.yml
dwhswenson/plugcli:
  - ci.yml
# I'm okay with these being inactive, but maybe I'll activate them again
# someday
#dwhswenson/ghcontribs:
  #- tests.yml
#dwhswenson/fabulous-paths:
  #- tests.yml
token: ghp_<blahblahblah>
```
