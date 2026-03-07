# Infrastructure

This directory contains the AWS CloudFormation template for deploying the Healthcare Triage Chatbot.

## CloudFormation Template

The `cloudformation-template.yaml` file defines all required AWS resources:

### Resources Created

1. **S3 Bucket (WebsiteBucket)**
   - Configured for static website hosting
   - Public read access enabled
   - Serves frontend HTML, CSS, and JavaScript files

2. **S3 Bucket Policy (WebsiteBucketPolicy)**
   - Allows public GetObject access for website content
   - Required for static website hosting

3. **IAM Role (LambdaExecutionRole)**
   - Execution role for Lambda function
   - Permissions for:
     - Amazon Bedrock model invocation (amazon.nova-v2)
     - CloudWatch Logs (CreateLogGroup, CreateLogStream, PutLogEvents)
   - Includes AWSLambdaBasicExecutionRole managed policy

4. **Lambda Function (TriageLambdaFunction)**
   - Runtime: Python 3.11
   - Timeout: 10 seconds
   - Memory: 256 MB
   - Handler: index.lambda_handler
   - Environment variables for Bedrock model ID and region

5. **API Gateway REST API (TriageApi)**
   - Regional endpoint
   - POST /triage endpoint for symptom submissions
   - OPTIONS /triage endpoint for CORS preflight
   - Lambda proxy integration

6. **API Gateway Deployment (ApiDeployment)**
   - Deploys API to 'prod' stage
   - Creates invoke URL for frontend integration

7. **Lambda Permission (LambdaApiGatewayInvoke)**
   - Allows API Gateway to invoke Lambda function

### Outputs

The template provides the following outputs after deployment:

- **WebsiteURL**: S3 static website URL for accessing the frontend
- **ApiEndpoint**: API Gateway endpoint URL for the /triage endpoint
- **LambdaFunctionArn**: ARN of the Lambda function
- **S3BucketName**: Name of the S3 bucket (for uploading frontend files)

## Deployment

Deploy the CloudFormation stack using AWS CLI:

```bash
aws cloudformation create-stack \
  --stack-name healthcare-triage-chatbot \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

Check deployment status:

```bash
aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --region us-east-1
```

Get stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name healthcare-triage-chatbot \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

## Configuration

### Parameters

- **ProjectName**: Name prefix for all resources (default: healthcare-triage-chatbot)

### Environment Variables

The Lambda function uses these environment variables:

- `BEDROCK_MODEL_ID`: Amazon Bedrock model identifier (default: amazon.nova-v2)
- `AWS_REGION_NAME`: AWS region for Bedrock service

## Security Considerations

1. **S3 Bucket**: Public read access is required for static website hosting
2. **API Gateway**: HTTPS-only access enforced by default
3. **IAM Role**: Least privilege permissions for Bedrock and CloudWatch
4. **CORS**: Configured to allow requests from any origin (adjust for production)

## Updating the Stack

To update an existing stack:

```bash
aws cloudformation update-stack \
  --stack-name healthcare-triage-chatbot \
  --template-body file://infrastructure/cloudformation-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Deleting the Stack

To delete all resources:

```bash
aws cloudformation delete-stack \
  --stack-name healthcare-triage-chatbot \
  --region us-east-1
```

**Note**: Empty the S3 bucket before deleting the stack, or the deletion will fail.

## Requirements Validation

This CloudFormation template satisfies the following requirements:

- **6.1**: Defines S3 bucket, API Gateway, Lambda function, and IAM role
- **6.2**: IAM role has permissions to invoke Bedrock service
- **6.3**: S3 bucket configured with public read access
- **6.4**: API Gateway integrated with Lambda backend
- **6.5**: Outputs include website URL
- **6.6**: Single-command deployment (no manual configuration)
- **7.1**: IAM role grants Bedrock invocation permission for amazon.nova-v2
- **7.2**: IAM role grants CloudWatch Logs permissions
- **7.3**: S3 bucket allows public read access only
- **7.4**: API Gateway uses HTTPS by default
- **9.1**: S3 bucket configured for static website hosting
- **9.2**: Index document set to index.html
- **9.3**: Bucket policy allows GetObject access
- **9.4**: Website URL provided in outputs
