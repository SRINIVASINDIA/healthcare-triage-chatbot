# Phased Rollout Guide

This guide explains how to use the phased rollout mechanism for the WebSocket feature.

## Overview

The phased rollout allows you to gradually enable WebSocket functionality for a percentage of users while keeping others on the REST API. This helps:

1. Test new features with a small user base first
2. Monitor for issues before full rollout
3. Quickly rollback if problems occur
4. Reduce risk of widespread outages

## Configuration

Edit `frontend/config.js` to control the rollout:

```javascript
rollout: {
  enabled: true,      // Enable/disable phased rollout
  percentage: 10,     // Percentage of users (0-100)
}
```

### Rollout Stages

**Stage 1: Initial Testing (10%)**
```javascript
rollout: { enabled: true, percentage: 10 }
```
- Enable for 10% of users
- Monitor CloudWatch metrics closely
- Check for errors and performance issues

**Stage 2: Expanded Testing (25%)**
```javascript
rollout: { enabled: true, percentage: 25 }
```
- If Stage 1 is successful, expand to 25%
- Continue monitoring metrics
- Gather user feedback

**Stage 3: Majority Rollout (50%)**
```javascript
rollout: { enabled: true, percentage: 50 }
```
- Half of users on WebSocket
- Compare metrics between WebSocket and REST users
- Validate cost projections

**Stage 4: Near-Complete (75%)**
```javascript
rollout: { enabled: true, percentage: 75 }
```
- Most users on WebSocket
- Final validation before full rollout

**Stage 5: Full Rollout (100%)**
```javascript
rollout: { enabled: true, percentage: 100 }
// Or simply:
rollout: { enabled: false }
useWebSocket: true
```
- All users on WebSocket
- REST API remains available as fallback

## How It Works

The rollout uses **consistent hashing** to assign users to groups:

1. Each user gets a session ID (UUID)
2. Session ID is hashed to a number 0-99
3. If hash < percentage, user gets WebSocket
4. Same user always gets same assignment (consistent)

Example:
- User A: hash = 15 → Gets WebSocket if percentage ≥ 16
- User B: hash = 87 → Gets WebSocket if percentage ≥ 88

## Monitoring During Rollout

### Key Metrics to Watch

1. **Error Rates**
   - Lambda errors
   - WebSocket connection failures
   - Message delivery failures

2. **Performance**
   - Lambda duration
   - WebSocket latency
   - Message processing time

3. **Costs**
   - DynamoDB read/write units
   - Lambda invocations
   - API Gateway requests

### CloudWatch Dashboard

View the monitoring dashboard:
```bash
aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudWatchDashboard`].OutputValue' \
  --output text
```

### CloudWatch Alarms

Set up alarms for critical metrics:

```bash
# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name healthcare-triage-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# WebSocket connection failures
aws cloudwatch put-metric-alarm \
  --alarm-name healthcare-triage-websocket-failures \
  --alarm-description "Alert on WebSocket failures" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## Rollback Procedure

If issues are detected during rollout:

### Quick Rollback (Reduce Percentage)

Edit `frontend/config.js`:
```javascript
rollout: { enabled: true, percentage: 0 }  // Disable WebSocket for all users
```

Deploy updated config:
```bash
./scripts/deploy-frontend.sh
```

### Full Rollback (Disable Feature)

```javascript
rollout: { enabled: false }
useWebSocket: false  // Force REST API for everyone
```

### Emergency Rollback (CloudFormation)

If frontend changes aren't sufficient, update Lambda environment variables:

```bash
aws lambda update-function-configuration \
  --function-name healthcare-triage-websocket-message \
  --environment Variables={FEATURE_WEBSOCKET_ENABLED=false}
```

## Testing Rollout Locally

Test the rollout logic locally:

```javascript
// In browser console
const config = { rollout: { enabled: true, percentage: 10 } };

// Test with different session IDs
function testRollout(sessionId) {
  const shouldUse = config.shouldUseWebSocket(sessionId);
  console.log(`Session ${sessionId}: ${shouldUse ? 'WebSocket' : 'REST'}`);
}

// Test multiple users
for (let i = 0; i < 100; i++) {
  testRollout(`test-user-${i}`);
}
```

## Best Practices

1. **Start Small**: Begin with 10% or less
2. **Monitor Closely**: Watch metrics for 24-48 hours at each stage
3. **Gradual Increase**: Double percentage at each stage (10% → 25% → 50% → 100%)
4. **Wait Between Stages**: Allow time to detect issues
5. **Document Issues**: Keep notes on any problems encountered
6. **Have Rollback Plan**: Be ready to reduce percentage quickly
7. **Communicate**: Inform team of rollout schedule

## Rollout Checklist

- [ ] Deploy infrastructure (CloudFormation stack)
- [ ] Configure secrets (Groq API key)
- [ ] Deploy Lambda functions
- [ ] Deploy frontend with rollout at 10%
- [ ] Monitor for 24 hours
- [ ] Check CloudWatch metrics
- [ ] Review error logs
- [ ] Increase to 25% if successful
- [ ] Monitor for 24 hours
- [ ] Increase to 50%
- [ ] Monitor for 24 hours
- [ ] Increase to 75%
- [ ] Monitor for 24 hours
- [ ] Increase to 100%
- [ ] Monitor for 1 week
- [ ] Disable rollout mechanism (set enabled: false)

## Troubleshooting

### Users Not Getting WebSocket

1. Check rollout percentage in config.js
2. Verify frontend deployment (check S3 file timestamp)
3. Clear browser cache
4. Check browser console for errors

### Inconsistent Behavior

1. Verify session ID is being stored correctly
2. Check sessionStorage in browser DevTools
3. Ensure hash function is working (test in console)

### High Error Rates

1. Check CloudWatch logs for specific errors
2. Verify Lambda function configuration
3. Check DynamoDB table status
4. Verify Groq API key is valid

## Support

For issues during rollout:
1. Check CloudWatch logs
2. Review monitoring dashboard
3. Consult DEPLOYMENT_GUIDE.md
4. Rollback if necessary
