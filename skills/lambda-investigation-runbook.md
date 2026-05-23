# Lambda Incident Investigation Runbook

## Purpose
Use this skill when investigating AWS Lambda function errors, timeouts,
high duration, or throttling incidents for the `agentic-sre-demo-app` service.

## Investigation Sequence

Follow these steps **in order**. Do not skip steps.

### Step 1 — Confirm the Alarm
- Identify which alarm triggered: error rate, duration, or throttling
- Check the alarm state history in CloudWatch for the last 30 minutes
- Note the exact time the alarm entered ALARM state

### Step 2 — Check Lambda Metrics (Last 30 Minutes)
Pull these metrics for function `agentic-sre-demo-app`:
- `Errors` — total error count
- `Invocations` — total invocation count
- `Duration` — p50, p95, p99
- `Throttles` — total throttle count
- `ConcurrentExecutions` — max value

### Step 3 — Check Recent Logs
Query CloudWatch Logs for `/aws/lambda/agentic-sre-demo-app`:
- Look for ERROR or CRITICAL level log lines
- Look for timeout messages: `Task timed out after`
- Look for exception traces — note the exception type and message
- Time window: alarm trigger time ± 10 minutes

### Step 4 — Correlate With Recent Deployments
Check CodePipeline or GitHub for deployments in the last 2 hours:
- Was a new version deployed before the incident?
- Did the deployment coincide with the metric anomaly?
- If yes, the deployment is the primary suspect

### Step 5 — Identify Root Cause Category

| Symptom | Likely Root Cause |
|---|---|
| High error rate + exception in logs | Code bug or bad config in latest deploy |
| High duration + no errors | Slow downstream (DB, external API) |
| High duration + timeout logs | Lambda timeout too low or infinite loop |
| Throttling | Concurrency limit too low for traffic |
| All metrics clean but alarm firing | Alarm threshold misconfigured |

## Mitigation Templates

### If deployment caused the issue
```
Recommended action: Rollback to previous Lambda version
Command: aws lambda update-alias --function-name agentic-sre-demo-app \
  --name live --function-version <previous_version>
Validation: Monitor error rate for 5 minutes post-rollback
```

### If timeout is the issue
```
Recommended action: Increase Lambda timeout
Current: 30 seconds
Suggested: 60 seconds (investigate root cause in parallel)
IaC change: Update timeout in CDK stack DemoAppStack
```

### If throttling is the issue
```
Recommended action: Increase reserved concurrency
Current: unreserved (account limit)
Suggested: Set reserved concurrency to 50
Command: aws lambda put-function-concurrency \
  --function-name agentic-sre-demo-app --reserved-concurrent-executions 50
```

## Escalation Criteria
Escalate to on-call engineer if:
- Root cause cannot be determined after completing all 5 steps
- Error rate > 50% sustained for more than 10 minutes
- Multiple services affected simultaneously

## Post-Investigation
After resolving the incident:
1. Generate a mitigation plan with Prepare / Pre-Validate / Apply / Post-Validate phases
2. Post the root cause summary to #sre-incidents Slack channel
3. Create an agent-ready spec if code changes are needed (hand off to Kiro)
