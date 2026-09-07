from __future__ import annotations


def to_markdown(report: dict) -> str:
    icon = {"pass": "✅", "fail": "❌", "unknown": "⚠️"}
    lines = [
        "# Proof Report",
        "",
        f"**Verdict:** {icon.get(report['verdict'], '•')} {report['verdict'].upper()}",
        f"**Score:** {report['score']}/100",
        f"**Task:** {report.get('task','')}",
        "",
        "## Acceptance criteria",
        "",
    ]
    for c in report["criteria"]:
        lines.append(f"### {icon.get(c['status'], '•')} {c['id']} — {c['status'].upper()}")
        lines.append(c["text"])
        lines.append("")
        for chk in c["checks"]:
            lines.append(f"- **{chk['type']}** → `{chk['status']}` — {chk['summary']}")
        lines.append("")
    lines += [
        "## Verification policy",
        "",
        f"- Command execution: {report['policy']['command_execution']}",
        "- Unknown evidence is never upgraded to PASS.",
        "",
    ]
    return "\n".join(lines)
