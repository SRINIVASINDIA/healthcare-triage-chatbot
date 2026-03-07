#!/bin/bash
# Deploy frontend to S3 bucket

set -e

echo "Deploying frontend to S3..."

# Configuration
PROJECT_NAME="${PROJECT_NAME:-healthcare-triage}"
STACK_NAME="${STACK_NAME:-healthcare-triage-chatbot}"
REGION="${AWS_REGION:-us-east-1}"

# Get S3 bucket name from CloudFormation stack
echo "Getting S3 bucket name from CloudFormation..."
WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
    --output text \
    --region "$REGION")

if [ -z "$WEBSITE_URL" ]; then
    echo "Error: Could not get website URL from CloudFormation stack"
    echo "Make sure the stack '$STACK_NAME' exists and has been deployed"
    exit 1
fi

# Extract bucket name from URL
S3_BUCKET=$(echo "$WEBSITE_URL" | cut -d'/' -f3 | cut -d'.' -f1)
echo "S3 Bucket: $S3_BUCKET"

# Get API endpoints from CloudFormation
echo "Getting API endpoints..."
REST_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text \
    --region "$REGION")

WS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketEndpoint`].OutputValue' \
    --output text \
    --region "$REGION")

echo "REST API Endpoint: $REST_ENDPOINT"
echo "WebSocket Endpoint: $WS_ENDPOINT"

# Update config.js with endpoints
echo "Updating frontend configuration..."
cat > frontend/config.js << EOF
// Auto-generated configuration
const config = {
  websocketUrl: '$WS_ENDPOINT',
  restApiUrl: '$REST_ENDPOINT',
  useWebSocket: true,  // Set to false to use REST API only
  reconnectDelay: 1000,  // Initial reconnect delay in ms
  maxReconnectDelay: 30000,  // Maximum reconnect delay in ms
  maxReconnectAttempts: 10
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = config;
}
EOF

echo "✓ Configuration updated"

# Upload frontend files to S3
echo "Uploading frontend files to S3..."
aws s3 sync frontend/ "s3://$S3_BUCKET/" \
    --exclude "node_modules/*" \
    --exclude "*.test.js" \
    --exclude "package*.json" \
    --exclude "jest.config.js" \
    --region "$REGION" \
    --delete

echo "✓ Frontend files uploaded"

# Set correct content types
echo "Setting content types..."
aws s3 cp "s3://$S3_BUCKET/index.html" "s3://$S3_BUCKET/index.html" \
    --content-type "text/html" \
    --metadata-directive REPLACE \
    --region "$REGION"

aws s3 cp "s3://$S3_BUCKET/styles.css" "s3://$S3_BUCKET/styles.css" \
    --content-type "text/css" \
    --metadata-directive REPLACE \
    --region "$REGION"

for js_file in app.js websocket-client.js chat-ui.js config.js; do
    aws s3 cp "s3://$S3_BUCKET/$js_file" "s3://$S3_BUCKET/$js_file" \
        --content-type "application/javascript" \
        --metadata-directive REPLACE \
        --region "$REGION"
done

echo "✓ Content types set"

# Display deployment summary
echo ""
echo "Deployment Summary:"
echo "==================="
echo "Website URL: $WEBSITE_URL"
echo "REST API: $REST_ENDPOINT"
echo "WebSocket API: $WS_ENDPOINT"
echo ""
echo "Frontend deployment complete!"
echo "Open $WEBSITE_URL in your browser to test"
