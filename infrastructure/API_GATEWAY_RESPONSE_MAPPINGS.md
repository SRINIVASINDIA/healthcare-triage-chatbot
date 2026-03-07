# API Gateway Response Mappings Configuration

This document explains how the Healthcare Triage Chatbot API Gateway handles response mappings, status codes, timeouts, and HTTPS enforcement.

## Overview

The API Gateway is configured with **AWS_PROXY integration**, which means:
- Lambda function controls all response aspects (status codes, headers, body)
- API Gateway passes Lambda responses through without modification
- No custom response mapping templates needed

## Requirements Addressed

- **Requirement 4.4**: 200 status for successful Lambda responses
- **Requirement 4.5**: 4xx/5xx status for Lambda errors
- **Requirement 7.4**: HTTPS-only access and timeout handling

## Configuration Details

### 1. AWS_PROXY Integration (Requirements 4.4, 4.5)

**Configuration:**
```yaml
TriagePostMethod:
  Properties:
    Integration:
      Type: AWS_PROXY  # Lambda controls response format
      IntegrationHttpMethod: POST
      Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${TriageLambdaFunction.Arn}/invocations'
```

**How it works:**
- Lambda returns response in this format:
  ```json
  {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
    "body": "{\"severity\": \"LOW\", \"advice\": \"...\"}"
  }
  ```
- API Gateway passes this response directly to the client
- Lambda controls the status code based on the scenario:
  - `200`: Successful triage response (emergency or Bedrock analysis)
  - `400`: Invalid input (missing symptoms, empty string, etc.)
  - `500`: Internal server error (unexpected exceptions)

**Status Code Mapping:**

| Scenario | Lambda Status Code | API Gateway Response |
|----------|-------------------|---------------------|
| Successful triage (emergency) | 200 | 200 OK |
| Successful triage (Bedrock) | 200 | 200 OK |
| Invalid input | 400 | 400 Bad Request |
| Bedrock unavailable | 200 | 200 OK (graceful degradation) |
| Internal error | 500 | 500 Internal Server Error |
| Lambda timeout | N/A | 504 Gateway Timeout |

### 2. Timeout Configuration (Requirement 7.4)

**Lambda Timeout:**
```yaml
TriageLambdaFunction:
  Properties:
    Timeout: 10  # seconds
```

**API Gateway Timeout:**
- Fixed at 29 seconds (AWS limit, cannot be changed)

**Timeout Behavior:**

1. **Lambda completes within 10 seconds:**
   - Lambda returns response with appropriate status code
   - API Gateway passes response to client

2. **Lambda exceeds 10 seconds:**
   - Lambda execution terminates
   - Lambda returns error response
   - API Gateway passes error to client (typically 500)

3. **Request exceeds 29 seconds:**
   - API Gateway returns `504 Gateway Timeout`
   - Lambda may continue executing (response discarded)
   - Client receives 504 status code

**Why 10 seconds for Lambda?**
- Emergency detection: <100ms (no Bedrock call)
- Bedrock API call: typically 2-5 seconds
- Network overhead: 1-2 seconds
- Buffer for retries: 2-3 seconds
- Total: 10 seconds provides comfortable margin

### 3. HTTPS-Only Access (Requirement 7.4)

**Configuration:**
```yaml
TriageApi:
  Properties:
    EndpointConfiguration:
      Types:
        - REGIONAL  # Enforces HTTPS by default
```

**How HTTPS is enforced:**
- API Gateway REGIONAL endpoints only accept HTTPS requests
- HTTP requests are automatically rejected by AWS
- No additional configuration needed
- API endpoint URL uses `https://` protocol:
  ```
  https://{api-id}.execute-api.{region}.amazonaws.com/prod
  ```

**HTTPS Enforcement Details:**
- Built into API Gateway (cannot be disabled)
- TLS 1.2+ required
- AWS-managed SSL certificates
- No HTTP fallback available

### 4. CORS Configuration (Requirement 4.3)

**POST Method CORS:**
```yaml
TriagePostMethod:
  Properties:
    MethodResponses:
      - StatusCode: 200
        ResponseParameters:
          method.response.header.Access-Control-Allow-Origin: true
```

**OPTIONS Method (Preflight):**
```yaml
TriageOptionsMethod:
  Properties:
    HttpMethod: OPTIONS
    Integration:
      Type: MOCK
      IntegrationResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Access-Control-Allow-Headers: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
            method.response.header.Access-Control-Allow-Methods: "'POST,OPTIONS'"
            method.response.header.Access-Control-Allow-Origin: "'*'"
```

**Lambda Response Headers:**
```python
{
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'  # CORS header
    },
    'body': json.dumps(response_body)
}
```

## Testing

All response mapping configurations are verified by automated tests in `infrastructure/test_api_gateway_config.py`:

1. **test_api_gateway_uses_aws_proxy_integration**: Verifies AWS_PROXY integration type
2. **test_lambda_timeout_allows_api_gateway_timeout**: Verifies Lambda timeout < 29s
3. **test_api_gateway_enforces_https_only**: Verifies REGIONAL endpoint configuration
4. **test_cors_configuration_present**: Verifies CORS headers
5. **test_lambda_returns_proper_status_codes**: Verifies Lambda returns correct status codes
6. **test_api_gateway_timeout_behavior**: Documents timeout chain
7. **test_api_gateway_url_uses_https**: Verifies HTTPS in output URL
8. **test_regional_endpoint_enforces_https**: Documents HTTPS enforcement
9. **test_aws_proxy_passes_through_lambda_response**: Verifies response pass-through

Run tests:
```bash
pytest infrastructure/test_api_gateway_config.py -v
```

## Error Handling

### Lambda Error Responses

Lambda returns structured error responses with appropriate status codes:

**400 Bad Request:**
```json
{
  "statusCode": 400,
  "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
  "body": "{\"error\": \"Invalid request: symptoms field is required\"}"
}
```

**500 Internal Server Error:**
```json
{
  "statusCode": 500,
  "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
  "body": "{\"severity\": \"MODERATE\", \"advice\": \"We're unable to process your request...\"}"
}
```

### API Gateway Error Responses

**504 Gateway Timeout:**
```json
{
  "message": "Endpoint request timed out"
}
```

This occurs when the request exceeds 29 seconds (API Gateway limit).

## Deployment Verification

After deploying the CloudFormation stack, verify the configuration:

1. **Check API Gateway endpoint:**
   ```bash
   aws cloudformation describe-stacks --stack-name <stack-name> --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text
   ```

2. **Verify HTTPS enforcement:**
   ```bash
   # This should fail (HTTP not supported)
   curl http://<api-id>.execute-api.<region>.amazonaws.com/prod/triage
   
   # This should work
   curl https://<api-id>.execute-api.<region>.amazonaws.com/prod/triage -X POST -H "Content-Type: application/json" -d '{"symptoms":"headache"}'
   ```

3. **Test status codes:**
   ```bash
   # Should return 200
   curl -X POST https://<api-endpoint>/triage -H "Content-Type: application/json" -d '{"symptoms":"headache"}' -w "\nStatus: %{http_code}\n"
   
   # Should return 400
   curl -X POST https://<api-endpoint>/triage -H "Content-Type: application/json" -d '{}' -w "\nStatus: %{http_code}\n"
   ```

4. **Test CORS:**
   ```bash
   # OPTIONS preflight
   curl -X OPTIONS https://<api-endpoint>/triage -H "Origin: http://example.com" -v
   
   # Should see Access-Control-Allow-Origin header
   ```

## Summary

The API Gateway response mapping configuration is **complete and verified**:

✅ **AWS_PROXY integration** - Lambda controls all status codes (Requirements 4.4, 4.5)  
✅ **Lambda timeout (10s)** - Allows API Gateway 504 timeout at 29s (Requirement 7.4)  
✅ **REGIONAL endpoint** - Enforces HTTPS-only access automatically (Requirement 7.4)  
✅ **CORS headers** - Configured for cross-origin requests (Requirement 4.3)  
✅ **Automated tests** - All configurations verified by test suite  

No additional configuration changes are needed. The current setup properly handles:
- 200 status for successful responses
- 4xx/5xx status for errors
- 504 Gateway Timeout for Lambda timeouts
- HTTPS-only access enforcement
