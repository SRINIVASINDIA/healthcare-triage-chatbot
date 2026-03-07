#!/bin/bash
# Set up CloudWatch alarms for monitoring rollout

set -e

echo "Setting up CloudWatch alarms..."

# Configuration
PROJECT_NAME="${PROJECT_NAME:-healthcare-triage}"
REGION="${AWS_REGION:-us-east-1}"
SNS_EMAIL="${SNS_EMAIL:-}"

# Create SNS topic for alerts if email provided
if [ -n "$SNS_EMAIL" ]; then
    echo "Creating SNS topic for alerts..."
    SNS_TOPIC_ARN=$(aws sns create-topic \
        --name "${PROJECT_NAME}-alerts" \
        --region "$REGION" \
        --query 'TopicArn' \
        --output text)
    
    echo "SNS Topic ARN: $SNS_TOPIC_ARN"
    
    # Subscribe email to topic
    echo "Subscribing $SNS_EMAIL to alerts..."
    aws sns subscribe \
        --topic-arn "$SNS_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$SNS_EMAIL" \
        --region "$REGION"
    
    echo "✓ Check your email to confirm subscription"
    ALARM_ACTIONS="--alarm-actions $SNS_TOPIC_ARN"
else
    echo "No SNS_EMAIL provided, alarms will be created without notifications"
    ALARM_ACTIONS=""
fi

# Lambda Error Rate Alarm
echo "Creating Lambda error rate alarm..."
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-lambda-errors" \
    --alarm-description "Alert when Lambda error rate exceeds threshold" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --treat-missing-data notBreaching \
    --region "$REGION" \
    $ALARM_ACTIONS

echo "✓ Lambda error alarm created"

# Lambda Throttle Alarm
echo "Creating Lambda throttle alarm..."
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-lambda-throttles" \
    --alarm-description "Alert when Lambda functions are throttled" \
    --metric-name Throttles \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --treat-missing-data notBreaching \
    --region "$REGION" \
    $ALARM_ACTIONS

echo "✓ Lambda throttle alarm created"

# Lambda Duration Alarm (P99)
echo "Creating Lambda duration alarm..."
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-lambda-duration" \
    --alarm-description "Alert when Lambda duration is high" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --threshold 5000 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --treat-missing-data notBreaching \
    --region "$REGION" \
    $ALARM_ACTIONS

echo "✓ Lambda duration alarm created"

# API Gateway 5XX Errors
echo "Creating API Gateway error alarm..."
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-api-5xx-errors" \
    --alarm-description "Alert on API Gateway 5XX errors" \
    --metric-name 5XXError \
    --namespace AWS/ApiGateway \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --treat-missing-data notBreaching \
    --region "$REGION" \
    $ALARM_ACTIONS

echo "✓ API Gateway error alarm created"

# DynamoDB Throttle Alarm
echo "Creating DynamoDB throttle alarm..."
aws cloudwatch put-metric-alarm \
    --alarm-name "${PROJECT_NAME}-dynamodb-throttles" \
    --alarm-description "Alert when DynamoDB requests are throttled" \
    --metric-name UserErrors \
    --namespace AWS/DynamoDB \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --treat-missing-data notBreaching \
    --region "$REGION" \
    $ALARM_ACTIONS

echo "✓ DynamoDB throttle alarm created"

# Display summary
echo ""
echo "CloudWatch Alarms Summary:"
echo "=========================="
echo "Project: $PROJECT_NAME"
echo "Region: $REGION"
if [ -n "$SNS_EMAIL" ]; then
    echo "Notifications: $SNS_EMAIL"
    echo "SNS Topic: $SNS_TOPIC_ARN"
else
    echo "Notifications: None (set SNS_EMAIL to enable)"
fi
echo ""
echo "Alarms created:"
echo "- Lambda errors (threshold: 10 in 5 minutes)"
echo "- Lambda throttles (threshold: 5 in 5 minutes)"
echo "- Lambda duration (threshold: 5000ms average)"
echo "- API Gateway 5XX errors (threshold: 5 in 5 minutes)"
echo "- DynamoDB throttles (threshold: 10 in 5 minutes)"
echo ""
echo "View alarms in CloudWatch console:"
echo "https://console.aws.amazon.com/cloudwatch/home?region=${REGION}#alarmsV2:"
