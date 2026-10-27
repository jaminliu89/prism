"""Structured specialist reviews for product planning. Does not invoke models."""

ROLES = ("pm", "research", "ux", "architect", "security", "qa", "challenger")
VERDICTS = ("support", "concern", "oppose")
SEVERITIES = ("info", "medium", "high", "critical")


def create_topic(data, stage, question, owner):
    if not question.strip() or not owner.strip():
        raise ValueError("topic needs a question and owner")
    topics = data.setdefault("panel_topics", [])
    topic_id = "PNL-%04d" % (len(topics) + 1)
    topic = {"id": topic_id, "stage": stage, "question": question.strip(),
             "owner_claim": owner, "status": "open", "opinions": [],
             "resolution": None, "independent_validation": False}
    topics.append(topic)
    return topic


def topic(data, topic_id):
    for item in data.get("panel_topics", []):
        if item["id"] == topic_id:
            return item
    raise ValueError("unknown review topic")


def add_opinion(data, topic_id, role, actor, verdict, severity,
                reasoning, evidence, counterexample):
    item = topic(data, topic_id)
    if item["status"] != "open":
        raise ValueError("review topic is closed")
    if role not in ROLES or verdict not in VERDICTS or severity not in SEVERITIES:
        raise ValueError("invalid role, opinion or severity")
    if not all(value.strip() for value in (actor, reasoning, evidence, counterexample)):
        raise ValueError("opinion must include reasoning, evidence and a falsification example")
    if any(x["role"] == role and x["actor_claim"] == actor for x in item["opinions"]):
        raise ValueError("duplicate opinion from same claimed role and actor")
    opinion = {"role": role, "actor_claim": actor, "verdict": verdict,
               "severity": severity, "reasoning": reasoning.strip(),
               "evidence": evidence.strip(), "counterexample": counterexample.strip(),
               "verification": "UNVERIFIED_SOURCE",
               "identity_verified": False}
    item["opinions"].append(opinion)
    return opinion


def unresolved(data, stage=None):
    items = [x for x in data.get("panel_topics", []) if x["status"] == "open"]
    if stage is not None:
        items = [x for x in items if x["stage"] == stage]
    return [{"id": x["id"], "stage": x["stage"], "question": x["question"],
             "opinion_count": len(x["opinions"]),
             "serious_disagreement": any(
                 p["verdict"] == "oppose" and p["severity"] in ("high", "critical")
                 for p in x["opinions"])}
            for x in items]


def resolve(data, topic_id, outcome, decision_owner, rationale):
    item = topic(data, topic_id)
    if item["status"] != "open":
        raise ValueError("already resolved")
    if outcome not in ("adopt", "revise", "defer", "reject"):
        raise ValueError("unsupported resolution")
    if not decision_owner.strip() or not rationale.strip():
        raise ValueError("decision requires actor and rationale")
    if not item["opinions"]:
        raise ValueError("cannot resolve without expert input")
    if not any(x["role"] == "challenger" or x["verdict"] in ("concern", "oppose")
               for x in item["opinions"]):
        raise ValueError("adversarial review is missing")
    item["status"] = "resolved"
    item["resolution"] = {"outcome": outcome, "owner_claim": decision_owner,
                          "rationale": rationale.strip(),
                          "identity_verified": False}
    return item


def brief(data, topic_id):
    item = topic(data, topic_id)
    return {"topic": item["id"], "question": item["question"],
            "stage": item["stage"], "roles": list(ROLES),
            "required_opinion": ["verdict", "reasoning", "evidence", "counterexample"],
            "instruction": "Independently assess product value, scope, dependencies and user impact. Label unsupported claims. Do not execute tools or modify approved plans.",
            "protected_information": "Avoid copying private prompts, credentials or confidential orchestration into external agent prompts.",
            "opinions": item["opinions"], "resolution": item["resolution"],
            "execution": "MANUAL_AGENT_ADAPTER_REQUIRED"}
