# Deploy frontend to S3 bucket
# PowerShell script for Windows users

Write-Host "Deploying frontend to S3..." -ForegroundColor Green

# Configuration
$ProjectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "healthcare-triage" }
$StackName = if ($env:STACK_NAME) { $env:STACK_NAME } else { "healthcare-triage-chatbot" }
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }

# Get S3 bucket name from CloudFormation stack
Write-Host "Getting S3 bucket name from CloudFormation..." -ForegroundColor Yellow
$WebsiteUrl = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' `
    --output text `
    --region $Region

if (-not $WebsiteUrl) {
    Write-Host "Error: Could not get website URL from CloudFormation stack" -ForegroundColor Red
    Write-Host "Make sure the stack '$StackName' exists and has been deployed"
    exit 1
}

# Extract bucket name from URL
$S3Bucket = ($WebsiteUrl -split '/')[2] -split '\.' | Select-Object -First 1
Write-Host "S3 Bucket: $S3Bucket" -ForegroundColor Cyan

# Get API endpoints from CloudFormation
Write-Host "Getting API endpoints..." -ForegroundColor Yellow
$RestEndpoint = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' `
    --output text `
    --region $Region

$WsEndpoint = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketEndpoint`].OutputValue' `
    --output text `
    --region $Region

Write-Host "REST API Endpoint: $RestEndpoint" -ForegroundColor Cyan
Write-Host "WebSocket Endpoint: $WsEndpoint" -ForegroundColor Cyan

# Update config.js with endpoints
Write-Host "Updating frontend configuration..." -ForegroundColor Yellow
$ConfigContent = @"
// Auto-generated configuration
const config = {
  websocketUrl: '$WsEndpoint',
  restApiUrl: '$RestEndpoint',
  useWebSocket: true,  // Set to false to use REST API only
  reconnectDelay: 1000,  // Initial reconnect delay in ms
  maxReconnectDelay: 30000,  // Maximum reconnect delay in ms
  maxReconnectAttempts: 10
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = config;
}
"@

Set-Content -Path "frontend/config.js" -Value $ConfigContent
Write-Host "✓ Configuration updated" -ForegroundColor Green

# Upload frontend files to S3
Write-Host "Uploading frontend files to S3..." -ForegroundColor Yellow
aws s3 sync frontend/ "s3://$S3Bucket/" `
    --exclude "node_modules/*" `
    --exclude "*.test.js" `
    --exclude "package*.json" `
    --exclude "jest.config.js" `
    --region $Region `
    --delete

Write-Host "✓ Frontend files uploaded" -ForegroundColor Green

# Set correct content types
Write-Host "Setting content types..." -ForegroundColor Yellow
aws s3 cp "s3://$S3Bucket/index.html" "s3://$S3Bucket/index.html" `
    --content-type "text/html" `
    --metadata-directive REPLACE `
    --region $Region

aws s3 cp "s3://$S3Bucket/styles.css" "s3://$S3Bucket/styles.css" `
    --content-type "text/css" `
    --metadata-directive REPLACE `
    --region $Region

$JsFiles = @("app.js", "websocket-client.js", "chat-ui.js", "config.js")
foreach ($JsFile in $JsFiles) {
    aws s3 cp "s3://$S3Bucket/$JsFile" "s3://$S3Bucket/$JsFile" `
        --content-type "application/javascript" `
        --metadata-directive REPLACE `
        --region $Region
}

Write-Host "✓ Content types set" -ForegroundColor Green

# Display deployment summary
Write-Host ""
Write-Host "Deployment Summary:" -ForegroundColor Cyan
Write-Host "==================="
Write-Host "Website URL: $WebsiteUrl"
Write-Host "REST API: $RestEndpoint"
Write-Host "WebSocket API: $WsEndpoint"
Write-Host ""
Write-Host "Frontend deployment complete!" -ForegroundColor Green
Write-Host "Open $WebsiteUrl in your browser to test"
