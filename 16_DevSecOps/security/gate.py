"""Security gate: read every scanner's JSON report and decide whether the image may ship.

Policy (see security/README in the topic README):
  SAST    Bandit      block on any HIGH severity finding
  SCA     pip-audit   block on any known vulnerability in a pinned dependency
  Secrets gitleaks    block on any finding
  Image   Trivy       block on any CRITICAL, or any HIGH that already has a fixed version

usage: python gate.py <reports-dir>
Exit code 1 blocks the pipeline. A markdown summary is written to $GITHUB_STEP_SUMMARY when set.
"""
import json
import os
import sys
from pathlib import Path


def load(path):
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else []


def check_bandit(report):
    findings = report.get("results", [])
    high = [f for f in findings if f["issue_severity"] == "HIGH"]
    detail = ", ".join(f'{f["test_id"]} {Path(f["filename"]).name}:{f["line_number"]}' for f in high)
    return len(high), f"{len(findings)} findings, {len(high)} HIGH" + (f" ({detail})" if detail else "")


def check_pip_audit(report):
    vulns = [(d["name"], d["version"], v["id"]) for d in report.get("dependencies", []) for v in d.get("vulns", [])]
    packages = sorted({f"{n}=={v}" for n, v, _ in vulns})
    return len(vulns), f"{len(vulns)} known vulnerabilities" + (f" in {', '.join(packages)}" if packages else "")


def check_gitleaks(report):
    rules = sorted({f["RuleID"] for f in report})
    return len(report), f"{len(report)} leaked secrets" + (f" ({', '.join(rules)})" if rules else "")


def check_trivy(report):
    vulns = [v for r in report.get("Results", []) for v in (r.get("Vulnerabilities") or [])]
    critical = [v for v in vulns if v["Severity"] == "CRITICAL"]
    high_fixable = [v for v in vulns if v["Severity"] == "HIGH" and v.get("FixedVersion")]
    high_total = sum(v["Severity"] == "HIGH" for v in vulns)
    blocking = len(critical) + len(high_fixable)
    return blocking, f"{len(critical)} CRITICAL, {high_total} HIGH ({len(high_fixable)} with a fix available)"


CHECKS = [
    ("SAST", "Bandit", "bandit.json", check_bandit),
    ("SCA", "pip-audit", "pip-audit.json", check_pip_audit),
    ("Secrets", "gitleaks", "gitleaks.json", check_gitleaks),
    ("Image", "Trivy", "trivy.json", check_trivy),
]


def main(reports_dir):
    rows, blocked = [], False
    for stage, tool, filename, check in CHECKS:
        report = load(Path(reports_dir) / filename)
        if report is None:
            rows.append((stage, tool, "BLOCK", "report missing - the scan did not run"))
            blocked = True
            continue
        count, detail = check(report)
        verdict = "BLOCK" if count else "PASS"
        blocked |= bool(count)
        rows.append((stage, tool, verdict, detail))

    width = max(len(r[3]) for r in rows)
    print(f"{'Stage':<8} {'Tool':<10} {'Result':<7} Detail")
    print(f"{'-' * 8} {'-' * 10} {'-' * 7} {'-' * width}")
    for stage, tool, verdict, detail in rows:
        print(f"{stage:<8} {tool:<10} {verdict:<7} {detail}")
    print()
    print("SECURITY GATE: " + ("FAILED - image will NOT be pushed or deployed" if blocked else "PASSED"))

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Security gate: " + ("FAILED :x:" if blocked else "PASSED :white_check_mark:") + "\n\n")
            f.write("| Stage | Tool | Result | Detail |\n|---|---|---|---|\n")
            for stage, tool, verdict, detail in rows:
                f.write(f"| {stage} | {tool} | {verdict} | {detail} |\n")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "reports"))
