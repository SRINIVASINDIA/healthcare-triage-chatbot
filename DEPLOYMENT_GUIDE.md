# Deployment Guide - ChatGPT-Like Enhancements

This guide covers deploying the enhanced Healthcare Triage Chatbot with WebSocket support and conversation management.

## Prerequisites

1. AWS CLI installed and configured
2. Python 3.11 or later
3. AWS account with appropriate permissions
4. Groq API key (for AI model access)

## Step 1: Package Lambda Functions

### Linux/Mac:
```bash
chmod +x scripts/package-lambda.sh
./scripts/package-lambda.sh
```

### Windows (PowerShell):
```powershell
.\scripts\package-lambda.ps1
```

This creates `backend/lambda.zip` with all dependencies.

## Step 2: Store Groq API Key

Store your Groq API key in AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter \
  --name "/healthcare-triage/groq-api-key" \
  --value "YOUR_GROQ_API_KEY" \
  --type "SecureString" \
  --description "Groq API key for healthcare triage chatbot"
```

## Step 3: Deploy CloudFormation Stack

Deploy the infrastructure using CloudFormation:

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-template.yaml \
  --stack-name healthcare-triage-chatbot \
  --parameter-overrides \
    ProjectName=healthcare-triage \
    GroqApiKey=/healthcare-triage/groq-api-key \
  --capabilities CAPABILITY_IAM
```

## Step 4: Upload Lambda Code

After the stack is created, upload the Lambda deployment package:

```bash
# Get the Lambda function name from stack outputs
LAMBDA_FUNCTION=$(aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
  --output text | cut -d':' -f7)

# Update Lambda function code
aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION \
  --zip-file fileb://backend/lambda.zip
```

Update WebSocket Lambda functions:

```bash
# Connect Lambda
aws lambda update-function-code \
  --function-name healthcare-triage-websocket-connect \
  --zip-file fileb://backend/lambda.zip

# Disconnect Lambda
aws lambda update-function-code \
  --function-name healthcare-triage-websocket-disconnect \
  --zip-file fileb://backend/lambda.zip

# Message Lambda
aws lambda update-function-code \
  --function-name healthcare-triage-websocket-message \
  --zip-file fileb://backend/lambda.zip
```

## Step 5: Deploy Frontend

Get the WebSocket endpoint from stack outputs:

```bash
WS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketEndpoint`].OutputValue' \
  --output text)

echo "WebSocket Endpoint: $WS_ENDPOINT"
```

Update `frontend/config.js` with the WebSocket endpoint:

```javascript
const config = {
  websocketUrl: 'wss://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/prod',
  restApiUrl: 'https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/prod/triage',
  useWebSocket: true  // Set to false to use REST API only
};
```

Upload frontend to S3:

```bash
# Get S3 bucket name
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
  --output text | cut -d'/' -f3 | cut -d'.' -f1)

# Upload frontend files
aws s3 sync frontend/ s3://$S3_BUCKET/ \
  --exclude "node_modules/*" \
  --exclude "*.test.js" \
  --exclude "package*.json"
```

## Step 6: Verify Deployment

### Test REST API:
```bash
REST_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

curl -X POST $REST_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "I have a headache"}'
```

### Test WebSocket API:
Use a WebSocket client tool (like `wscat`) or open the frontend in a browser:

```bash
npm install -g wscat
wscat -c $WS_ENDPOINT
```

Then send a message:
```json
{"action": "sendMessage", "sessionId": "test-session-id", "message": "I have a headache"}
```

## Step 7: Monitor Deployment

View CloudWatch dashboard:

```bash
DASHBOARD_URL=$(aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudWatchDashboard`].OutputValue' \
  --output text)

echo "Dashboard URL: $DASHBOARD_URL"
```

Check Lambda logs:

```bash
aws logs tail /aws/lambda/healthcare-triage-websocket-message --follow
```

## Rollback

If you need to rollback the deployment:

```bash
aws cloudformation delete-stack --stack-name healthcare-triage-chatbot
```

## Cost Optimization

The deployment uses serverless, pay-per-use services:

- **DynamoDB**: On-demand billing, automatic TTL cleanup
- **Lambda**: Pay per invocation
- **API Gateway**: Pay per message
- **S3**: Pay per storage and requests
- **CloudWatch**: 7-day log retention

Estimated costs for 1000 conversations/month: ~$5-10 USD

## Troubleshooting

### Lambda Function Errors
Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/healthcare-triage-websocket-message --follow
```

### WebSocket Connection Issues
1. Verify WebSocket API endpoint is correct
2. Check CORS settings in API Gateway
3. Verify Lambda function has correct permissions

### DynamoDB Issues
1. Check table exists: `aws dynamodb describe-table --table-name healthcare-triage-conversations`
2. Verify TTL is enabled
3. Check IAM permissions for Lambda

### Frontend Not Loading
1. Verify S3 bucket has static website hosting enabled
2. Check bucket policy allows public read access
3. Verify config.js has correct endpoints

## Security Considerations

1. **API Key Protection**: Groq API key stored in Parameter Store (encrypted)
2. **CORS**: Configure allowed origins in API Gateway
3. **Rate Limiting**: API Gateway throttling enabled
4. **Input Validation**: All user inputs validated and sanitized
5. **PII Redaction**: Logging automatically redacts sensitive data

## Next Steps

1. Set up CloudWatch alarms for errors and throttling
2. Configure SNS notifications for critical alerts
3. Implement phased rollout (see task 16)
4. Run integration tests (see task 14)
5. Monitor costs and optimize as needed
