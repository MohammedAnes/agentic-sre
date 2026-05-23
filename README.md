# Agentic SRE with AWS DevOps Agent

An end-to-end autonomous incident response system built on AWS DevOps Agent.
When a CloudWatch alarm fires, the agent automatically investigates root cause,
correlates telemetry, generates a mitigation plan, and posts findings to Slack —
without waking up an engineer.

> Built as a companion to: **"I Built an Agentic SRE on AWS DevOps Agent — Here's What the Official Guide Left Out"**

---

## Architecture

```
CloudWatch Alarm (error rate / duration / throttling)
        │
        ▼
    SNS Topic
        │
        ▼
  Webhook Handler Lambda
  (HMAC-signed payload)
        │
        ▼
  AWS DevOps Agent Space
  (CloudWatch + GitHub + Slack)
        │
        ├── Investigates using Lambda Runbook Skill
        ├── Correlates metrics + logs + deployments
        ├── Generates mitigation plan
        └── Posts root cause to Slack
                │
                ▼
        Agent-Ready Spec → Kiro (code fix)
```

**Single-account setup.** Unlike the AWS reference architecture (3 accounts + Splunk),
this repo is designed to run in one AWS account so you can get started in under an hour.

---

## Project Structure

```
agentic-sre/
├── app.py                          # CDK entry point
├── cdk.json                        # CDK config
├── requirements.txt
├── infra/
│   └── stacks/
│       ├── demo_app_stack.py       # Demo Lambda being monitored
│       ├── alarm_stack.py          # 3 CloudWatch alarms + SNS topic
│       └── webhook_stack.py        # Webhook handler Lambda
├── demo_app/
│   └── index.py                    # Lambda with controllable failure modes
├── webhook_handler/
│   └── index.py                    # SNS → DevOps Agent webhook forwarder
├── skills/
│   └── lambda-investigation-runbook.md  # Custom DevOps Agent Skill
└── scripts/
    └── trigger.py                  # Manual alarm trigger for demos
```

---

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.12+
- AWS CDK v2 (`npm install -g aws-cdk`)
- AWS DevOps Agent already set up with an Agent Space
- Slack workspace connected to DevOps Agent

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Bootstrap CDK (first time only)

```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```

### 3. Deploy all stacks

```bash
cdk deploy --all
```

### 4. Store the DevOps Agent webhook secret

After configuring your DevOps Agent Space and creating a webhook,
save the URL and secret to Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name agentic-sre/devops-agent-webhook \
  --secret-string '{"url":"YOUR_WEBHOOK_URL","secret":"YOUR_HMAC_SECRET"}'
```

### 5. Upload the custom Skill to DevOps Agent

In the DevOps Agent Operator Console:
1. Go to **Skills** → **Add Skill** → **Upload Skill**
2. Upload `skills/lambda-investigation-runbook.md`
3. Assign the skill to your Agent Space

### 6. Connect GitHub (optional but recommended)

In your Agent Space → Capabilities → Pipeline → GitHub
Complete the OAuth flow and select your repositories.

---

## Triggering a Demo Investigation

### Option A — Force the alarm directly (fastest)

```bash
python scripts/trigger.py error
```

### Option B — Naturally trigger via Lambda invocations

```bash
python scripts/trigger.py burst 15
```

### Option C — AWS CLI

```bash
aws cloudwatch set-alarm-state \
  --alarm-name agentic-sre-high-error-rate \
  --state-value ALARM \
  --state-reason "Demo trigger"
```

Then watch your Slack channel — the DevOps Agent will post investigation
updates within ~30 seconds.

### Reset all alarms after demo

```bash
python scripts/trigger.py ok
```

---

## What the AWS Official Guide Covers vs This Repo

| Topic | AWS Official Blog | This Repo |
|---|---|---|
| Architecture | 3 accounts + Splunk | Single account, no Splunk |
| IaC | Manual console steps | Full CDK (Python) |
| Webhook handler | Node.js snippet | Full Python Lambda |
| Custom Skills | Mentioned briefly | Complete runbook example |
| Demo triggers | Not provided | `scripts/trigger.py` |

---

## Alarms Deployed

| Alarm | Trigger | Priority |
|---|---|---|
| `agentic-sre-high-error-rate` | Error rate > 20% over 5 min | HIGH |
| `agentic-sre-high-duration` | P99 duration > 24s over 10 min | HIGH |
| `agentic-sre-throttling` | Any throttles in 5 min | MEDIUM |

---

## Estimated AWS Cost

Running this demo costs approximately **$0–2/month** at low invocation volumes.
The main cost driver is Lambda invocations and CloudWatch metrics.
AWS DevOps Agent has a **2-month free trial** — start there.

---

## Related

- [AWS DevOps Agent product page](https://aws.amazon.com/devops-agent/)
- [Official Agentic SRE blog post](https://aws.amazon.com/blogs/devops/building-an-end-to-end-agentic-sre-using-aws-devops-agent/)
- [DevOps Agent Skills documentation](https://docs.aws.amazon.com/devopsagent/latest/userguide/about-aws-devops-agent-devops-agent-skills.html)

---

## License

MIT
