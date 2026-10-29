#!/usr/bin/env python3
"""Structure-only Mermaid architecture preflight for Prism / Foundry.

This validates a preliminary architecture sketch, not design correctness or
Mermaid rendering. Approval remains the existing Foundry stage review/confirm.
"""
import argparse
import json
import re
from pathlib import Path

ARCHITECTURE_PATH = "docs/02-architecture-sketch.md"
MAX_BYTES = 128 * 1024
BLOCK = re.compile(r"(?im)^\`\`\`mermaid[ \t]*\n(.*?)^\`\`\`[ \t]*$", re.S | re.M)
REQUIRED_HEADINGS = {
    "goal": r"(?im)^#{2,4}\s*(?:目标|目的|Goal|Intent|Problem)\b?",
    "boundary": r"(?im)^#{2,4}\s*(?:系统边界|边界|Boundary|System boundary|Scope)\b?",
    "flow": r"(?im)^#{2,4}\s*(?:数据流|信息流|Data flow|Information flow|信息如何流转)\b?",
    "tradeoff": r"(?im)^#{2,4}\s*(?:权衡|取舍|Trade.?offs?|Options|架构决策)\b?",
    "risks": r"(?im)^#{2,4}\s*(?:风险|假设|失败恢复|Risks?|Assumptions?|Failure|Recovery)\b?",
}
# Diagram node labels are deliberately not interpreted as executable instructions.
FORBIDDEN = re.compile(r"(?im)^\s*(?:click\s|%%\{init:|%%\{config:|accTitle:.*<script)")


def validate(document):
    if isinstance(document, bytes):
        if len(document) > MAX_BYTES:
            raise ValueError("architecture sketch exceeds size limit")
        try:
            document = document.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("architecture sketch must be UTF-8") from error
    if not isinstance(document, str) or not document.strip():
        raise ValueError("missing architecture sketch")
    if len(document.encode("utf-8")) > MAX_BYTES:
        raise ValueError("architecture sketch exceeds size limit")
    missing = [name for name, pattern in REQUIRED_HEADINGS.items()
               if not re.search(pattern, document)]
    if missing:
        raise ValueError("missing architecture reasoning sections: " + ", ".join(missing))
    blocks = [x.strip() for x in BLOCK.findall(document)]
    if not blocks:
        raise ValueError("architecture sketch requires fenced mermaid diagrams")
    if len(blocks) > 12:
        raise ValueError("too many Mermaid diagrams")
    diagrams = []
    graph_found = False
    for block in blocks:
        if FORBIDDEN.search(block):
            raise ValueError("unsafe Mermaid directive/click handler forbidden")
        first = next((line.strip() for line in block.splitlines() if line.strip()), "")
        kind = first.split(maxsplit=1)[0].lower() if first else ""
        if kind not in {"flowchart", "graph", "sequencediagram", "statediagram-v2",
                        "statediagram", "erdiagram", "classdiagram"}:
            raise ValueError("unsupported/empty Mermaid diagram declaration")
        if kind in {"flowchart", "graph"}:
            graph_found = True
            if not re.search(r"-->|-.->|==>", block):
                raise ValueError("system flowchart has no visible dependency/data edge")
        if len(block.splitlines()) < 3:
            raise ValueError("Mermaid diagram is too small to describe architecture")
        diagrams.append(kind)
    if not graph_found:
        raise ValueError("architecture sketch needs a system flowchart")
    return {
        "status": "ARCHITECTURE_STRUCTURE_PRESENT",
        "diagrams": diagrams,
        "reasoning_sections": sorted(REQUIRED_HEADINGS),
        "mermaid_render_verified": False,
        "technical_correctness_verified": False,
        "human_review_verified": False,
        "contract_generation_authorized": False,
        "next": "Review architecture, trade-offs, boundaries and failure modes before approving Foundry stage 2",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="UTF-8 Markdown architecture sketch")
    args = parser.parse_args(argv)
    try:
        result = validate(args.file.read_bytes())
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
