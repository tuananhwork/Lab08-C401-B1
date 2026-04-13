# 📄 DOCUMENT ANALYSIS — Sprint 1 Task 1A

**Task:** Load + analyze documents (5 files). Mô tả structure từng document.  
**Person:** Person 1  
**Sprint:** 1  
**Date:** 2026-04-13

---

## 📊 Overview

5 documents từ `/data/docs/`:
1. `access_control_sop.txt` — IT Security Policy
2. `hr_leave_policy.txt` — HR Leave & Benefits Policy
3. `it_helpdesk_faq.txt` — IT Helpdesk FAQ
4. `policy_refund_v4.txt` — Refund Policy (v4)
5. `sla_p1_2026.txt` — IT SLA Policy

---

## 1️⃣ Document 1: ACCESS_CONTROL_SOP.txt

### Metadata
- **Source:** it/access-control-sop.md
- **Department:** IT Security
- **Effective Date:** 2026-01-01
- **Access Level:** internal
- **Language:** Vietnamese
- **Content Type:** Procedural Policy / SOP

### Structure
```
Title: QUY TRÌNH KIỂM SOÁT TRUY CẬP HỆ THỐNG (ACCESS CONTROL SOP)

Metadata Header:
├── Source: it/access-control-sop.md
├── Department: IT Security
├── Effective Date: 2026-01-01
└── Access: internal

Main Content Sections (4 sections):
├── Ghi chú (Notes): Historical naming info
├── Section 1: Phạm vi và mục đích (Scope & Purpose)
├── Section 2: Phân cấp quyền truy cập (Access Hierarchy)
│   ├── Level 1 — Read Only
│   ├── Level 2 — Standard Access
│   ├── Level 3 — Elevated Access
│   └── Level 4 — Admin Access
├── Section 3: Quy trình yêu cầu cấp quyền (Request Process)
│   └── 5-step procedure with approval chain
└── Section 4: Escalation (Emergency Access)
    └── On-call escalation for P1 incidents (max 24h)
```

### Key Information Elements
- **4 Access Levels** with different approval chains + processing time
- **5-step approval process**: Request → Line Manager → IT Admin → IT Security → Notification
- **Escalation rules**: Temporary access up to 24h for P1 incidents
- **Dependencies**: Line Manager, IT Admin, IT Security approval

### Document Characteristics
- **Format**: Structured sections with subsections (Vietnamese)
- **Density**: High technical detail per section
- **Clarity**: Very clear hierarchy and role definitions
- **Actionability**: Clear steps and prerequisites

---

## 2️⃣ Document 2: HR_LEAVE_POLICY.txt

### Metadata
- **Source:** hr/leave-policy-2026.pdf
- **Department:** HR
- **Effective Date:** 2026-01-01
- **Access Level:** internal
- **Language:** Vietnamese
- **Content Type:** Personnel Policy

### Structure
```
Title: CHÍNH SÁCH NGHỈ PHÉP VÀ PHÚC LỢI NHÂN SỰ (Leave & Benefits Policy)

Metadata Header:
├── Source: hr/leave-policy-2026.pdf
├── Department: HR
├── Effective Date: 2026-01-01
└── Access: internal

Main Content Sections (4 sections):
├── Phần 1: Các loại nghỉ phép (Leave Types)
│   ├── Annual Leave (12/15/18 days based on tenure)
│   ├── Sick Leave (10 days/year, need doc after 3 days)
│   ├── Maternity Leave (6 months statutory)
│   └── Public Holidays (varies yearly)
├── Phần 2: Quy trình xin nghỉ phép (Leave Request Process)
│   ├── 3-step process: Request → Manager Approval → Notification
│   └── Emergency process with direct manager approval
├── Phần 3: Chính sách làm thêm giờ (Overtime Policy)
│   └── 150%/200%/300% rates based on day type
└── Phần 4: Remote work policy (2 days/week max)
    └── Mandatory on-site: Tuesday & Friday
```

### Key Information Elements
- **Leave entitlements** (varies by tenure and type)
- **3-step request process** with 3-day notice requirement
- **Multiple leave categories** with different rules
- **Overtime multipliers** for different day types
- **Remote work limits** (2 days/week, mandatory Tuesday+Friday)

### Document Characteristics
- **Format**: Numbered sections with detailed subsections
- **Density**: Mix of categorical and procedural info
- **Clarity**: Clear entitlements and approval flow
- **Actionability**: Clear timeline expectations (3-day notice, 1-day approval)

---

## 3️⃣ Document 3: IT_HELPDESK_FAQ.txt

### Metadata
- **Source:** support/helpdesk-faq.md
- **Department:** IT
- **Effective Date:** 2026-01-20
- **Access Level:** internal
- **Language:** Vietnamese
- **Content Type:** FAQ / Knowledge Base

### Structure
```
Title: IT HELPDESK FAQ — CÂU HỎI THƯỜNG GẶP

Metadata Header:
├── Source: support/helpdesk-faq.md
├── Department: IT
├── Effective Date: 2026-01-20
└── Access: internal

Main Content Q&A Sections (5 sections, each 2-3 Q&A pairs):
├── Section 1: Tài khoản và mật khẩu (Account & Password)
│   ├── Q: Forgot password?
│   ├── Q: Account locked after how many attempts?
│   └── Q: Password change frequency?
├── Section 2: VPN và kết nối từ xa (VPN & Remote)
│   ├── Q: Which VPN software?
│   ├── Q: Connection drops?
│   └── Q: Device limit per account?
├── Section 3: Phần mềm và license (Software & License)
│   ├── Q: How to request new software?
│   └── Q: License renewal responsibility?
├── Section 4: Thiết bị và phần cứng (Hardware)
│   ├── Q: Laptop provision timeline?
│   └── Q: Broken laptop reporting?
└── Section 5: Email và lịch (Email & Calendar)
    └── Q: Mailbox full?
    └── [Section cut off in document]
```

### Key Information Elements
- **Q&A format**: Direct answers to common problems
- **Practical contacts**: Ext. numbers, email addresses, URLs
- **Support channels**: Jira tickets with priority levels (P2, P3)
- **SLA references**: 5 min email, 30 day license reminder, etc.
- **Self-service options**: SSO reset portal, email increase tickets

### Document Characteristics
- **Format**: Q&A pairs grouped by topic
- **Density**: Answers are concise and action-oriented
- **Clarity**: Easy to scan for specific problem
- **Actionability**: Every answer includes "WHAT to do" or "WHO to contact"

---

## 4️⃣ Document 4: POLICY_REFUND_V4.txt

### Metadata
- **Source:** policy/refund-v4.pdf
- **Department:** CS (Customer Service)
- **Effective Date:** 2026-02-01
- **Access Level:** internal
- **Language:** Vietnamese
- **Content Type:** Business Policy / Terms & Conditions

### Structure
```
Title: CHÍNH SÁCH HOÀN TIỀN - PHIÊN BẢN 4 (Refund Policy v4)

Metadata Header:
├── Source: policy/refund-v4.pdf
├── Department: CS
├── Effective Date: 2026-02-01
└── Access: internal

Main Content Articles (6 sections):
├── Điều 1: Phạm vi áp dụng (Scope of Application)
│   └── Applies to orders from 2026-02-01 onwards
├── Điều 2: Điều kiện được hoàn tiền (Refund Eligibility)
│   ├── Product defects (manufacturer issue)
│   ├── 7 business day request window
│   └── Unused / sealed product
├── Điều 3: Điều kiện áp dụng và ngoại lệ (Conditions & Exceptions)
│   ├── Refund conditions met
│   └── Exclusions: Digital goods, Flash Sale discounts, Activated products
├── Điều 4: Quy trình xử lý yêu cầu (Processing Procedure)
│   └── 4-step workflow: Request → CS Review → Finance Approval → Refund (3-5 days)
├── Điều 5: Hình thức hoàn tiền (Refund Methods)
│   ├── Original payment method (100% cases)
│   └── Store credit option (110% value)
└── Điều 6: Liên hệ và hỗ trợ (Support Contact)
    ├── Email: cs-refund@company.internal
    ├── Hotline: ext. 1234
    └── Hours: Mon-Fri, 8:00-17:30
```

### Key Information Elements
- **Eligibility criteria**: 3 conditions (defect, timing, condition)
- **Exclusion rules**: Digital goods, promotional discounts, activated products
- **4-step workflow**: Request → CS (1 day) → Finance (3-5 days)
- **Refund options**: Original payment method OR store credit (110%)
- **Contact info**: Email, phone extension, business hours

### Document Characteristics
- **Format**: Numbered articles (legal contract style)
- **Density**: High legal precision, numbered conditions
- **Clarity**: Explicit eligibility rules and exclusions
- **Actionability**: Clear contact methods and timelines

---

## 5️⃣ Document 5: SLA_P1_2026.txt

### Metadata
- **Source:** support/sla-p1-2026.pdf
- **Department:** IT
- **Effective Date:** 2026-01-15
- **Access Level:** internal
- **Language:** Vietnamese
- **Content Type:** Service Level Agreement / Operations Policy

### Structure
```
Title: SLA TICKET - QUY ĐỊNH XỬ LÝ SỰ CỐ (Incident SLA Policy)

Metadata Header:
├── Source: support/sla-p1-2026.pdf
├── Department: IT
├── Effective Date: 2026-01-15
└── Access: internal

Main Content Sections (3+ sections, partially visible):
├── Phần 1: Định nghĩa mức độ ưu tiên (Priority Definitions)
│   ├── P1 — CRITICAL: Full system outage, no workaround
│   │   └── Example: Database down, API gateway down, login impossible
│   ├── P2 — HIGH: Partial system impact, workaround exists
│   │   └── Example: Feature unavailable, affects user group
│   ├── P3 — MEDIUM: Minor impact, users can work
│   └── P4 — LOW: Enhancement request, minor UI bug
├── Phần 2: SLA theo mức độ ưu tiên (SLAs by Priority)
│   ├── P1: 15 min first response, 4h resolution, 10 min auto-escalate
│   ├── P2: 2h first response, 1 day resolution, 90 min auto-escalate
│   ├── P3: 1 day first response, 5 day resolution
│   └── P4: 3 day first response, 2-4 week resolution (per sprint)
└── Phần 3: Quy trình xử lý sự cố P1 (P1 Incident Workflow)
    ├── Step 1: Reception (confirmation within 5 min)
    ├── Step 2: Notification (Slack + email immediately)
    └── [Section continues...]
```

### Key Information Elements
- **4 Priority levels** (P1-P4) with clear definitions
- **SLA timelines**: First response varies (15 min - 3 days)
- **Escalation rules**: Automatic after threshold (10 min P1, 90 min P2)
- **Stakeholder notification**: Email, Slack, 30-min updates for P1
- **On-call procedures**: Emergency escalation chain

### Document Characteristics
- **Format**: Hierarchical sections with priority levels
- **Density**: High operational detail
- **Clarity**: Precise SLA numbers and escalation criteria
- **Actionability**: Clear on-call procedures and notification flow

---

## 📋 Comparative Summary

| Aspect | Access Control | Leave Policy | Helpdesk FAQ | Refund Policy | SLA Policy |
|--------|---|---|---|---|---|
| **Type** | Procedural SOP | Personnel Policy | FAQ/Knowledge Base | Business Terms | Operational SLA |
| **Primary Purpose** | Define access approval | Manage leave entitlements | Support troubleshooting | Handle customer refunds | Define incident response |
| **Structure** | Sections + Levels | Numbered parts | Q&A pairs | Articles + procedures | Priority hierarchy |
| **Main Actors** | IT Security, Manager | HR, Employee | IT Support, User | Customer, CS, Finance | On-call engineer, Lead |
| **Key Metric** | Approval time (1-5 days) | Leave days/year | Response time (5 min) | Processing time (3-5 days) | SLA (15 min - 3 days) |
| **Complexity** | Medium (4 levels) | Medium (4 categories) | Low (Q&A) | Medium (3+ conditions) | High (4 priorities + escalation) |
| **Effective Date** | 2026-01-01 | 2026-01-01 | 2026-01-20 | 2026-02-01 | 2026-01-15 |

---

## 🎯 Key Metadata Fields Present in All Documents

1. **Source** (Reference location)
2. **Department** (Owner/Authority)
3. **Effective Date** (Policy version date)
4. **Access Level** (internal/restricted)

---

## 📝 Suggested Metadata Schema for Indexing

Based on document analysis, proposed metadata fields for RAG system:

```json
{
  "source": "string",           // Document origin
  "department": "string",       // Owning department
  "doc_type": "string",         // Policy/SOP/FAQ/Agreement
  "effective_date": "date",     // When policy became effective
  "access_level": "string",     // internal/restricted/public
  "section": "string",          // Section name within document
  "priority_level": "string",   // For SLAs (P1-P4) / Leave types / Access levels
  "version": "string",          // Version number (e.g., v4, 2026)
  "language": "string"          // Vietnamese/English
}
```

---

## ✅ Summary

**Document Analysis Complete:**
- ✅ 5 documents loaded and analyzed
- ✅ Structure of each document described
- ✅ Key information elements identified
- ✅ Metadata fields extracted
- ✅ Comparative analysis created
- ✅ Suggested schema for indexing

**Ready for Phase 1 Deliverables:**
1. All documents have clear structure
2. Metadata schema ready for Task 1D (Person 4)
3. Documents are well-suited for chunking (Task 1C - Person 3)
4. Ready for preprocessing (Task 1B - Person 2)

---

**Generated by Person 1 — Sprint 1 Task 1A**  
**Output:** Document analysis notes (this file)
