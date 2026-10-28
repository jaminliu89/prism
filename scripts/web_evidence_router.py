#!/usr/bin/env python3
"""Deterministic evidence route/failover/hash validation. Does not fetch or install."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"sources/skillhub/site/tool-collaboration.json"
ACCESS_BLOCKS={"access_denied","robots_disallow","site_policy","unauthorized"}

def load(path=CONTRACT):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("not_a_runtime") is not True: raise ValueError("contract runtime boundary removed")
    ids={x["id"] for x in data["resources"]}
    for rule in data["selection_rules"]:
        if not set(rule["candidates"])<=ids: raise ValueError("unregistered candidate")
    return data

def route(intent,host_verified=(),contract=None):
    data=contract or load()
    rules=[x for x in data["selection_rules"] if x["intent"]==intent]
    if len(rules)!=1: raise ValueError("unknown intent")
    rule=rules[0]
    known={x["id"] for x in data["resources"]}
    if not set(host_verified)<=known: raise ValueError("host claimed unknown tool")
    selected=next((c for c in rule["candidates"] if c in host_verified),None)
    return {"status":"HOST_DECLARED_NOT_EXECUTED" if selected else "NEEDS_RUNTIME_DISCOVERY",
            "intent":intent,"packet":rule["packet"],"candidates":rule["candidates"],
            "selected":selected,"exit_criterion":rule["success"],"tool_execution_verified":False}

def fallback(intent,engine,attempts,failure,contract=None):
    data=contract or load()
    if attempts<1: raise ValueError("invalid attempts")
    r=route(intent,contract=data)
    if engine not in r["candidates"]: raise ValueError("engine not in task route")
    if failure in ACCESS_BLOCKS:
        return {"status":"BLOCKED","next_condition":"Acquire legitimate permission; never bypass target protections."}
    if failure not in {"missing_tool","timeout","parse_error","schema_mismatch","navigation_failure"}:
        raise ValueError("invalid failure")
    if attempts<data["fallback_policy"]["max_same_method_failures"] and failure!="missing_tool":
        return {"status":"RETRY_SAME_METHOD","candidate":engine,"exit_criterion":r["exit_criterion"]}
    i=r["candidates"].index(engine)+1
    if i>=len(r["candidates"]):
        return {"status":"BLOCKED","next_condition":"Report partial evidence and seek authorized alternate surface."}
    return {"status":"VERIFY_FALLBACK_BEFORE_EXECUTION","candidate":r["candidates"][i],
            "exit_criterion":r["exit_criterion"],"tool_execution_verified":False}

def verify_record(row,root,contract=None):
    data=contract or load()
    if any(key not in row for key in data["evidence_policy"]["required"]): raise ValueError("missing evidence field")
    if row["claim_level"] not in data["evidence_policy"]["accepted_claim_levels"]: raise ValueError("invalid claim level")
    if row["tool"] not in {x["id"] for x in data["resources"]}: raise ValueError("unregistered tool")
    for k in ("task_id","target","revision","case_id","tool","observed_at","next_condition"):
        if not isinstance(row[k],str) or not row[k].strip(): raise ValueError("missing text")
    p=Path(row["evidence_path"])
    if p.is_absolute() or ".." in p.parts or not p.parts: raise ValueError("outside evidence root")
    root=Path(root).resolve(); current=root
    for part in p.parts:
        current=current/part
        if current.is_symlink(): raise ValueError("symlink not allowed")
    if not current.is_file() or not current.resolve().is_relative_to(root): raise ValueError("missing or outside evidence")
    if current.stat().st_size>20*1024*1024: raise ValueError("evidence over budget")
    digest=hashlib.sha256(current.read_bytes()).hexdigest()
    if digest!=row["sha256"]: raise ValueError("hash mismatch")
    return {"status":"STRUCTURAL_EVIDENCE_VERIFIED_NOT_SEMANTICALLY_REVIEWED",
            "sha256":digest,"tool_execution_verified":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest="cmd",required=True)
    a=subs.add_parser("route"); a.add_argument("--intent",required=True);a.add_argument("--host-verified",nargs="*",default=[])
    b=subs.add_parser("fallback");b.add_argument("--intent",required=True);b.add_argument("--engine",required=True);b.add_argument("--attempts",type=int,required=True);b.add_argument("--failure",required=True)
    v=subs.add_parser("verify-evidence");v.add_argument("--record",required=True,type=Path);v.add_argument("--artifact-root",required=True,type=Path)
    x=p.parse_args()
    result=route(x.intent,x.host_verified) if x.cmd=="route" else fallback(x.intent,x.engine,x.attempts,x.failure) if x.cmd=="fallback" else verify_record(json.loads(x.record.read_text(encoding="utf-8")),x.artifact_root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
