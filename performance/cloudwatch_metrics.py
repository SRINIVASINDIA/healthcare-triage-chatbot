"""
CloudWatch Metrics Analyzer
Retrieves and analyzes performance metrics from AWS CloudWatch
"""

import boto3
from datetime import datetime, timedelta
import json
from collections import defaultdict

class CloudWatchAnalyzer:
    def __init__(self, region='us-east-1'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        
    def get_lambda_metrics(self, function_name, hours=24):
        """Get Lambda function performance metrics"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = {}
        
        # Invocations
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour
            Statistics=['Sum']
        )
        metrics['invocations'] = sum(point['Sum'] for point in response['Datapoints'])
        
        # Duration
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Duration',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average', 'Maximum', 'Minimum']
        )
        
        if response['Datapoints']:
            durations = response['Datapoints']
            metrics['duration'] = {
                'average': sum(p['Average'] for p in durations) / len(durations),
                'max': max(p['Maximum'] for p in durations),
                'min': min(p['Minimum'] for p in durations)
            }
        
        # Errors
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Errors',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum']
        )
        metrics['errors'] = sum(point['Sum'] for point in response['Datapoints'])
        
        # Throttles
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Throttles',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum']
        )
        metrics['throttles'] = sum(point['Sum'] for point in response['Datapoints'])
        
        # Concurrent Executions
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='ConcurrentExecutions',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Maximum', 'Average']
        )
        
        if response['Datapoints']:
            metrics['concurrent_executions'] = {
                'max': max(p['Maximum'] for p in response['Datapoints']),
                'avg': sum(p['Average'] for p in response['Datapoints']) / len(response['Datapoints'])
            }
        
        return metrics
    
    def get_api_gateway_metrics(self, api_id, hours=24):
        """Get API Gateway performance metrics"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = {}
        
        # Count
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='Count',
            Dimensions=[{'Name': 'ApiId', 'Value': api_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum']
        )
        metrics['request_count'] = sum(point['Sum'] for point in response['Datapoints'])
        
        # Latency
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='Latency',
            Dimensions=[{'Name': 'ApiId', 'Value': api_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average', 'Maximum', 'Minimum']
        )
        
        if response['Datapoints']:
            latencies = response['Datapoints']
            metrics['latency'] = {
                'average': sum(p['Average'] for p in latencies) / len(latencies),
                'max': max(p['Maximum'] for p in latencies),
                'min': min(p['Minimum'] for p in latencies)
            }
        
        # 4XX Errors
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='4XXError',
            Dimensions=[{'Name': 'ApiId', 'Value': api_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum']
        )
        metrics['4xx_errors'] = sum(point['Sum'] for point in response['Datapoints'])
        
        # 5XX Errors
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='5XXError',
            Dimensions=[{'Name': 'ApiId', 'Value': api_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum']
        )
        metrics['5xx_errors'] = sum(point['Sum'] for point in response['Datapoints'])
        
        return metrics
    
    def get_dynamodb_metrics(self, table_name, hours=24):
        """Get DynamoDB performance metrics"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = {}
        
        # Read Capacity
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/DynamoDB',
            MetricName='ConsumedReadCapacityUnits',
            Dimensions=[{'Name': 'TableName', 'Value': table_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum', 'Average']
        )
        
        if response['Datapoints']:
            metrics['read_capacity'] = {
                'total': sum(p['Sum'] for p in response['Datapoints']),
                'average': sum(p['Average'] for p in response['Datapoints']) / len(response['Datapoints'])
            }
        
        # Write Capacity
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/DynamoDB',
            MetricName='ConsumedWriteCapacityUnits',
            Dimensions=[{'Name': 'TableName', 'Value': table_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Sum', 'Average']
        )
        
        if response['Datapoints']:
            metrics['write_capacity'] = {
                'total': sum(p['Sum'] for p in response['Datapoints']),
                'average': sum(p['Average'] for p in response['Datapoints']) / len(response['Datapoints'])
            }
        
        return metrics
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("="*60)
        print("CloudWatch Performance Report")
        print("="*60)
        
        # Lambda metrics
        print("\n📊 Lambda Function Metrics (Last 24 hours)")
        print("-"*60)
        
        lambda_functions = [
            'healthcare-triage-chatbot-triage-function',
            'healthcare-triage-websocket-connect',
            'healthcare-triage-websocket-disconnect',
            'healthcare-triage-websocket-message'
        ]
        
        for func in lambda_functions:
            try:
                metrics = self.get_lambda_metrics(func)
                print(f"\n{func}:")
                print(f"  Invocations: {metrics.get('invocations', 0):.0f}")
                print(f"  Errors: {metrics.get('errors', 0):.0f}")
                print(f"  Throttles: {metrics.get('throttles', 0):.0f}")
                
                if 'duration' in metrics:
                    print(f"  Duration (ms):")
                    print(f"    Average: {metrics['duration']['average']:.2f}")
                    print(f"    Max: {metrics['duration']['max']:.2f}")
                    print(f"    Min: {metrics['duration']['min']:.2f}")
                
                if 'concurrent_executions' in metrics:
                    print(f"  Concurrent Executions:")
                    print(f"    Max: {metrics['concurrent_executions']['max']:.0f}")
                    print(f"    Avg: {metrics['concurrent_executions']['avg']:.2f}")
            except Exception as e:
                print(f"  ⚠️  Could not retrieve metrics: {e}")
        
        # API Gateway metrics
        print("\n\n📊 API Gateway Metrics (Last 24 hours)")
        print("-"*60)
        
        try:
            api_metrics = self.get_api_gateway_metrics('z6tufnwdj4')
            print(f"  Total Requests: {api_metrics.get('request_count', 0):.0f}")
            print(f"  4XX Errors: {api_metrics.get('4xx_errors', 0):.0f}")
            print(f"  5XX Errors: {api_metrics.get('5xx_errors', 0):.0f}")
            
            if 'latency' in api_metrics:
                print(f"  Latency (ms):")
                print(f"    Average: {api_metrics['latency']['average']:.2f}")
                print(f"    Max: {api_metrics['latency']['max']:.2f}")
                print(f"    Min: {api_metrics['latency']['min']:.2f}")
        except Exception as e:
            print(f"  ⚠️  Could not retrieve metrics: {e}")
        
        # DynamoDB metrics
        print("\n\n📊 DynamoDB Metrics (Last 24 hours)")
        print("-"*60)
        
        try:
            db_metrics = self.get_dynamodb_metrics('healthcare-triage-conversations')
            
            if 'read_capacity' in db_metrics:
                print(f"  Read Capacity:")
                print(f"    Total: {db_metrics['read_capacity']['total']:.2f}")
                print(f"    Average: {db_metrics['read_capacity']['average']:.2f}")
            
            if 'write_capacity' in db_metrics:
                print(f"  Write Capacity:")
                print(f"    Total: {db_metrics['write_capacity']['total']:.2f}")
                print(f"    Average: {db_metrics['write_capacity']['average']:.2f}")
        except Exception as e:
            print(f"  ⚠️  Could not retrieve metrics: {e}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    analyzer = CloudWatchAnalyzer()
    analyzer.generate_performance_report()
