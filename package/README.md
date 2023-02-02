# SmartEdge Repository packaging script

This script creates source code package and optionally pushes to github.

Following script will:
```bash
PUSH_TO_GITHUB=true \ # Push the package contents to the EK_REPOSITORY defined below.
EK_REPOSITORY="git@github.com:intel-innersource/applications.services.smart-edge-open.developer-experience-kits-open.git" \
GIT_USER=smart-edge-open \ # Git user to sign the package commit
GIT_EMAIL=smart-edge-open@intel.com \ # Git email to sign the package commit
GITHUB_BRANCH=validation-<se-open-version> \ # Git branch to which the package will be pushed
PACKAGE_PREFIX=opendek \ # Package prefix (DEK, PWEK, ...)
./package/prepare_package.sh
```

## Excludes from package

**Experience Kit owner** must ensure that `exclude-$PACKAGE_PREGIX.txt` contains all necessary excludes for the package.

Following exclude files are available:
- `exclude.txt` provides generic excludes that are required for all packages
- `exclude-$PACKAGE_PREFIX.txt` provides package-oriented excludes (e.g. exclude unnecesary roles from PWEK package)

## Github Actions package build automation

Following github actions workflows are used to prepare the validation/release package:
```bash
.github/workflows
├── release.yml
└── validation.yml
```

Package creation is triggered by tagging a commit. In OpenDEK, following tags trigger the package build:
* Validation package: `smart-edge-open-*-rc[1-9]`
* Release package: `smart-edge-open-* && !smart-edge-open-*-rc[1-9]`

To tag the current tip of the branch, use following commands:
```
git tag smart-edge-open-rcX
git push --tags
```
