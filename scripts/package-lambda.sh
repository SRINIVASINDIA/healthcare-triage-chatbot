#!/bin/bash
# Package Lambda functions with dependencies for deployment
# This script creates deployment packages for all Lambda functions

set -e

echo "Starting Lambda packaging process..."

# Configuration
BACKEND_DIR="backend"
BUILD_DIR="build"
LAMBDA_ZIP="lambda.zip"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create deployment package
echo "Creating deployment package..."
cd "$BACKEND_DIR"

# Install dependencies to build directory
echo "Installing Python dependencies..."
pip install -r requirements.txt -t "../$BUILD_DIR" --upgrade

# Copy backend code to build directory
echo "Copying backend code..."
cp -r core/ "../$BUILD_DIR/"
cp -r websocket/ "../$BUILD_DIR/"
cp -r integrations/ "../$BUILD_DIR/"
cp -r utils/ "../$BUILD_DIR/"
cp lambda_function.py "../$BUILD_DIR/"

# Create ZIP file
echo "Creating ZIP archive..."
cd "../$BUILD_DIR"
zip -r "../$BACKEND_DIR/$LAMBDA_ZIP" . -q

echo "Lambda package created: $BACKEND_DIR/$LAMBDA_ZIP"

# Clean up build directory
cd ..
rm -rf "$BUILD_DIR"

echo "Packaging complete!"
echo ""
echo "Next steps:"
echo "1. Upload $BACKEND_DIR/$LAMBDA_ZIP to AWS Lambda"
echo "2. Or deploy using CloudFormation: aws cloudformation deploy ..."
