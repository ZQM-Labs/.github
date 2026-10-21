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
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

# ── Config ──────────────────────────────────────────────────────────────
ECOSYSTEMS = {
    "python": ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile.lock"],
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
    """Parse requirement lines without treating a version range as an installed version."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$", line)
        if not m:
            continue
        name, spec = m.group(1), m.group(2).split(";", 1)[0].strip()
        exact = re.fullmatch(r"(?:===|==)\s*[vV]?([0-9][A-Za-z0-9.+!-]*)", spec)
        deps.append({"name": name, "version": exact.group(1) if exact else "unknown", "ecosystem": "PyPI"})
    return deps

def parse_pyproject_toml(content: str) -> list[dict]:
    """Best-effort parser for simple dependency tables; ranges are not installed versions."""
    deps = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_deps = "dependencies" in stripped or "project.dependencies" in stripped
            continue
        if in_deps and "=" in stripped and not stripped.startswith("#"):
            m = re.match(r'^["\']?([A-Za-z0-9_.-]+)["\']?\s*=\s*["\']([^"\']+)["\']', stripped)
            if m:
                name, spec = m.group(1), m.group(2).strip()
                exact = re.fullmatch(r"(?:===|==)\s*[vV]?([0-9][A-Za-z0-9.+!-]*)", spec)
                deps.append({"name": name, "version": exact.group(1) if exact else "unknown", "ecosystem": "PyPI"})
    return deps

def parse_package_json(content: str) -> list[dict]:
    """Parse direct npm dependencies; semver ranges are not treated as installed versions."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps = []
    for section in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        for name, spec in data.get(section, {}).items():
            spec = str(spec).strip()
            exact = re.fullmatch(r"[vV]?(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)", spec)
            deps.append({"name": name, "version": exact.group(1) if exact else "unknown", "ecosystem": "npm"})
    return deps


def parse_package_lock(content: str) -> list[dict]:
    """Read resolved versions from npm lockfiles (v2/v3 and legacy v1)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps = []
    packages = data.get("packages")
    if isinstance(packages, dict):
        for path, meta in packages.items():
            if not path or "node_modules/" not in path or not isinstance(meta, dict):
                continue
            version = meta.get("version")
            if not version:
                continue
            name = meta.get("name") or path.rsplit("node_modules/", 1)[-1]
            deps.append({"name": name, "version": str(version).lstrip("v"), "ecosystem": "npm"})
        return deps

    def walk(entries):
        for name, meta in entries.items():
            if not isinstance(meta, dict):
                continue
            version = meta.get("version")
            if version:
                deps.append({"name": name, "version": str(version).lstrip("v"), "ecosystem": "npm"})
            nested = meta.get("dependencies")
            if isinstance(nested, dict):
                walk(nested)

    legacy = data.get("dependencies")
    if isinstance(legacy, dict):
        walk(legacy)
    return deps

def parse_go_mod(content: str) -> list[dict]:
    deps = []
    in_require = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require") and "(" not in stripped:
            in_require = True
            parts = stripped.split()
            if len(parts) >= 3:
                deps.append({"name": parts[1], "version": parts[2].strip("v"), "ecosystem": "Go"})
            continue
        if stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if len(parts) >= 2:
                deps.append({"name": parts[0], "version": parts[1].strip("v"), "ecosystem": "Go"})
    return deps


def discover_deps(repo_root: str) -> list[dict]:
    deps = []
    for eco, filenames in ECOSYSTEMS.items():
        for fname in filenames:
            path = os.path.join(repo_root, fname)
            if not os.path.isfile(path):
                continue
            content = read_file(path)
            if not content:
                continue
            if eco == "python" and fname in ("requirements.txt", "requirements-dev.txt"):
                deps.extend(parse_python_requirements(content))
            elif eco == "python" and fname == "pyproject.toml":
                deps.extend(parse_pyproject_toml(content))
            elif eco == "javascript" and fname == "package.json":
                if not os.path.isfile(os.path.join(repo_root, "package-lock.json")):
                    deps.extend(parse_package_json(content))
            elif eco == "javascript" and fname == "package-lock.json":
                deps.extend(parse_package_lock(content))
            elif eco == "go" and fname == "go.mod":
                deps.extend(parse_go_mod(content))
    return deps


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


def shell_cmd(cmd: list[str], cwd: str) -> list | None:
    """Run an optional scanner and preserve valid JSON even when findings cause exit code 1."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
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
    # "dependencies" array; older tools may emit a top-level list.
    if isinstance(data, dict) and isinstance(data.get("dependencies"), list):
        data = data["dependencies"]
    elif not isinstance(data, list):
        print(
            f"::warning::Scanner `{cmd[0]}` returned JSON of unexpected type "
            f"{type(data).__name__}; expected a list or an object with a dependencies list.",
            file=sys.stderr,
        )
        return None

    if r.returncode != 0:
        print(
            f"::notice::Scanner `{cmd[0]}` exited {r.returncode}; preserving its valid JSON findings.",
            file=sys.stderr,
        )
    return data
def scan_pip_audit(repo_root: str) -> list[dict]:
    """Audit declared Python requirements, not the unrelated runner environment."""
    findings = []
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
                f"::warning::Could not extract project dependencies from pyproject.toml for pip-audit: {exc}",
                file=sys.stderr,
            )

    if not manifests:
        print(
            "::notice::No requirements.txt, requirements-dev.txt, or PEP 621 dependencies found; "
            "pip-audit manifest scanning is not applicable.",
            file=sys.stderr,
        )
        return findings

    try:
        for manifest in manifests:
            data = shell_cmd(
                ["pip-audit", "--format=json", "--strict", "-r", manifest],
                repo_root,
            )
            if data is None:
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
    return findings
def scan_safety(repo_root: str) -> list[dict]:
    findings = []
    data = shell_cmd(["safety", "check", "--json"], repo_root)
    if not data:
        return findings
    for item in data:
        findings.append({
            "type": "vulnerability",
            "package": item.get("package_name", ""),
            "id": item.get("vulnerability_id"),
            "installed": item.get("analyzed_version", ""),
            "severity": item.get("severity", "medium"),
            "message": f"{item.get('vulnerability_id', 'UNKNOWN')}: {item.get('advisory', '')[:180]}",
        })
    return findings


# ── Main scan ───────────────────────────────────────────────────────────

def scan_repo(repo_root: str, repo_full: str) -> tuple[list[dict], dict]:
    # Each invocation reports only errors from its own scan.
    API_ERRORS.clear()
    deps = discover_deps(repo_root)
    findings = []
    licenses_checked = {}

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

        if license_name:
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
