#!/bin/bash

# The script is used for
# creation a commit on validation/release branch
# without history of the repository.
#
# It does that in 2 steps:
# 1. Create squashed tar.gz in build/
#   This is acheved by creating tmp folder
#   where src repo is copied with excludes provided in
#   ./package/exclude.txt & ./package/exclude-opendek.txt
#   then all from that temp path is zipped to
#   build/ folder of source repository.
# 2. Push unzipped package to validation/release branch
#   When PUSH_TO_GITHUB is set new temp repo is
#   initialised with remote set to source DEC.
#   In that new repo validation/release branch is created
#   with a content of package created is step number 1.

set -euxo pipefail

PUSH_TO_GITHUB=${PUSH_TO_GITHUB:-false}
GITHUB_BRANCH=${GITHUB_BRANCH:-"package"}
PACKAGE_PREFIX=${PACKAGE_PREFIX:-"opendek"}
GIT_USER=${GIT_USER:-smart-edge-open}
GIT_EMAIL=${GIT_EMAIL:-smart-edge-open@intel.com}
EK_REPOSITORY=${EK_REPOSITORY:-"https://github.com/intel-innersource/applications.services.smart-edge-open.developer-experience-kits-open.git"}

# GITHUB_BRANCH should be one of (in Dec 2021):
#  opendek-package
#  opendek-validation-21.12
#  opendek-release-21.12
GITHUB_BRANCH=$PACKAGE_PREFIX-$GITHUB_BRANCH

# it should be something like smart-edge-open-21.12-cf
# be carefull if you get smart-edge-open-21.12-cf-dirty
VERSION=$(git describe --tags --always --dirty)
# VERSION is used in callbacks
export VERSION

cd "$(dirname "$0")"/.. || exit
EK_SRC_REPO_PATH=$(pwd)

# create temp dir to copy EK with excludes
TEMP_PATH="$(mktemp -d)"
CEEK_PATH="$TEMP_PATH"/"${PACKAGE_PREFIX}"-"$VERSION"
# CEEK_PATH is used in callbacks, need to export
export CEEK_PATH
mkdir -p "${CEEK_PATH}"

# copy all from src EK repo to temp CEEK folder
# with some excludes
cat ./package/exclude*.txt > ./package/Exclude-all.txt
rsync -av . "$CEEK_PATH" --exclude-from="./package/Exclude-all.txt"

# exec callbacks in temp
cd "$TEMP_PATH"
for script in "$EK_SRC_REPO_PATH"/package/callbacks/*; do
  "$script"
done

# zip all from temp to src EK repo build/ folder
mkdir -p "$EK_SRC_REPO_PATH"/build/
tar -czf "$EK_SRC_REPO_PATH"/build/"${PACKAGE_PREFIX}"-"${VERSION}".tar.gz -- *

# remove temp as we already have tar.gz package in EK build/
cd "$EK_SRC_REPO_PATH"
rm -rf "$CEEK_PATH"

if $PUSH_TO_GITHUB; then
  echo "pushing validation/release branch"
  TEMP_VALIDATION_RELEASE_EK_REPO_PATH="$(mktemp -d)"
  cd "$TEMP_VALIDATION_RELEASE_EK_REPO_PATH"

  # create new EK repository without history
  git init
  git config user.name "$GIT_USER"
  git config user.email "$GIT_EMAIL"
  git remote add origin "$EK_REPOSITORY"
  
  # create validation/release branch not related to any other branch from source
  git checkout -b "$GITHUB_BRANCH"
  if git pull origin "$GITHUB_BRANCH" > /dev/null;
  then
    echo "remote branch already exists, remove all from it"
    git rm -rf .
  fi
  
  # unzip already prepared tar.gz package from EK repo
  tar -xzf "$EK_SRC_REPO_PATH"/build/"${PACKAGE_PREFIX}"-"${VERSION}".tar.gz --strip-components=1
  rm -rf "$EK_SRC_REPO_PATH"/build/"${PACKAGE_PREFIX}"-"${VERSION}".tar.gz

  # commit the changes
  git add --all
  git commit -m "$VERSION"
  git push origin "$GITHUB_BRANCH"

  # remove temp
  cd "$EK_SRC_REPO_PATH"
  rm -rf "$TEMP_VALIDATION_RELEASE_EK_REPO_PATH"
  echo "$TEMP_VALIDATION_RELEASE_EK_REPO_PATH"
fi
