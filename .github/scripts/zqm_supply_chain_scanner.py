#!/usr/bin/env python3
"""
ZQM Supply Chain Scanner
- Scans Python/JS/Go dependencies for vulnerabilities (OSV + pip-audit + safety)
- Checks license compliance
- Detects outdated packages
- Outputs GitHub Security Advisory comments + SARIF
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

# ── Config ──────────────────────────────────────────────────────────────
ECOSYSTEMS = {
    "python": ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile.lock", "poetry.lock"],
    "javascript": ["package.json", "package-lock.json", "yarn.lock"],
    "go": ["go.mod", "go.sum"],
}
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", "Python-2.0", "Apache Software License", "0BSD", "MIT License", "Python Software Foundation License", "BSD License"}
OSV_API = "https://api.osv.dev/v1/query"
GITHUB_API = "https://api.github.com"
MAX_RETRIES = 3
# API lookup failures must be visible in scan results; never report an incomplete scan as clean.
API_ERRORS: list[dict[str, str]] = []
# ────────────────────────────────────────────────────────────────────────


def gh_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api_post(url: str, payload: dict, headers: dict | None = None) -> dict:
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=hdrs)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            if not isinstance(data, dict):
                error = {"error": f"expected JSON object, received {type(data).__name__}"}
                API_ERRORS.append({"url": url, "error": str(error)})
                return error
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", 5))
                time.sleep(wait)
                continue
            error = {"error": e.code, "body": e.read().decode()[:400]}
            API_ERRORS.append({"url": url, "error": str(error)})
            return error
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            error = {"error": str(exc)[:200]}
            API_ERRORS.append({"url": url, "error": str(error)})
            return error
    error = {"error": "max retries exceeded"}
    API_ERRORS.append({"url": url, "error": str(error)})
    return error


def api_get(url: str, headers: dict | None = None) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            if not isinstance(data, dict):
                error = {"error": f"expected JSON object, received {type(data).__name__}"}
                API_ERRORS.append({"url": url, "error": str(error)})
                return error
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", 5)))
                continue
            error = {"error": e.code, "body": e.read().decode()[:400]}
            API_ERRORS.append({"url": url, "error": str(error)})
            return error
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            error = {"error": str(exc)[:200]}
            API_ERRORS.append({"url": url, "error": str(error)})
            return error
    error = {"error": "max retries exceeded"}
    API_ERRORS.append({"url": url, "error": str(error)})
    return error


# ── Dependency discovery ────────────────────────────────────────────────

def read_file(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def parse_python_requirements(content: str) -> list[dict]:
    """Parse simple requirement pins and reject lines we cannot inventory safely."""
    deps = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Includes and pip options can change the effective dependency set. They
        # are surfaced as incomplete coverage instead of silently being skipped.
        if line.startswith("-"):
            raise ValueError(
                f"unsupported pip option or nested requirement on line {line_number}: {line[:120]}"
            )
        # VCS/URL requirements and direct references need dedicated resolution;
        # do not accidentally interpret the URL scheme as a package name.
        if re.match(r"^(?:git\+|svn\+|hg\+|https?://|file://)", line, re.IGNORECASE):
            raise ValueError(f"unsupported VCS/URL requirement on line {line_number}: {line[:120]}")
        m = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$", line)
        if not m:
            raise ValueError(f"unsupported requirement syntax on line {line_number}: {line[:120]}")
        name, spec = m.group(1), m.group(2).split(";", 1)[0].strip()
        if spec.startswith("@") or re.search(r"(?:git\+|svn\+|hg\+|https?://|file://)", spec, re.IGNORECASE):
            raise ValueError(f"unsupported direct-reference requirement on line {line_number}: {line[:120]}")
        exact = re.fullmatch(r"(?:===|==)\s*[vV]?([0-9][A-Za-z0-9.+!-]*)", spec)
        deps.append({"name": name, "version": exact.group(1) if exact else "unknown", "ecosystem": "PyPI"})
    return deps

def parse_pyproject_toml(content: str) -> list[dict]:
    """Parse PEP 621 and Poetry dependency declarations without inventing resolved versions.

    Malformed or unsupported manifest structures raise ValueError so a broken
    manifest cannot silently produce an empty dependency inventory.
    """
    import tomllib

    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid pyproject.toml: {exc}") from exc

    requirements = []
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml [project] must be a table")

    declared = project.get("dependencies", [])
    if declared is not None:
        if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
            raise ValueError("pyproject.toml [project].dependencies must be an array of strings")
        requirements.extend(declared)

    optional = project.get("optional-dependencies", {})
    if optional is not None:
        if not isinstance(optional, dict):
            raise ValueError("pyproject.toml [project.optional-dependencies] must be a table")
        for group, entries in optional.items():
            if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
                raise ValueError(
                    f"pyproject.toml optional dependency group {group!r} must be an array of strings"
                )
            requirements.extend(entries)

    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        raise ValueError("pyproject.toml [tool] must be a table")
    poetry = tool.get("poetry", {})
    if not isinstance(poetry, dict):
        raise ValueError("pyproject.toml [tool.poetry] must be a table")

    poetry_tables = []
    for key in ("dependencies", "dev-dependencies"):
        table = poetry.get(key, {})
        if table is not None:
            if not isinstance(table, dict):
                raise ValueError(f"pyproject.toml [tool.poetry].{key} must be a table")
            poetry_tables.append((key, table))

    groups = poetry.get("group", {})
    if groups is not None:
        if not isinstance(groups, dict):
            raise ValueError("pyproject.toml [tool.poetry.group] must be a table")
        for group_name, group_data in groups.items():
            if not isinstance(group_data, dict):
                raise ValueError(f"pyproject.toml Poetry group {group_name!r} must be a table")
            group_deps = group_data.get("dependencies", {})
            if group_deps is not None:
                if not isinstance(group_deps, dict):
                    raise ValueError(
                        f"pyproject.toml Poetry group {group_name!r} dependencies must be a table"
                    )
                poetry_tables.append((f"group.{group_name}.dependencies", group_deps))

    for section, table in poetry_tables:
        for name, spec in table.items():
            if section == "dependencies" and name.lower() == "python":
                continue  # Python interpreter constraint, not a PyPI package.
            if isinstance(spec, str):
                requirements.append(f"{name} {spec}")
            elif isinstance(spec, dict):
                version_spec = spec.get("version", "")
                if version_spec is not None and not isinstance(version_spec, str):
                    raise ValueError(f"Poetry dependency {name!r} version must be a string")
                requirements.append(f"{name} {version_spec or ''}")
            else:
                raise ValueError(f"Poetry dependency {name!r} must be a string or table")

    deps = []
    seen = set()
    for requirement in requirements:
        # PEP 508 entries start with a distribution name; extras and markers are
        # intentionally not interpreted as installed-version evidence.
        match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        if not match:
            raise ValueError(f"unsupported dependency declaration: {requirement!r}")
        name = match.group(1)
        # Manifest constraints are not the installed/resolved version.
        version = "unknown"
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        deps.append({"name": name, "version": version, "ecosystem": "PyPI"})
    return deps


def parse_poetry_lock(content: str) -> list[dict]:
    """Parse resolved package versions from Poetry's TOML lockfile."""
    import tomllib

    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid poetry.lock: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("poetry.lock root must be a table")
    if "package" not in data:
        raise ValueError("poetry.lock is missing its package array")
    packages = data["package"]
    if not isinstance(packages, list):
        raise ValueError("poetry.lock package entries must be an array of tables")

    deps = []
    seen = set()
    for item in packages:
        if not isinstance(item, dict):
            raise ValueError("poetry.lock package entry must be a table")
        name, version = item.get("name"), item.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or not version:
            raise ValueError("poetry.lock package entries require string name and version")
        key = (name.lower().replace("_", "-"), version)
        if key in seen:
            continue
        seen.add(key)
        deps.append({"name": name, "version": version.lstrip("v"), "ecosystem": "PyPI"})
    return deps

def parse_pipfile_lock(content: str) -> list[dict]:
    """Parse Pipenv's resolved default/develop packages from Pipfile.lock."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Pipfile.lock: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Pipfile.lock root must be a JSON object")

    if not any(section in data for section in ("default", "develop")):
        raise ValueError("Pipfile.lock must contain a default or develop section")

    deps = []
    seen = set()
    for section in ("default", "develop"):
        packages = data.get(section, {})
        if not isinstance(packages, dict):
            raise ValueError(f"Pipfile.lock {section} must be an object")
        for name, metadata in packages.items():
            if not isinstance(metadata, dict):
                raise ValueError(f"Pipfile.lock package {name!r} must be an object")
            declared = metadata.get("version", "")
            exact = re.fullmatch(r"==\s*[vV]?([0-9][A-Za-z0-9.+!-]*)", str(declared).strip())
            version = exact.group(1) if exact else "unknown"
            key = name.lower().replace("_", "-")
            if key in seen:
                continue
            seen.add(key)
            deps.append({"name": name, "version": version, "ecosystem": "PyPI"})
    return deps

def parse_package_json(content: str) -> list[dict]:
    """Parse direct npm dependencies; reject malformed manifests instead of hiding them."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid package.json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("package.json root must be a JSON object")

    deps = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        entries = data.get(section, {})
        if entries is None:
            continue
        if not isinstance(entries, dict):
            raise ValueError(f"package.json {section} must be an object")
        for name, spec in entries.items():
            if not isinstance(name, str) or not isinstance(spec, str):
                raise ValueError(f"package.json {section} entries must map package names to strings")
            spec = spec.strip()
            exact = re.fullmatch(r"[vV]?(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)", spec)
            deps.append({"name": name, "version": exact.group(1) if exact else "unknown", "ecosystem": "npm"})
    return deps

def parse_package_lock(content: str) -> list[dict]:
    """Read resolved versions from npm lockfiles (v2/v3 and legacy v1)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid package-lock.json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("package-lock.json root must be a JSON object")

    if "packages" not in data and "dependencies" not in data:
        raise ValueError("package-lock.json must contain packages or dependencies")

    deps = []
    packages = data.get("packages")
    if packages is not None:
        if not isinstance(packages, dict):
            raise ValueError("package-lock.json packages must be an object")
        for path, meta in packages.items():
            if not path or "node_modules/" not in path:
                continue
            if not isinstance(meta, dict):
                raise ValueError(f"package-lock.json entry {path!r} must be an object")
            version = meta.get("version")
            if not version:
                continue
            name = meta.get("name") or path.rsplit("node_modules/", 1)[-1]
            deps.append({"name": name, "version": str(version).lstrip("v"), "ecosystem": "npm"})
        return deps

    def walk(entries):
        if not isinstance(entries, dict):
            raise ValueError("package-lock.json dependencies must be an object")
        for name, meta in entries.items():
            if not isinstance(meta, dict):
                raise ValueError(f"package-lock.json dependency {name!r} must be an object")
            version = meta.get("version")
            if version:
                deps.append({"name": name, "version": str(version).lstrip("v"), "ecosystem": "npm"})
            nested = meta.get("dependencies")
            if nested is not None:
                walk(nested)

    legacy = data.get("dependencies")
    if legacy is not None:
        walk(legacy)
    return deps

def parse_go_mod(content: str) -> list[dict]:
    """Parse Go require directives without treating unrelated directives as modules."""
    deps = []
    in_require = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        # Go comments are not part of the module/version tokens.
        stripped = stripped.split("//", 1)[0].strip()
        if not stripped:
            continue

        if in_require:
            if stripped == ")":
                in_require = False
                continue
            parts = stripped.split()
            if len(parts) < 2:
                raise ValueError(f"invalid go.mod require entry on line {line_number}")
            deps.append({"name": parts[0], "version": parts[1].lstrip("v"), "ecosystem": "Go"})
            continue

        if stripped == "require (":
            in_require = True
            continue
        if stripped.startswith("require "):
            parts = stripped[len("require "):].split()
            if len(parts) < 2:
                raise ValueError(f"invalid go.mod require directive on line {line_number}")
            deps.append({"name": parts[0], "version": parts[1].lstrip("v"), "ecosystem": "Go"})

    if in_require:
        raise ValueError("unterminated go.mod require block")
    if not any(line.strip().startswith("module ") for line in content.splitlines()):
        raise ValueError("go.mod is missing its module directive")
    return deps

def discover_deps(repo_root: str, errors: list[dict] | None = None) -> list[dict]:
    """Discover dependencies while converting manifest failures into reportable findings."""
    deps = []
    errors = errors if errors is not None else []
    for eco, filenames in ECOSYSTEMS.items():
        for fname in filenames:
            path = os.path.join(repo_root, fname)
            if not os.path.isfile(path):
                continue
            content = read_file(path)
            if content is None:
                errors.append({
                    "type": "scan_error",
                    "package": path,
                    "id": "MANIFEST_UNREADABLE",
                    "severity": "high",
                    "message": "Dependency manifest exists but could not be read; scan coverage is incomplete.",
                })
                continue
            try:
                if eco == "python" and fname in ("requirements.txt", "requirements-dev.txt"):
                    deps.extend(parse_python_requirements(content))
                elif eco == "python" and fname == "pyproject.toml":
                    deps.extend(parse_pyproject_toml(content))
                elif eco == "python" and fname == "Pipfile.lock":
                    deps.extend(parse_pipfile_lock(content))
                elif eco == "python" and fname == "poetry.lock":
                    deps.extend(parse_poetry_lock(content))
                elif eco == "javascript" and fname == "package.json":
                    manifest_deps = parse_package_json(content)
                    if not os.path.isfile(os.path.join(repo_root, "package-lock.json")):
                        deps.extend(manifest_deps)
                elif eco == "javascript" and fname == "package-lock.json":
                    deps.extend(parse_package_lock(content))
                elif eco == "go" and fname == "go.mod":
                    deps.extend(parse_go_mod(content))
            except (ValueError, TypeError) as exc:
                errors.append({
                    "type": "scan_error",
                    "package": path,
                    "id": "MANIFEST_INVALID",
                    "severity": "high",
                    "message": f"Dependency manifest could not be parsed; scan coverage is incomplete: {str(exc)[:300]}",
                })

    # Prefer resolved lockfile versions over unresolved declarations for the
    # same ecosystem/package. Preserve distinct resolved versions where a lockfile
    # legitimately contains multiple versions (e.g. nested npm packages).
    resolved_names = {
        (dep["ecosystem"], dep["name"].lower().replace("_", "-"))
        for dep in deps if dep["version"] != "unknown"
    }
    filtered = [
        dep for dep in deps
        if dep["version"] != "unknown"
        or (dep["ecosystem"], dep["name"].lower().replace("_", "-")) not in resolved_names
    ]
    unique = []
    seen = set()
    for dep in filtered:
        key = (dep["ecosystem"], dep["name"].lower().replace("_", "-"), dep["version"])
        if key not in seen:
            seen.add(key)
            unique.append(dep)
    return unique


# ── Vulnerability + license + outdatedness checks ───────────────────────

def query_osv(name: str, version: str, ecosystem: str) -> list[dict]:
    payload = {
        "package": {"name": name, "ecosystem": ecosystem},
        "version": version,
    }
    result = api_post(OSV_API, payload)
    if "error" in result:
        return []
    return result.get("vulns", [])


def check_license_pypi(name: str) -> str | None:
    url = f"https://pypi.org/pypi/{name}/json"
    result = api_get(url)
    if "error" in result:
        return None
    info = result.get("info", {})
    lic = info.get("license", "")
    # classifiers
    for classifier in info.get("classifiers", []):
        if classifier.startswith("License ::"):
            lic = classifier.split("::")[-1].strip()
    return lic or None


def check_license_npm(name: str) -> str | None:
    url = f"https://registry.npmjs.org/{name}"
    result = api_get(url)
    if "error" in result:
        return None
    return result.get("license") or None


def check_license_go(name: str) -> str | None:
    # Best effort: proxy.golang.org module metadata (no stable license endpoint)
    # Fallback: Unknown
    return None


def license_is_allowed(license_name: str) -> bool:
    """Compare normalized license labels against the scanner's explicit allowlist."""
    norm_lic = re.sub(r"[\s\-_]+", "", license_name).upper()
    allowed_norm = {re.sub(r"[\s\-_]+", "", item).upper() for item in ALLOWED_LICENSES}
    return norm_lic in allowed_norm


def check_outdated_pypi(name: str, current: str) -> str | None:
    url = f"https://pypi.org/pypi/{name}/json"
    result = api_get(url)
    if "error" in result:
        return None
    latest = result.get("info", {}).get("version", current)
    return latest if latest != current else None


def check_outdated_npm(name: str, current: str) -> str | None:
    url = f"https://registry.npmjs.org/{name}"
    result = api_get(url)
    if "error" in result:
        return None
    dist_tags = result.get("dist-tags", {})
    latest = dist_tags.get("latest", current)
    return latest if latest != current else None


def check_outdated_go(name: str, current: str) -> str | None:
    # go list -m -json {name}@latest would require network; skip for speed
    return None


# ── SARIF + Advisory formatting ─────────────────────────────────────────

def to_sarif(findings: list[dict], repo: str) -> dict:
    rules = []
    for f in findings:
        rules.append({
            "id": f"{f['package']}-{f['id']}" if f.get("id") else f"{f['package']}-license",
            "shortDescription": {"text": f["type"].upper()},
            "fullDescription": {"text": f["message"]},
            "properties": {
                "package": f["package"],
                "installedVersion": f.get("installed"),
                "severity": f.get("severity", "medium"),
            },
        })
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "zqm-supply-chain-scanner", "version": "0.1.0"}},
                "results": [
                    {
                        "ruleId": r["id"],
                        "level": (
                            "error"
                            if str(r["properties"].get("severity", "")).lower() in {"critical", "high"}
                            else "note"
                            if str(r["properties"].get("severity", "")).lower() in {"low", "info"}
                            else "warning"
                        ),
                        "message": {"text": r["fullDescription"]["text"]},
                        "properties": r["properties"],
                    }
                    for r in rules
                ],
            }
        ],
    }


def to_github_advisory_comment(findings: list[dict]) -> str:
    if not findings:
        return ":white_check_mark: **zqm-supply-chain-scanner** — 0 supply-chain issues detected."
    lines = [f"### :warning: zqm-supply-chain-scanner — {len(findings)} findings\n"]
    for f in findings:
        lines.append(f"- **{f['type'].upper()}** `{f['package']}` @ {f.get('installed', '?')}: {f['message']}")
    lines.append(f"\n_Scanned {datetime.now(timezone.utc).isoformat()}Z_")
    return "\n".join(lines)


def shell_cmd(cmd: list[str], cwd: str, list_key: str = "dependencies", env: dict | None = None) -> list | None:
    """Run an optional scanner and preserve valid JSON even when findings cause exit code 1."""
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, **env} if env else None,
        )
    except FileNotFoundError:
        print(f"::warning::Optional scanner `{cmd[0]}` is not installed; its results are unavailable.", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"::warning::Optional scanner `{cmd[0]}` could not run: {exc}", file=sys.stderr)
        return None

    try:
        data = json.loads(r.stdout)
    except (json.JSONDecodeError, TypeError):
        detail = (r.stderr or r.stdout or "no output").strip().replace("\n", " ")[:300]
        print(
            f"::warning::Scanner `{cmd[0]}` exited {r.returncode} without valid JSON: {detail}",
            file=sys.stderr,
        )
        return None

    # pip-audit's current JSON format is an object containing a
    # "dependencies" array, and safety's is an object containing a
    # "vulnerabilities" array; older tools may emit a top-level list.
    if isinstance(data, dict) and isinstance(data.get(list_key), list):
        data = data[list_key]
    elif not isinstance(data, list):
        print(
            f"::warning::Scanner `{cmd[0]}` returned JSON of unexpected type "
            f"{type(data).__name__}; expected a list or an object with a {list_key} list.",
            file=sys.stderr,
        )
        return None

    if r.returncode != 0:
        print(
            f"::notice::Scanner `{cmd[0]}` exited {r.returncode}; preserving its valid JSON findings.",
            file=sys.stderr,
        )
    return data
def _python_manifests(repo_root: str) -> tuple[list[str], str | None]:
    """Declared Python manifests: requirements files plus a temporary
    manifest synthesized from PEP 621 pyproject dependencies.

    Returns (manifest_paths, temporary_manifest_path_or_None); the
    caller owns deleting the temporary manifest.
    """
    manifests = [
        os.path.join(repo_root, name)
        for name in ("requirements.txt", "requirements-dev.txt")
        if os.path.isfile(os.path.join(repo_root, name))
    ]
    temporary_manifest = None

    pyproject = os.path.join(repo_root, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                project_data = tomllib.load(f)
            project = project_data.get("project", {})
            dependencies = list(project.get("dependencies", []))
            optional = project.get("optional-dependencies", {})
            if isinstance(optional, dict):
                for group in optional.values():
                    if isinstance(group, list):
                        dependencies.extend(group)
            if dependencies:
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    suffix="-zqm-pip-audit-requirements.txt",
                    delete=False,
                ) as f:
                    f.write("\n".join(str(dep) for dep in dependencies) + "\n")
                    temporary_manifest = f.name
                manifests.append(temporary_manifest)
        except Exception as exc:
            print(
                f"::warning::Could not extract project dependencies from pyproject.toml: {exc}",
                file=sys.stderr,
            )

    return manifests, temporary_manifest


def _pip_audit_wheelhouse(manifests: list[str]) -> str | None:
    """Pre-download everything pip-audit's isolated env will install:
    the pip/wheel/setuptools bootstrap trio plus each manifest's full
    dependency closure. Returns the wheelhouse directory, or None
    (cleaning up) when any download fails - the caller then audits
    without it, exactly as before.
    """
    wheelhouse = tempfile.mkdtemp(prefix="zqm-wheelhouse-")
    commands = [
        [sys.executable, "-m", "pip", "download", "--quiet", "--dest", wheelhouse,
         "pip", "wheel", "setuptools"],
    ]
    commands += [
        [sys.executable, "-m", "pip", "download", "--quiet", "--dest", wheelhouse,
         "-r", manifest]
        for manifest in manifests
    ]
    for cmd in commands:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except Exception as exc:
            print(f"::warning::Wheelhouse pre-stage could not run: {exc}", file=sys.stderr)
            shutil.rmtree(wheelhouse, ignore_errors=True)
            return None
        if r.returncode != 0:
            detail = (r.stderr or "").strip().replace("\n", " ")[:200]
            print(
                f"::warning::Wheelhouse pre-stage failed ({detail}); "
                "pip-audit will use the network directly.",
                file=sys.stderr,
            )
            shutil.rmtree(wheelhouse, ignore_errors=True)
            return None
    print(f"::notice::Wheelhouse pre-staged at {wheelhouse}", file=sys.stderr)
    return wheelhouse


def scan_pip_audit(repo_root: str) -> list[dict]:
    """Audit declared Python requirements, not the unrelated runner environment."""
    findings = []
    manifests, temporary_manifest = _python_manifests(repo_root)

    if not manifests:
        print(
            "::notice::No requirements.txt, requirements-dev.txt, or PEP 621 dependencies found; "
            "pip-audit manifest scanning is not applicable.",
            file=sys.stderr,
        )
        return findings

    # pip-audit bootstraps an isolated venv with pip at audit time, and
    # that bootstrap dies whenever the runner's network path hiccups
    # (observed on this fleet as proxy 407s minutes into a job, while
    # the workflow's own installs at job start succeed). Pre-stage a
    # wheelhouse while the scan is young so pip's install phase needs
    # no network at all, and retry the audit on transport failure.
    wheelhouse = _pip_audit_wheelhouse(manifests)
    audit_env = (
        {"PIP_FIND_LINKS": wheelhouse, "PIP_NO_INDEX": "1"} if wheelhouse else None
    )

    try:
        for manifest in manifests:
            data = None
            for attempt in range(3):
                data = shell_cmd(
                    ["pip-audit", "--format=json", "--strict", "-r", manifest],
                    repo_root,
                    env=audit_env,
                )
                if data is not None:
                    break
                if attempt < 2:
                    print(
                        f"::notice::pip-audit attempt {attempt + 1} for {manifest} "
                        "returned no results; retrying.",
                        file=sys.stderr,
                    )
                    time.sleep(10 * (attempt + 1))
            if data is None:
                findings.append({
                    "type": "scan_error",
                    "package": manifest,
                    "id": "PIP_AUDIT_UNAVAILABLE",
                    "severity": "high",
                    "message": (
                        "pip-audit did not return valid results for this manifest; "
                        "vulnerability coverage is incomplete."
                    ),
                })
                continue
            for item in data:
                name = item.get("name", "")
                version = item.get("version", "")
                for vuln in item.get("vulns", []):
                    findings.append({
                        "type": "vulnerability",
                        "package": name,
                        "id": vuln.get("id"),
                        "installed": version,
                        "severity": vuln.get("severity", "medium"),
                        "message": f"{vuln.get('id', 'UNKNOWN')}: {vuln.get('fix_versions', ['no fix'])[0]}",
                    })
    finally:
        if temporary_manifest and os.path.exists(temporary_manifest):
            os.unlink(temporary_manifest)
        if wheelhouse:
            shutil.rmtree(wheelhouse, ignore_errors=True)
    return findings
def scan_safety(repo_root: str) -> list[dict]:
    """Audit declared Python requirements with safety, like pip-audit.

    A bare `safety check` scans the interpreter environment it runs
    in - on a CI runner that is the tooling bootstrap (pip,
    setuptools, wheel), whose advisories say nothing about this repo
    and can never all be cleared (some have no fixed release at all,
    e.g. SFTY-20260721-58460 flags every setuptools including the
    latest). Declared manifests are the coverage that means
    something, so safety gets the same manifests as pip-audit.
    """
    findings = []
    manifests, temporary_manifest = _python_manifests(repo_root)
    if not manifests:
        print(
            "::notice::No requirements.txt, requirements-dev.txt, or PEP 621 dependencies found; "
            "safety manifest scanning is not applicable.",
            file=sys.stderr,
        )
        return findings
    try:
        seen = set()
        for manifest in manifests:
            # safety<3 --json returns an object whose findings live under
            # "vulnerabilities" (verified against safety 2.3.5), not a bare list.
            data = shell_cmd(
                ["safety", "check", "--json", "--file", manifest],
                repo_root,
                list_key="vulnerabilities",
            )
            if data is None:
                findings.append({
                    "type": "scan_error",
                    "package": "safety",
                    "id": "SAFETY_UNAVAILABLE",
                    "severity": "high",
                    "message": "Safety did not return valid scan results; secondary Python vulnerability coverage is incomplete.",
                })
                continue
            for item in data:
                key = (item.get("package_name", ""), item.get("vulnerability_id"))
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "type": "vulnerability",
                    "package": item.get("package_name", ""),
                    "id": item.get("vulnerability_id"),
                    "installed": item.get("analyzed_version", ""),
                    "severity": item.get("severity", "medium"),
                    "message": f"{item.get('vulnerability_id', 'UNKNOWN')}: {item.get('advisory', '')[:180]}",
                })
    finally:
        if temporary_manifest and os.path.exists(temporary_manifest):
            os.unlink(temporary_manifest)
    return findings


# ── Main scan ───────────────────────────────────────────────────────────

def scan_repo(repo_root: str, repo_full: str) -> tuple[list[dict], dict]:
    # Each invocation reports only errors from its own scan.
    API_ERRORS.clear()
    manifest_errors: list[dict] = []
    deps = discover_deps(repo_root, manifest_errors)
    findings = list(manifest_errors)
    licenses_checked = {}

    # Poetry's caret/tilde constraints are not pip requirement specifiers, and
    # without poetry.lock there is no resolved package set to audit. Do not
    # let those declarations silently pass as a complete vulnerability scan.
    pyproject_path = os.path.join(repo_root, "pyproject.toml")
    poetry_lock_path = os.path.join(repo_root, "poetry.lock")
    if os.path.isfile(pyproject_path) and not os.path.isfile(poetry_lock_path):
        import tomllib

        try:
            project_data = tomllib.loads(read_file(pyproject_path) or "")
        except (tomllib.TOMLDecodeError, TypeError):
            project_data = {}
        tool = project_data.get("tool", {})
        poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
        if isinstance(poetry, dict):
            has_poetry_deps = bool(poetry.get("dependencies") or poetry.get("dev-dependencies"))
            groups = poetry.get("group", {})
            if isinstance(groups, dict):
                has_poetry_deps = has_poetry_deps or any(
                    isinstance(group, dict) and bool(group.get("dependencies"))
                    for group in groups.values()
                )
            if has_poetry_deps:
                findings.append({
                    "type": "scan_error",
                    "package": pyproject_path,
                    "id": "POETRY_LOCK_MISSING",
                    "severity": "high",
                    "message": (
                        "Poetry dependencies are declared but poetry.lock is missing; "
                        "resolved versions cannot be audited reliably."
                    ),
                })

    # Do not present partial inventories as complete when a supported ecosystem
    # has a lockfile format that this scanner does not yet resolve.
    package_json = os.path.join(repo_root, "package.json")
    package_lock = os.path.join(repo_root, "package-lock.json")
    yarn_lock = os.path.join(repo_root, "yarn.lock")
    pnpm_lock = os.path.join(repo_root, "pnpm-lock.yaml")
    if os.path.isfile(package_json) and not os.path.isfile(package_lock):
        if os.path.isfile(yarn_lock):
            findings.append({
                "type": "scan_error",
                "package": yarn_lock,
                "id": "YARN_LOCK_UNSUPPORTED",
                "severity": "high",
                "message": "yarn.lock is present but its resolved dependency graph is not parsed; npm transitive coverage is incomplete.",
            })
        elif os.path.isfile(pnpm_lock):
            findings.append({
                "type": "scan_error",
                "package": pnpm_lock,
                "id": "PNPM_LOCK_UNSUPPORTED",
                "severity": "high",
                "message": "pnpm-lock.yaml is present but its resolved dependency graph is not parsed; npm transitive coverage is incomplete.",
            })
        else:
            try:
                package_dependencies = parse_package_json(read_file(package_json) or "")
            except (ValueError, TypeError):
                # The primary discovery pass has already recorded the invalid manifest.
                package_dependencies = []
            if package_dependencies:
                findings.append({
                    "type": "scan_error",
                    "package": package_json,
                    "id": "NPM_LOCK_MISSING",
                    "severity": "high",
                    "message": "Direct npm dependencies are declared without a supported lockfile; resolved versions and transitive dependencies cannot be audited reliably.",
                })

    go_mod = os.path.join(repo_root, "go.mod")
    go_sum = os.path.join(repo_root, "go.sum")
    try:
        go_dependencies = parse_go_mod(read_file(go_mod) or "") if os.path.isfile(go_mod) else []
    except (ValueError, TypeError):
        # The primary discovery pass has already recorded the invalid manifest.
        go_dependencies = []
    if go_dependencies:
        findings.append({
            "type": "scan_error",
            "package": go_sum if os.path.isfile(go_sum) else go_mod,
            "id": "GO_TRANSITIVE_COVERAGE_INCOMPLETE",
            "severity": "high",
            "message": (
                "The scanner inventories direct go.mod requirements only; it does not resolve "
                "the full Go module graph from go.sum. Transitive vulnerability coverage is incomplete."
            ),
        })

    for req_name in ("requirements.txt", "requirements-dev.txt"):
        req_path = os.path.join(repo_root, req_name)
        req_content = read_file(req_path) if os.path.isfile(req_path) else None
        if req_content and any(
            line.strip().startswith(("-r ", "--requirement ", "-c ", "--constraint "))
            for line in req_content.splitlines()
        ):
            findings.append({
                "type": "scan_error",
                "package": req_path,
                "id": "PYTHON_REQUIREMENTS_INCLUDE_UNSUPPORTED",
                "severity": "high",
                "message": "Nested requirements/constraint files are not included in the manual license inventory; Python dependency coverage is incomplete.",
            })

    for dep in deps:
        name = dep["name"]
        version = dep["version"]
        ecosystem = dep["ecosystem"]

        # 1. Vulnerabilities
        # A manifest range is not an installed version; use resolved lockfile pins where available.
        vulns = query_osv(name, version, ecosystem) if version != "unknown" else []
        for vuln in vulns:
            vuln_id = vuln.get("id", "UNKNOWN")
            severity = "high"
            desc = vuln.get("details", "")
            affected = vuln.get("affected", [])
            for a in affected:
                for r in a.get("ranges", []):
                    for ev in r.get("events", []):
                        if ev.get("fixed") and version != "unknown":
                            try:
                                if tuple(map(int, ev["fixed"].split("."))) <= tuple(map(int, version.split(".")[:3])):
                                    severity = "critical"
                            except Exception:
                                pass
            aliases = vuln.get("aliases", [])
            cve = next((a for a in aliases if a.startswith("CVE-")), vuln_id)
            findings.append({
                "type": "vulnerability",
                "package": name,
                "id": vuln_id,
                "installed": version,
                "severity": severity,
                "message": f"{cve}: {desc[:180]}",
            })

        # 2. License compliance
        license_name = None
        if ecosystem == "PyPI":
            license_name = licenses_checked.get(name) or check_license_pypi(name)
        elif ecosystem == "npm":
            license_name = licenses_checked.get(name) or check_license_npm(name)
        elif ecosystem == "Go":
            license_name = licenses_checked.get(name) or check_license_go(name)

        if not license_name:
            findings.append({
                "type": "license",
                "package": name,
                "id": "LICENSE-UNKNOWN",
                "installed": version,
                "severity": "high",
                "message": (
                    "License metadata is unavailable; compliance with the allowed-license "
                    "policy cannot be verified."
                ),
            })
        else:
            licenses_checked[name] = license_name
            if not license_is_allowed(license_name):
                findings.append({
                    "type": "license",
                    "package": name,
                    "id": None,
                    "installed": version,
                    "severity": "medium",
                    "message": f"License `{license_name}` not in allowlist: {sorted(ALLOWED_LICENSES)}",
                })

        # 3. Outdated dependencies
        latest = None
        if version != "unknown":
            if ecosystem == "PyPI":
                latest = check_outdated_pypi(name, version)
            elif ecosystem == "npm":
                latest = check_outdated_npm(name, version)
            elif ecosystem == "Go":
                latest = check_outdated_go(name, version)

        if latest:
            findings.append({
                "type": "outdated",
                "package": name,
                "id": None,
                "installed": version,
                "severity": "low",
                "message": f"Update available: {name}@{latest} (installed {version})",
            })

    # Secondary sources: pip-audit, safety
    extra = scan_pip_audit(repo_root) + scan_safety(repo_root)
    existing = {(f["type"], f["package"], f.get("id")) for f in findings}
    for f in extra:
        key = (f["type"], f["package"], f.get("id"))
        if key not in existing:
            findings.append(f)
            existing.add(key)

    # Build SARIF after all scanners have contributed findings.
    # API outages, throttling, and malformed responses mean coverage is incomplete.
    # Emit explicit findings so CI fails closed instead of silently claiming a clean scan.
    seen_errors = set()
    for error in API_ERRORS:
        key = (error["url"], error["error"])
        if key in seen_errors:
            continue
        seen_errors.add(key)
        findings.append({
            "type": "scan_error",
            "package": error["url"],
            "id": "SCAN-API-ERROR",
            "severity": "high",
            "message": "Security metadata lookup failed; scan coverage is incomplete: " + error["error"][:300],
        })

    sarif = to_sarif(findings, repo_full)
    return findings, sarif


def post_github_advisory(repo_full: str, pr_number: int, comment: str) -> bool:
    token = gh_token()
    if not token or pr_number <= 0:
        return False
    url = f"{GITHUB_API}/repos/{repo_full}/issues/{pr_number}/comments"
    payload = {"body": comment}
    result = api_post(url, payload, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    })
    return "id" in result


def save_artifact(findings: list[dict], sarif: dict, repo_full: str, output: str = "both") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = repo_full.replace("/", "_")
    out_dir = os.path.join(".zqm-security-reports", safe)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{ts}-findings.json")
    sarif_path = os.path.join(out_dir, f"{ts}-results.sarif")
    if output in ("json", "both"):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"repo": repo_full, "scanned_at": ts, "findings": findings}, f, indent=2)
    if output in ("sarif", "both"):
        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2)
    artifacts = [p for p, enabled in ((json_path, output in ("json", "both")), (sarif_path, output in ("sarif", "both"))) if enabled]
    print("Artifacts: " + " | ".join(artifacts))
    return sarif_path if output in ("sarif", "both") else json_path


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ZQM Supply Chain Scanner")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""), help="owner/repo")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--pr", type=int, default=int(os.environ.get("PR_NUMBER", "0")), help="PR number for comment")
    parser.add_argument("--output", default="sarif", choices=["sarif", "json", "both"], help="Output format")
    parser.add_argument("--no-comment", action="store_true", help="Skip GitHub advisory comment")
    args = parser.parse_args()

    repo_full = args.repo or os.path.basename(os.getcwd())
    repo_root = args.root

    print(f"Scanning {repo_full} @ {repo_root} ...")
    findings, sarif = scan_repo(repo_root, repo_full)
    print(f"Findings: {len(findings)}")

    save_artifact(findings, sarif, repo_full, args.output)

    if not args.no_comment and args.pr > 0:
        comment = to_github_advisory_comment(findings)
        if post_github_advisory(repo_full, args.pr, comment):
            print(f"Advisory comment posted on PR #{args.pr}")
        else:
            print("Advisory comment skipped (no token or invalid PR)")

    # Print summary
    vulns = sum(1 for f in findings if f["type"] == "vulnerability")
    licenses = sum(1 for f in findings if f["type"] == "license")
    outdated = sum(1 for f in findings if f["type"] == "outdated")
    print(f"  vulnerabilities={vulns} license_issues={licenses} outdated={outdated}")

    if findings:
        sys.exit(1)


if __name__ == "__main__":
    main()
