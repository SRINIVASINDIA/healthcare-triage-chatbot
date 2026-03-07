# Package Lambda functions with dependencies for deployment
# PowerShell script for Windows users

Write-Host "Starting Lambda packaging process..." -ForegroundColor Green

# Configuration
$BackendDir = "backend"
$BuildDir = "build"
$LambdaZip = "lambda.zip"

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
New-Item -ItemType Directory -Path $BuildDir | Out-Null

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Push-Location $BackendDir

# Install dependencies to build directory
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -t "..\$BuildDir" --upgrade

# Copy backend code to build directory
Write-Host "Copying backend code..." -ForegroundColor Yellow
Copy-Item -Recurse -Path "core" -Destination "..\$BuildDir\"
Copy-Item -Recurse -Path "websocket" -Destination "..\$BuildDir\"
Copy-Item -Recurse -Path "integrations" -Destination "..\$BuildDir\"
Copy-Item -Recurse -Path "utils" -Destination "..\$BuildDir\"
Copy-Item -Path "lambda_function.py" -Destination "..\$BuildDir\"

# Create ZIP file
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
Push-Location "..\$BuildDir"
Compress-Archive -Path * -DestinationPath "..\$BackendDir\$LambdaZip" -Force
Pop-Location

Write-Host "Lambda package created: $BackendDir\$LambdaZip" -ForegroundColor Green

# Clean up build directory
Pop-Location
Remove-Item -Recurse -Force $BuildDir

Write-Host "Packaging complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Upload $BackendDir\$LambdaZip to AWS Lambda"
Write-Host "2. Or deploy using CloudFormation: aws cloudformation deploy ..."
