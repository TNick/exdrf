#!/usr/bin/env bash

# Re-exec under bash when a runner invokes this script as ``sh`` (shebang is
# ignored); POSIX ``sh`` does not support ``set -o pipefail``.
if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

# ---------------------------------------------------------------------------
# registry-release.sh — Build and publish one exdrf monorepo package.
#
# CI must push a tag ``vX.Y.Z-<pkg_dir>`` (for example ``v0.1.14-exdrf`` or
# ``v0.1.14-exdrf-gen-openapi2rtk``). The numeric version must match
# ``[project].version`` in that package's ``pyproject.toml``.
#
# We do not run ``make init-d``: ``python -m build`` uses a PEP 517 isolated
# environment (only ``[build-system] requires``). The release venv only needs
# ``build`` and ``twine``.
# ---------------------------------------------------------------------------

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

# Resolve the Git tag name (Forgejo sets GITHUB_REF_NAME on tag builds).
release_tag="${GITHUB_REF_NAME:-}"
if [[ -z "${release_tag}" ]] && [[ -n "${GITHUB_REF:-}" ]]; then
    release_tag="${GITHUB_REF#refs/tags/}"
fi
if [[ -z "${release_tag}" ]]; then
    release_tag="${RELEASE_VERSION:-}"
fi
if [[ -z "${release_tag}" ]]; then
    release_tag="$(git -C "${repo_root}" describe --tags --always)"
fi

# Hyphen-safe package suffix (directory names like ``exdrf-gen-al2qt``).
if [[ ! "${release_tag}" =~ ^v([0-9]+\.[0-9]+\.[0-9]+)-(.+)$ ]]; then
    printf 'Registry release expects tag vX.Y.Z-pkg_dir (got %s).\n' \
        "${release_tag}" >&2
    exit 1
fi

pep_ver="${BASH_REMATCH[1]}"
pkg_dir="${BASH_REMATCH[2]}"

if [[ "${pkg_dir}" == *"/"* ]] || [[ "${pkg_dir}" == *\\* ]] \
    || [[ "${pkg_dir}" == *..* ]]; then
    printf 'Invalid package directory segment in tag: %q\n' "${pkg_dir}" >&2
    exit 1
fi

cd "${repo_root}"
python3 scripts/assert_release_version.py --root "${repo_root}" \
    --tag "${release_tag}"

printf 'Releasing %s at version %s (tag %s)\n' \
    "${pkg_dir}" "${pep_ver}" "${release_tag}"

venv_dir="${repo_root}/.venv-release"
python3 -m venv "${venv_dir}"
# shellcheck source=/dev/null
source "${venv_dir}/bin/activate"
python -m pip install --upgrade pip
python -m pip install --upgrade build twine

python scripts/build_packages.py --include "${pkg_dir}"
python scripts/collect_dist.py --include "${pkg_dir}"

export TWINE_USERNAME="${TWINE_USERNAME:-${GITHUB_ACTOR:-git}}"
: "${TWINE_PASSWORD:?Set TWINE_PASSWORD (e.g. Forgejo package token).}"
: "${TWINE_REPOSITORY_URL:?Set TWINE_REPOSITORY_URL for PyPI-compatible upload.}"
export TWINE_PASSWORD
export TWINE_REPOSITORY_URL

python -m twine check release_dist/*
python -m twine upload --non-interactive release_dist/*

printf 'Registry release complete for %s (Python package %s published).\n' \
    "${release_tag}" "${pkg_dir}"
