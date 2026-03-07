# Validation Checklist - ChatGPT-Like Enhancements

This checklist ensures all components are working correctly before full deployment.

## Pre-Deployment Validation

### Infrastructure
- [ ] CloudFormation stack deployed successfully
- [ ] DynamoDB table created with TTL enabled
- [ ] WebSocket API Gateway created
- [ ] Lambda functions deployed (connect, disconnect, message, triage)
- [ ] S3 bucket configured for static website hosting
- [ ] IAM roles and policies configured correctly
- [ ] CloudWatch log groups created
- [ ] CloudWatch dashboard accessible

### Configuration
- [ ] Groq API key stored in Parameter Store
- [ ] Lambda environment variables set correctly
- [ ] Frontend config.js updated with correct endpoints
- [ ] CloudWatch log retention set to 7 days
- [ ] Rollout percentage configured (start at 10%)

## Functional Testing

### REST API (Backward Compatibility)
- [ ] POST /triage endpoint responds successfully
- [ ] Emergency keywords detected correctly
- [ ] Non-emergency symptoms processed by AI
- [ ] Response format matches original system
- [ ] Error handling works (invalid input, missing fields)
- [ ] CORS headers present in responses

**Test Command:**
```bash
curl -X POST $REST_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "I have a headache"}'
```

Expected response:
```json
{
  "severity": "LOW|MODERATE|SEVERE",
  "advice": "..."
}
```

### WebSocket Connection
- [ ] WebSocket connection establishes successfully
- [ ] Session ID generated and returned
- [ ] Existing session restored on reconnection
- [ ] Connection state changes logged
- [ ] Disconnection handled gracefully

**Test with wscat:**
```bash
npm install -g wscat
wscat -c $WS_ENDPOINT
```

### Message Processing
- [ ] User messages received and processed
- [ ] Medical entities extracted (if NER enabled)
- [ ] Emergency keywords detected across messages
- [ ] Context maintained across conversation
- [ ] Follow-up questions generated appropriately
- [ ] AI responses returned successfully
- [ ] Message history stored in DynamoDB
- [ ] TTL updated on each message

**Test Message:**
```json
{"action": "sendMessage", "sessionId": "test-123", "message": "I have chest pain"}
```

Expected response:
```json
{
  "type": "message",
  "timestamp": "2024-01-15T10:30:00Z",
  "content": "Call 911 immediately...",
  "severity": "SEVERE",
  "conversationState": "INITIAL"
}
```

### Session Management
- [ ] New sessions created with unique IDs
- [ ] Sessions retrieved by ID
- [ ] Session TTL set to 24 hours
- [ ] Message history limited to 50 messages
- [ ] Aggregated entities tracked correctly
- [ ] Follow-up count incremented
- [ ] Emergency flag set when detected

### Emergency Detection
- [ ] "chest pain" triggers SEVERE
- [ ] "stroke" triggers SEVERE
- [ ] "seizure" triggers SEVERE
- [ ] "difficulty breathing" triggers SEVERE
- [ ] Cross-message patterns detected (e.g., "chest" + "pain")
- [ ] Emergency logged with full context

### Context Analysis
- [ ] Recent messages retrieved (last 10)
- [ ] Aggregated entities collected
- [ ] References resolved ("it", "the pain")
- [ ] Conversation state tracked

### Frontend
- [ ] Page loads without errors
- [ ] WebSocket connection indicator shows status
- [ ] Messages display in chat interface
- [ ] User messages right-aligned (blue)
- [ ] Bot messages left-aligned (gray)
- [ ] Typing indicator appears while waiting
- [ ] Auto-scroll to newest message
- [ ] Session persists on page refresh
- [ ] Reconnection works after disconnect
- [ ] Fallback to REST API on persistent failure

## Performance Testing

### Response Times
- [ ] REST API responds in < 2 seconds
- [ ] WebSocket connection in < 1 second
- [ ] Message processing in < 3 seconds
- [ ] AI response generation in < 5 seconds

### Concurrent Users
- [ ] 10 concurrent users handled
- [ ] 50 concurrent users handled
- [ ] 100 concurrent users handled
- [ ] No throttling errors
- [ ] No timeout errors

### Load Testing
```bash
# Use Apache Bench or similar tool
ab -n 100 -c 10 -p test-payload.json -T application/json $REST_ENDPOINT
```

## Error Handling

### DynamoDB Unavailable
- [ ] System operates in stateless mode
- [ ] Warning logged to CloudWatch
- [ ] User receives response (no history)
- [ ] No crashes or 500 errors

### Groq API Unavailable
- [ ] Fallback response returned
- [ ] Error logged to CloudWatch
- [ ] User advised to seek in-person care
- [ ] No crashes or 500 errors

### WebSocket Connection Failure
- [ ] Frontend attempts reconnection
- [ ] Exponential backoff applied
- [ ] Falls back to REST API after max attempts
- [ ] User notified of connection issues

### Invalid Input
- [ ] Empty message rejected
- [ ] Message > 2000 chars rejected
- [ ] Invalid JSON rejected
- [ ] Missing fields rejected
- [ ] User-friendly error messages

## Security Testing

### Input Validation
- [ ] SQL injection attempts blocked
- [ ] XSS attempts sanitized
- [ ] Command injection blocked
- [ ] Path traversal blocked

### PII Protection
- [ ] Email addresses redacted in logs
- [ ] Phone numbers redacted in logs
- [ ] SSN patterns redacted in logs
- [ ] API keys not exposed in errors

### Rate Limiting
- [ ] API Gateway throttling configured
- [ ] Lambda concurrency limits set
- [ ] DynamoDB on-demand scaling works

## Monitoring Validation

### CloudWatch Logs
- [ ] Lambda invocations logged
- [ ] Connection events logged
- [ ] Message processing logged
- [ ] Errors logged with context
- [ ] Emergency detections logged

### CloudWatch Metrics
- [ ] Lambda invocations tracked
- [ ] Lambda errors tracked
- [ ] Lambda duration tracked
- [ ] DynamoDB capacity tracked
- [ ] API Gateway requests tracked

### CloudWatch Dashboard
- [ ] Dashboard accessible
- [ ] All widgets display data
- [ ] Metrics update in real-time
- [ ] Emergency detection widget works
- [ ] Processing time widget works

### CloudWatch Alarms
- [ ] Lambda error alarm configured
- [ ] Lambda throttle alarm configured
- [ ] API Gateway error alarm configured
- [ ] DynamoDB throttle alarm configured
- [ ] SNS notifications working (if configured)

## Cost Validation

### Estimated Costs (1000 conversations/month)
- [ ] DynamoDB: < $2/month
- [ ] Lambda: < $3/month
- [ ] API Gateway: < $2/month
- [ ] S3: < $1/month
- [ ] CloudWatch: < $2/month
- [ ] Total: < $10/month

### Cost Monitoring
- [ ] AWS Cost Explorer shows expected costs
- [ ] No unexpected charges
- [ ] DynamoDB on-demand billing active
- [ ] Lambda memory optimized
- [ ] CloudWatch log retention set to 7 days

## Browser Compatibility

### Desktop Browsers
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Mobile Browsers
- [ ] Chrome Mobile (Android)
- [ ] Safari Mobile (iOS)
- [ ] Firefox Mobile

### WebSocket Support
- [ ] All browsers support WebSocket
- [ ] Fallback to REST works if needed

## Rollout Validation

### Phased Rollout
- [ ] Rollout percentage configurable
- [ ] User assignment consistent (same user = same result)
- [ ] Hash function distributes evenly
- [ ] 10% rollout affects ~10% of users
- [ ] Rollback mechanism works

### Monitoring During Rollout
- [ ] Error rates monitored
- [ ] Performance metrics tracked
- [ ] Cost metrics reviewed
- [ ] User feedback collected

## Documentation

- [ ] DEPLOYMENT_GUIDE.md complete
- [ ] ROLLOUT_GUIDE.md complete
- [ ] VALIDATION_CHECKLIST.md complete
- [ ] README.md updated
- [ ] API documentation updated
- [ ] Architecture diagrams current

## Final Checks

- [ ] All tests passing
- [ ] No critical errors in logs
- [ ] Performance meets requirements
- [ ] Security validated
- [ ] Costs within budget
- [ ] Team trained on deployment
- [ ] Rollback plan documented
- [ ] Support contacts identified

## Sign-Off

- [ ] Development team approval
- [ ] QA team approval
- [ ] Security team approval
- [ ] Product owner approval
- [ ] Operations team approval

## Post-Deployment

- [ ] Monitor for 24 hours at 10% rollout
- [ ] Review CloudWatch metrics
- [ ] Check error logs
- [ ] Verify costs
- [ ] Collect user feedback
- [ ] Increase rollout percentage if successful

---

**Validation Date:** _____________

**Validated By:** _____________

**Issues Found:** _____________

**Resolution:** _____________

**Approved for Deployment:** [ ] Yes [ ] No
