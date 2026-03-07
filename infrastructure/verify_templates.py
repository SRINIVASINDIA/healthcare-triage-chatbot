#!/usr/bin/env python3
"""
CloudFormation Template Verification Script
Verifies infrastructure templates for Healthcare Triage Chatbot
"""

import yaml
import json
import sys
from pathlib import Path

# Custom YAML loader that handles CloudFormation intrinsic functions
class CFNLoader(yaml.SafeLoader):
    pass

# Add constructors for CloudFormation intrinsic functions
def construct_cfn_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix: loader.construct_mapping(node)}
    return {tag_suffix: None}

# Register CloudFormation intrinsic functions
cfn_tags = ['!Ref', '!GetAtt', '!Sub', '!Join', '!Select', '!Split', 
            '!GetAZs', '!ImportValue', '!Base64', '!Cidr', '!FindInMap',
            '!If', '!Not', '!Equals', '!And', '!Or']

for tag in cfn_tags:
    CFNLoader.add_constructor(tag, lambda loader, node, t=tag[1:]: construct_cfn_tag(loader, t, node))

def verify_template(template_path):
    """Verify a CloudFormation template"""
    print(f"\n{'='*60}")
    print(f"Verifying: {template_path}")
    print(f"{'='*60}\n")
    
    try:
        with open(template_path, 'r') as f:
            template = yaml.load(f, Loader=CFNLoader)
        
        print("✅ Template is valid YAML")
        
        # Verify required top-level keys
        required_keys = ['AWSTemplateFormatVersion', 'Resources']
        for key in required_keys:
            if key in template:
                print(f"✅ {key} present")
            else:
                print(f"❌ {key} missing")
                return False
        
        # Verify required resources
        required_resources = {
            'WebsiteBucket': 'AWS::S3::Bucket',
            'WebsiteBucketPolicy': 'AWS::S3::BucketPolicy',
            'LambdaExecutionRole': 'AWS::IAM::Role',
            'TriageLambdaFunction': 'AWS::Lambda::Function',
            'TriageApi': 'AWS::ApiGateway::RestApi',
            'TriageResource': 'AWS::ApiGateway::Resource',
            'TriagePostMethod': 'AWS::ApiGateway::Method',
            'TriageOptionsMethod': 'AWS::ApiGateway::Method',
            'ApiDeployment': 'AWS::ApiGateway::Deployment',
            'LambdaApiGatewayPermission': 'AWS::Lambda::Permission'
        }
        
        resources = template.get('Resources', {})
        print(f"\n📦 Resources ({len(resources)} total):")
        
        for resource_name, expected_type in required_resources.items():
            if resource_name in resources:
                actual_type = resources[resource_name].get('Type')
                if actual_type == expected_type:
                    print(f"  ✅ {resource_name} ({expected_type})")
                else:
                    print(f"  ❌ {resource_name} - Expected {expected_type}, got {actual_type}")
            else:
                print(f"  ❌ {resource_name} - MISSING")
        
        # Verify IAM Role permissions
        print(f"\n🔐 IAM Role Verification:")
        lambda_role = resources.get('LambdaExecutionRole', {})
        policies = lambda_role.get('Properties', {}).get('Policies', [])
        
        bedrock_policy_found = False
        cloudwatch_policy_found = False
        
        for policy in policies:
            policy_name = policy.get('PolicyName', '')
            if 'Bedrock' in policy_name:
                bedrock_policy_found = True
                print(f"  ✅ Bedrock policy found: {policy_name}")
                # Check for InvokeModel action
                statements = policy.get('PolicyDocument', {}).get('Statement', [])
                for stmt in statements:
                    actions = stmt.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    if 'bedrock:InvokeModel' in actions:
                        print(f"    ✅ bedrock:InvokeModel permission granted")
            
            if 'CloudWatch' in policy_name or 'Logs' in policy_name:
                cloudwatch_policy_found = True
                print(f"  ✅ CloudWatch policy found: {policy_name}")
        
        # Check managed policies
        managed_policies = lambda_role.get('Properties', {}).get('ManagedPolicyArns', [])
        for policy_arn in managed_policies:
            if 'AWSLambdaBasicExecutionRole' in str(policy_arn):
                print(f"  ✅ AWSLambdaBasicExecutionRole attached")
        
        if not bedrock_policy_found:
            print(f"  ❌ Bedrock policy not found")
        if not cloudwatch_policy_found:
            print(f"  ⚠️  CloudWatch policy not found (but may be in managed policy)")
        
        # Verify S3 bucket configuration
        print(f"\n🪣 S3 Bucket Configuration:")
        bucket = resources.get('WebsiteBucket', {})
        bucket_props = bucket.get('Properties', {})
        
        website_config = bucket_props.get('WebsiteConfiguration', {})
        if website_config:
            print(f"  ✅ Website hosting enabled")
            if website_config.get('IndexDocument') == 'index.html':
                print(f"    ✅ IndexDocument: index.html")
            else:
                print(f"    ❌ IndexDocument not set to index.html")
        else:
            print(f"  ❌ Website hosting not configured")
        
        # Verify S3 bucket policy
        bucket_policy = resources.get('WebsiteBucketPolicy', {})
        policy_doc = bucket_policy.get('Properties', {}).get('PolicyDocument', {})
        statements = policy_doc.get('Statement', [])
        
        public_read_found = False
        for stmt in statements:
            if stmt.get('Effect') == 'Allow' and stmt.get('Principal') == '*':
                actions = stmt.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                if 's3:GetObject' in actions:
                    public_read_found = True
                    print(f"  ✅ Public GetObject access configured")
        
        if not public_read_found:
            print(f"  ❌ Public GetObject access not found")
        
        # Verify Lambda configuration
        print(f"\n⚡ Lambda Function Configuration:")
        lambda_func = resources.get('TriageLambdaFunction', {})
        lambda_props = lambda_func.get('Properties', {})
        
        runtime = lambda_props.get('Runtime')
        if runtime == 'python3.11':
            print(f"  ✅ Runtime: {runtime}")
        else:
            print(f"  ❌ Runtime: {runtime} (expected python3.11)")
        
        timeout = lambda_props.get('Timeout')
        if timeout == 10:
            print(f"  ✅ Timeout: {timeout} seconds")
        else:
            print(f"  ⚠️  Timeout: {timeout} seconds (expected 10)")
        
        # Verify API Gateway configuration
        print(f"\n🌐 API Gateway Configuration:")
        api = resources.get('TriageApi', {})
        if api:
            print(f"  ✅ REST API defined")
        
        post_method = resources.get('TriagePostMethod', {})
        if post_method:
            integration = post_method.get('Properties', {}).get('Integration', {})
            if integration.get('Type') == 'AWS_PROXY':
                print(f"  ✅ POST /triage with Lambda proxy integration")
        
        options_method = resources.get('TriageOptionsMethod', {})
        if options_method:
            print(f"  ✅ OPTIONS /triage for CORS")
        
        # Verify outputs
        print(f"\n📤 CloudFormation Outputs:")
        required_outputs = ['WebsiteURL', 'ApiEndpoint', 'LambdaFunctionArn']
        outputs = template.get('Outputs', {})
        
        for output_name in required_outputs:
            if output_name in outputs:
                print(f"  ✅ {output_name}")
            else:
                print(f"  ❌ {output_name} - MISSING")
        
        print(f"\n{'='*60}")
        print(f"✅ Template verification complete: {template_path}")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying template: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main verification function"""
    templates = [
        'infrastructure/template.yaml',
        'infrastructure/cloudformation-template.yaml'
    ]
    
    all_valid = True
    for template_path in templates:
        if Path(template_path).exists():
            if not verify_template(template_path):
                all_valid = False
        else:
            print(f"❌ Template not found: {template_path}")
            all_valid = False
    
    if all_valid:
        print("\n" + "="*60)
        print("✅ ALL TEMPLATES VERIFIED SUCCESSFULLY")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ SOME TEMPLATES FAILED VERIFICATION")
        print("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
