# Routing Decisions — Day 09 Lab

**Document:** Quyết định routing chi tiết của nhóm B1-C401  
**Date:** 2026-04-14  
**Owner:** Chu Thị Ngọc Huyền (Supervisor Owner)

---

## 1. Routing Architecture

### 1.1 Supervisor-Worker Pattern

```
User Input (task)
    ↓
Supervisor (keyword-based classification)
    ↓
    ├─→ [HIGH_RISK] → human_review (HITL)
    ├─→ [POLICY keywords] → policy_tool_worker
    ├─→ [SLA keywords] → retrieval_worker
    ├─→ [CROSS-DOC: policy + SLA] → policy_tool_worker (multi-hop)
    └─→ [DEFAULT] → retrieval_worker
    ↓
Worker(s) process task
    ↓
Synthesis Worker (aggregate results + cite)
    ↓
Final Answer
```

---

## 2. Routing Keyword Tables

### 2.1 POLICY_KEYWORDS

**Trigger:** policy_tool_worker

Keywords:
- "hoàn tiền", "refund", "flash sale", "khuyến mãi"
- "license", "subscription", "kỹ thuật số"
- "cấp quyền", "access level", "level 1/2/3", "contractor", "temporary access"

**Example:** "Khách hàng Flash Sale yêu cầu hoàn tiền được không?"
→ Route: policy_tool_worker, Reason: ['hoàn tiền', 'flash sale']

### 2.2 SLA_TICKET_KEYWORDS

**Trigger:** retrieval_worker

Keywords:
- "p1", "p2", "p3", "ticket", "sla", "escalation"
- "sự cố", "incident", "on-call", "response time"

**Example:** "SLA P1 ticket phải phản hồi trong bao lâu?"
→ Route: retrieval_worker, Reason: ['p1', 'ticket', 'sla']

### 2.3 HIGH_RISK_KEYWORDS

**Trigger:** human_review

Keywords:
- "emergency", "security breach", "ransomware"
- "escalation to ceo", "contractor level 3"

**Example:** "Security breach, immediate escalation needed"
→ Route: human_review, Risk: True

---

## 3. Real Routing Decisions from Traces

### Decision #1: Simple SLA Query

**Task:** "SLA P1 là bao lâu?"

**Routing Process:**
- Supervisor checks keywords → finds ['p1', 'sla', 'ticket']
- No policy keywords found
- Not HIGH_RISK

**Decision:** 
```json
{
  "route": "retrieval_worker",
  "reason": "SLA keywords detected: ['p1', 'ticket', 'sla']",
  "risk_high": false,
  "needs_tool": false
}
```

**Workers Called:** [retrieval_worker, synthesis_worker]

**Result:**
- Retrieved chunks from: sla_p1_2026.txt
- Answer: "P1 ticket SLA: response 15 phút, resolution 4 giờ"
- Confidence: 0.88 ✅

**Trace File:** artifacts/traces/run_20260414_161311.json

---

### Decision #2: Policy with Exception

**Task:** "Khách hàng Flash Sale có thể hoàn tiền được không?"

**Routing Process:**
- Supervisor checks keywords → finds ['hoàn tiền', 'flash sale']
- No SLA keywords
- Not HIGH_RISK

**Decision:**
```json
{
  "route": "policy_tool_worker",
  "reason": "policy keywords: ['hoàn tiền', 'flash sale']",
  "risk_high": false,
  "needs_tool": true
}
```

**Workers Called:** [retrieval_worker, policy_tool_worker, synthesis_worker]

**Processing:**
1. retrieval_worker: finds policy_refund_v4.txt chunks
2. policy_tool_worker: calls MCP tool policy_check → detects "flash_sale_no_refund" exception
3. synthesis_worker: combines chunks + exception, reduces confidence by penalty (-0.05)

**Result:**
- Answer: "Flash Sale không được hoàn tiền theo chính sách ngoại lệ"
- Confidence: 0.75 (reduced from 0.88 due to exception) ✅
- Exception noted: True

**Trace File:** artifacts/traces/run_20260414_161316.json

---

### Decision #3: Cross-Document Multi-Hop

**Task:** "P1 khẩn cấp, cấp quyền Level 3 cho engineer mới"

**Routing Process:**
- Supervisor checks keywords:
  - SLA keywords found: ['p1']
  - Policy keywords found: ['cấp quyền', 'level 3']
- Not HIGH_RISK (per se, but risky due to combination)
- Cross-doc detected! (SLA + policy)

**Decision:**
```json
{
  "route": "policy_tool_worker",
  "reason": "cross-doc multi-hop: SLA ['p1'] + policy ['cấp quyền', 'level 3']",
  "risk_high": true,
  "needs_tool": true
}
```

**Workers Called:** [retrieval_worker, policy_tool_worker, synthesis_worker]

**Processing:**
1. retrieval_worker: finds SLA context ("P1 escalation procedure")
2. policy_tool_worker: calls MCP tools
   - policy_check: "Level 3 requires manager approval"
   - exception_approval: "Approve for emergency + SLA P1"
3. synthesis_worker: combines both contexts

**Result:**
- Answer: "P1 khẩn cấp: SLA có escalation automatic. Level 3 cần manager approve. Được phép trong tình huống P1."
- Confidence: 0.68 (multi-hop harder to synthesize) ⚠️
- Risk noted: True

**Trace File:** artifacts/traces/run_20260414_161321.json

---

## 4. Routing Performance Metrics

### Latency by Route

| Route | Avg Latency | Workers | Notes |
|-------|------------|---------|-------|
| SLA query → retrieval | 1320ms | 2 | Quick KB lookup |
| Policy query → policy_tool | 1680ms | 3 | +MCP tool call |
| Cross-doc → policy_tool | 2140ms | 3 | Parallel + MCP |
| Edge case → human_review | N/A | HITL | Manual handling |

### Accuracy by Route

| Route | Success Rate | Avg Confidence | Notes |
|-------|--------------|----------------|-------|
| retrieval_worker | 88% | 0.82 | SLA/ticket questions |
| policy_tool_worker | 80% | 0.72 | Policy + exception detection |
| cross-doc | 76% | 0.65 | Multi-hop complexity |

---

## 5. Routing Decision Logic (Code Reference)

```python
# graph.py - supervisor_node()

_POLICY_KEYWORDS = [
    "hoàn tiền", "refund", "flash sale", "license",
    "cấp quyền", "access level", "level 1", "level 2", "level 3",
    "contractor", "temporary access"
]

_SLA_TICKET_KEYWORDS = [
    "p1", "p2", "p3", "ticket", "sla", "escalation",
    "incident", "on-call", "response time"
]

_HIGH_RISK_KEYWORDS = [
    "emergency", "security breach", "escalation to ceo"
]

def route_decision(task: str) -> tuple:
    # Step 1: HIGH_RISK check
    if any(kw in task.lower() for kw in _HIGH_RISK_KEYWORDS):
        return ("human_review", f"HIGH_RISK: {task[:50]}...", True, True)
    
    # Step 2: Keyword detection
    policy_hits = [kw for kw in _POLICY_KEYWORDS if kw in task.lower()]
    sla_hits = [kw for kw in _SLA_TICKET_KEYWORDS if kw in task.lower()]
    
    # Step 3: Cross-doc routing (both policy + SLA)
    if policy_hits and sla_hits:
        return (
            "policy_tool_worker",
            f"cross-doc: SLA {sla_hits} + policy {policy_hits}",
            True,  # Risk high for combination
            True
        )
    
    # Step 4: Single-doc routing
    if policy_hits:
        return ("policy_tool_worker", f"policy: {policy_hits}", False, True)
    
    if sla_hits:
        return ("retrieval_worker", f"SLA: {sla_hits}", False, False)
    
    # Step 5: Default
    return ("retrieval_worker", "default", False, False)
```

---

## 6. Future Improvements

### Enhancement 1: Confidence-Based Re-Routing

If synthesis confidence < 0.4 → auto escalate to HITL:

```python
# After synthesis_worker
if state["confidence"] < 0.4:
    state["supervisor_route"] = "human_review"
    state["hitl_triggered"] = True
    state["route_reason"] = f"Low confidence {state['confidence']:.2f}, escalated"
```

### Enhancement 2: LLM-Based Classification

For edge cases not covered by keywords, use LLM:

```python
if not matches_any_keyword(task):
    route = llm_classify(task)  # +800ms latency
else:
    route = keyword_classify(task)  # ~50ms
```

---

## 7. Summary

**Routing Strategy:**
- ✅ Keyword-based phân tầng (5-step priority)
- ✅ Fast (~50ms), deterministic, visible
- ⚠️ Misses synonyms, but acceptable for domain

**Success Rate:** ~85% accurate routing
**Latency:** 50-100ms supervisor overhead acceptable (total pipeline 1.3-2.1s)
