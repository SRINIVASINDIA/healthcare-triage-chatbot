#!/bin/bash
# Configure AWS secrets and parameters for the Healthcare Triage Chatbot

set -e

echo "Configuring AWS secrets and parameters..."

# Configuration
PROJECT_NAME="${PROJECT_NAME:-healthcare-triage}"
REGION="${AWS_REGION:-us-east-1}"

# Check if Groq API key is provided
if [ -z "$GROQ_API_KEY" ]; then
    echo "Error: GROQ_API_KEY environment variable not set"
    echo "Usage: GROQ_API_KEY=your_key ./configure-secrets.sh"
    exit 1
fi

# Store Groq API key in Parameter Store
echo "Storing Groq API key in Parameter Store..."
aws ssm put-parameter \
    --name "/${PROJECT_NAME}/groq-api-key" \
    --value "$GROQ_API_KEY" \
    --type "SecureString" \
    --description "Groq API key for ${PROJECT_NAME}" \
    --overwrite \
    --region "$REGION"

echo "✓ Groq API key stored successfully"

# Configure CloudWatch log retention
echo "Configuring CloudWatch log retention..."
for LOG_GROUP in \
    "/aws/lambda/${PROJECT_NAME}-websocket-connect" \
    "/aws/lambda/${PROJECT_NAME}-websocket-disconnect" \
    "/aws/lambda/${PROJECT_NAME}-websocket-message" \
    "/aws/lambda/${PROJECT_NAME}-triage"
do
    # Check if log group exists
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$REGION" | grep -q "$LOG_GROUP"; then
        echo "Setting retention for $LOG_GROUP to 7 days..."
        aws logs put-retention-policy \
            --log-group-name "$LOG_GROUP" \
            --retention-in-days 7 \
            --region "$REGION" || echo "Warning: Could not set retention for $LOG_GROUP"
    else
        echo "Log group $LOG_GROUP does not exist yet (will be created on first invocation)"
    fi
done

echo "✓ CloudWatch log retention configured"

# Display configuration summary
echo ""
echo "Configuration Summary:"
echo "====================="
echo "Project Name: $PROJECT_NAME"
echo "Region: $REGION"
echo "Groq API Key: Stored in /${PROJECT_NAME}/groq-api-key"
echo "Log Retention: 7 days"
echo ""
echo "Configuration complete!"
