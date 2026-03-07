# WebSocket Infrastructure Setup

This document describes the WebSocket infrastructure additions to the Healthcare Triage Chatbot.

## New Resources

### DynamoDB Table
- **Name**: `healthcare-triage-chatbot-conversations`
- **Purpose**: Store conversation sessions with automatic TTL cleanup
- **Billing**: On-demand (pay-per-request)
- **TTL**: 24 hours after last update

### WebSocket API Gateway
- **Protocol**: WebSocket
- **Routes**:
  - `$connect`: Initialize or retrieve session
  - `$disconnect`: Update session timestamp
  - `sendMessage`: Process user messages

### Lambda Functions
1. **ConnectLambda**: Handle WebSocket connections
2. **DisconnectLambda**: Handle WebSocket disconnections
3. **MessageLambda**: Process messages and generate responses

### IAM Roles
- **WebSocketLambdaRole**: Permissions for DynamoDB, Comprehend Medical, WebSocket API, and SSM Parameter Store

### CloudWatch Resources
- Log groups for each Lambda function (7-day retention)
- Monitoring dashboard with Lambda and DynamoDB metrics

## Deployment

To deploy the updated infrastructure:

```bash
aws cloudformation deploy \
  --template-file cloudformation-template.yaml \
  --stack-name healthcare-triage-chatbot \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ProjectName=healthcare-triage-chatbot
```

## Configuration

Before deploying, store the Groq API key in AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter \
  --name "/healthcare-triage-chatbot/groq-api-key" \
  --value "your-groq-api-key" \
  --type "SecureString"
```

## Outputs

After deployment, the stack will output:
- `WebSocketEndpoint`: WebSocket API URL for frontend configuration
- `DynamoDBTableName`: Table name for session storage
- `CloudWatchDashboard`: URL to monitoring dashboard

## Cost Optimization

All resources use serverless, pay-per-use pricing:
- DynamoDB: On-demand billing
- Lambda: Pay per invocation
- API Gateway WebSocket: Pay per connection minute and message
- CloudWatch: 7-day log retention to minimize storage costs
