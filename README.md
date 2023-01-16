# ghadash

*A dashboard to check on the status of your neglected GitHub Actions
Workflows.*

Do you have a lot of GitHub repositories? Things you where you like to keep the
projects alive, even if they aren't very active?

Do you worry that you'll miss one of the warning emails GitHub sends you when a
scheduled workflow becomes inactive? Have you missed them before, only
discovering that CI hadn't been running for months after a user complained
about incompatibility with a new release of a dependency?

**Then ghadash is for you!**

ghadash is a little command line utility to check on your scheduled workflows.

Here's what it looks like in practice:

...

## Installation

```
python -m pip install ghadash
```

## Usage


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
