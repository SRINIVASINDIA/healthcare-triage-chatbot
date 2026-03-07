# Configure AWS secrets and parameters for the Healthcare Triage Chatbot
# PowerShell script for Windows users

Write-Host "Configuring AWS secrets and parameters..." -ForegroundColor Green

# Configuration
$ProjectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "healthcare-triage" }
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }

# Check if Groq API key is provided
if (-not $env:GROQ_API_KEY) {
    Write-Host "Error: GROQ_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Usage: `$env:GROQ_API_KEY='your_key'; .\configure-secrets.ps1"
    exit 1
}

# Store Groq API key in Parameter Store
Write-Host "Storing Groq API key in Parameter Store..." -ForegroundColor Yellow
aws ssm put-parameter `
    --name "/$ProjectName/groq-api-key" `
    --value $env:GROQ_API_KEY `
    --type "SecureString" `
    --description "Groq API key for $ProjectName" `
    --overwrite `
    --region $Region

Write-Host "✓ Groq API key stored successfully" -ForegroundColor Green

# Configure CloudWatch log retention
Write-Host "Configuring CloudWatch log retention..." -ForegroundColor Yellow
$LogGroups = @(
    "/aws/lambda/$ProjectName-websocket-connect",
    "/aws/lambda/$ProjectName-websocket-disconnect",
    "/aws/lambda/$ProjectName-websocket-message",
    "/aws/lambda/$ProjectName-triage"
)

foreach ($LogGroup in $LogGroups) {
    # Check if log group exists
    $exists = aws logs describe-log-groups --log-group-name-prefix $LogGroup --region $Region | ConvertFrom-Json
    if ($exists.logGroups.Count -gt 0) {
        Write-Host "Setting retention for $LogGroup to 7 days..." -ForegroundColor Yellow
        aws logs put-retention-policy `
            --log-group-name $LogGroup `
            --retention-in-days 7 `
            --region $Region
    } else {
        Write-Host "Log group $LogGroup does not exist yet (will be created on first invocation)" -ForegroundColor Gray
    }
}

Write-Host "✓ CloudWatch log retention configured" -ForegroundColor Green

# Display configuration summary
Write-Host ""
Write-Host "Configuration Summary:" -ForegroundColor Cyan
Write-Host "====================="
Write-Host "Project Name: $ProjectName"
Write-Host "Region: $Region"
Write-Host "Groq API Key: Stored in /$ProjectName/groq-api-key"
Write-Host "Log Retention: 7 days"
Write-Host ""
Write-Host "Configuration complete!" -ForegroundColor Green
