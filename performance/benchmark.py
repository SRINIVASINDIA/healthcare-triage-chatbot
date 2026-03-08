"""
Performance Benchmarking Tool for Healthcare Triage Chatbot
Measures response times, throughput, and system performance
"""

import requests
import time
import statistics
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import csv

# Configuration
API_ENDPOINT = "https://z6tufnwdj4.execute-api.us-east-1.amazonaws.com/prod/triage"
TEST_MESSAGES = [
    "I have a headache",
    "I have chest pain",
    "I'm feeling tired and have a fever",
    "I have a sore throat and cough",
    "I'm experiencing nausea and dizziness"
]

class PerformanceBenchmark:
    def __init__(self, api_endpoint):
        self.api_endpoint = api_endpoint
        self.results = []
        
    def single_request(self, message):
        """Make a single API request and measure performance"""
        start_time = time.time()
        
        try:
            response = requests.post(
                self.api_endpoint,
                json={"symptoms": message},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "response_size": len(response.content)
            }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                "success": False,
                "status_code": 0,
                "response_time_ms": response_time,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def run_sequential_test(self, num_requests=10):
        """Run sequential requests to measure baseline performance"""
        print(f"\n{'='*60}")
        print(f"Running Sequential Test ({num_requests} requests)")
        print(f"{'='*60}")
        
        results = []
        for i in range(num_requests):
            message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
            print(f"Request {i+1}/{num_requests}: {message[:30]}...")
            
            result = self.single_request(message)
            results.append(result)
            
            print(f"  ✓ Response time: {result['response_time_ms']:.2f}ms")
            
            # Small delay between requests
            time.sleep(0.5)
        
        self.results.extend(results)
        return results
    
    def run_concurrent_test(self, num_requests=10, max_workers=5):
        """Run concurrent requests to test scalability"""
        print(f"\n{'='*60}")
        print(f"Running Concurrent Test ({num_requests} requests, {max_workers} workers)")
        print(f"{'='*60}")
        
        results = []
        messages = [TEST_MESSAGES[i % len(TEST_MESSAGES)] for i in range(num_requests)]
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.single_request, msg) for msg in messages]
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                print(f"  ✓ Request {i+1}/{num_requests} completed: {result['response_time_ms']:.2f}ms")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\nTotal time: {total_time:.2f}s")
        print(f"Throughput: {num_requests/total_time:.2f} requests/second")
        
        self.results.extend(results)
        return results
    
    def run_load_test(self, duration_seconds=60, requests_per_second=2):
        """Run sustained load test"""
        print(f"\n{'='*60}")
        print(f"Running Load Test ({duration_seconds}s, {requests_per_second} req/s)")
        print(f"{'='*60}")
        
        results = []
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            message = TEST_MESSAGES[request_count % len(TEST_MESSAGES)]
            result = self.single_request(message)
            results.append(result)
            request_count += 1
            
            if request_count % 10 == 0:
                elapsed = time.time() - start_time
                print(f"  {request_count} requests in {elapsed:.1f}s")
            
            # Sleep to maintain target rate
            time.sleep(1.0 / requests_per_second)
        
        self.results.extend(results)
        return results
    
    def analyze_results(self):
        """Analyze and print performance statistics"""
        if not self.results:
            print("No results to analyze")
            return
        
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        response_times = [r['response_time_ms'] for r in successful]
        
        print(f"\n{'='*60}")
        print("PERFORMANCE ANALYSIS")
        print(f"{'='*60}")
        
        print(f"\n📊 Request Statistics:")
        print(f"  Total Requests: {len(self.results)}")
        print(f"  Successful: {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        print(f"  Failed: {len(failed)} ({len(failed)/len(self.results)*100:.1f}%)")
        
        if response_times:
            print(f"\n⏱️  Response Time Statistics (ms):")
            print(f"  Min: {min(response_times):.2f}")
            print(f"  Max: {max(response_times):.2f}")
            print(f"  Mean: {statistics.mean(response_times):.2f}")
            print(f"  Median: {statistics.median(response_times):.2f}")
            print(f"  Std Dev: {statistics.stdev(response_times):.2f}" if len(response_times) > 1 else "  Std Dev: N/A")
            
            # Percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            print(f"\n📈 Percentiles:")
            print(f"  P50: {p50:.2f}ms")
            print(f"  P90: {p90:.2f}ms")
            print(f"  P95: {p95:.2f}ms")
            print(f"  P99: {p99:.2f}ms")
        
        # Response time distribution
        if response_times:
            print(f"\n📊 Response Time Distribution:")
            ranges = [
                (0, 1000, "< 1s"),
                (1000, 2000, "1-2s"),
                (2000, 3000, "2-3s"),
                (3000, 5000, "3-5s"),
                (5000, float('inf'), "> 5s")
            ]
            
            for min_time, max_time, label in ranges:
                count = sum(1 for t in response_times if min_time <= t < max_time)
                percentage = count / len(response_times) * 100
                bar = '█' * int(percentage / 2)
                print(f"  {label:8} {bar:25} {count:3} ({percentage:5.1f}%)")
        
        return {
            "total_requests": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) * 100,
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p50": p50 if response_times else 0,
                "p90": p90 if response_times else 0,
                "p95": p95 if response_times else 0,
                "p99": p99 if response_times else 0,
            }
        }
    
    def save_results(self, filename="benchmark_results.csv"):
        """Save results to CSV file"""
        if not self.results:
            print("No results to save")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"\n💾 Results saved to: {filename}")
    
    def generate_report(self, filename="performance_report.json"):
        """Generate comprehensive performance report"""
        analysis = self.analyze_results()
        
        report = {
            "test_date": datetime.now().isoformat(),
            "api_endpoint": self.api_endpoint,
            "total_tests": len(self.results),
            "analysis": analysis,
            "raw_results": self.results
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {filename}")
        return report


def main():
    """Run comprehensive performance benchmark"""
    print("="*60)
    print("Healthcare Triage Chatbot - Performance Benchmark")
    print("="*60)
    
    benchmark = PerformanceBenchmark(API_ENDPOINT)
    
    # Test 1: Sequential baseline
    benchmark.run_sequential_test(num_requests=10)
    
    # Test 2: Concurrent load
    benchmark.run_concurrent_test(num_requests=20, max_workers=5)
    
    # Test 3: Sustained load (optional - comment out for quick test)
    # benchmark.run_load_test(duration_seconds=30, requests_per_second=2)
    
    # Analyze and save results
    benchmark.analyze_results()
    benchmark.save_results("benchmark_results.csv")
    benchmark.generate_report("performance_report.json")
    
    print(f"\n{'='*60}")
    print("✅ Benchmark Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
