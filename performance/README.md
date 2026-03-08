# Performance Testing & Benchmarking

## 🎯 Overview

This directory contains tools to measure and analyze the performance of the Healthcare Triage Chatbot.

## 📊 Available Tools

### 1. API Benchmark (`benchmark.py`)
Tests API response times, throughput, and reliability.

### 2. CloudWatch Metrics (`cloudwatch_metrics.py`)
Retrieves real AWS metrics from CloudWatch.

### 3. Load Testing (`load_test.py`)
Simulates high traffic scenarios.

---

## 🚀 Quick Start

### Install Dependencies
```bash
pip install requests boto3
```

### Run Basic Benchmark
```bash
cd performance
python benchmark.py
```

### Get CloudWatch Metrics
```bash
python cloudwatch_metrics.py
```

---

## 📈 Benchmark Tests

### Test 1: Sequential Baseline
- **Purpose:** Measure single-request performance
- **Requests:** 10 sequential requests
- **Metrics:** Response time, success rate

### Test 2: Concurrent Load
- **Purpose:** Test scalability
- **Requests:** 20 concurrent requests (5 workers)
- **Metrics:** Throughput, concurrent performance

### Test 3: Sustained Load
- **Purpose:** Test stability under continuous load
- **Duration:** 60 seconds
- **Rate:** 2 requests/second
- **Metrics:** Sustained performance, error rate

---

## 📊 Metrics Collected

### Response Time Metrics
- **Min:** Fastest response
- **Max:** Slowest response
- **Mean:** Average response time
- **Median:** Middle value
- **P50, P90, P95, P99:** Percentiles

### Reliability Metrics
- **Success Rate:** % of successful requests
- **Error Rate:** % of failed requests
- **Throughput:** Requests per second

### AWS Metrics (CloudWatch)
- **Lambda Duration:** Function execution time
- **Lambda Invocations:** Number of calls
- **Lambda Errors:** Error count
- **API Gateway Latency:** API response time
- **DynamoDB Capacity:** Read/write units consumed

---

## 📋 Expected Performance

### Response Times
- **Cold Start:** 2-3 seconds (first request)
- **Warm Start:** 200-500ms (subsequent requests)
- **Average:** 1-2 seconds (including AI processing)
- **P95:** < 3 seconds
- **P99:** < 5 seconds

### Throughput
- **Sequential:** ~1 request/second
- **Concurrent:** 5-10 requests/second
- **Max Concurrent:** Limited by Lambda concurrency

### Reliability
- **Success Rate:** > 99%
- **Error Rate:** < 1%
- **Availability:** 99.9% (AWS SLA)

---

## 🎯 Running Benchmarks

### Quick Test (2 minutes)
```bash
python benchmark.py
```

### Full Test (5 minutes)
Edit `benchmark.py` and uncomment:
```python
benchmark.run_load_test(duration_seconds=60, requests_per_second=2)
```

### CloudWatch Analysis
```bash
python cloudwatch_metrics.py
```

---

## 📄 Output Files

### `benchmark_results.csv`
Raw test results with timestamps

### `performance_report.json`
Comprehensive analysis in JSON format

### Console Output
Real-time performance statistics

---

## 📊 Sample Output

```
==============================================================
Healthcare Triage Chatbot - Performance Benchmark
==============================================================

==============================================================
Running Sequential Test (10 requests)
==============================================================
Request 1/10: I have a headache...
  ✓ Response time: 2341.23ms
Request 2/10: I have chest pain...
  ✓ Response time: 456.78ms
...

==============================================================
PERFORMANCE ANALYSIS
==============================================================

📊 Request Statistics:
  Total Requests: 30
  Successful: 30 (100.0%)
  Failed: 0 (0.0%)

⏱️  Response Time Statistics (ms):
  Min: 234.56
  Max: 2341.23
  Mean: 1245.67
  Median: 1123.45
  Std Dev: 456.78

📈 Percentiles:
  P50: 1123.45ms
  P90: 1987.65ms
  P95: 2156.78ms
  P99: 2341.23ms

📊 Response Time Distribution:
  < 1s     ████████████          12 ( 40.0%)
  1-2s     ████████████████      16 ( 53.3%)
  2-3s     ██                     2 (  6.7%)
  3-5s                            0 (  0.0%)
  > 5s                            0 (  0.0%)
```

---

## 🔍 Interpreting Results

### Good Performance
- ✅ P95 < 3 seconds
- ✅ Success rate > 99%
- ✅ No throttling errors
- ✅ Consistent response times

### Performance Issues
- ⚠️ P95 > 5 seconds
- ⚠️ Success rate < 95%
- ⚠️ High error rate
- ⚠️ Increasing response times

### Optimization Needed
- 🔴 P95 > 10 seconds
- 🔴 Success rate < 90%
- 🔴 Frequent throttling
- 🔴 Timeouts

---

## 🛠️ Troubleshooting

### Slow Response Times
1. Check Lambda memory allocation
2. Review CloudWatch logs for cold starts
3. Optimize code (reduce dependencies)
4. Consider provisioned concurrency

### High Error Rate
1. Check CloudWatch logs for errors
2. Verify API endpoint is correct
3. Check AWS service limits
4. Review IAM permissions

### Throttling
1. Increase Lambda concurrency limit
2. Check API Gateway throttling settings
3. Review DynamoDB capacity
4. Implement exponential backoff

---

## 📊 CloudWatch Dashboard

View real-time metrics:
1. Go to AWS CloudWatch Console
2. Navigate to Dashboards
3. Select "healthcare-triage-dashboard"

Metrics available:
- Lambda invocations and errors
- API Gateway requests and latency
- DynamoDB read/write capacity
- Custom application metrics

---

## 🎯 Performance Goals

### Current Performance
- Response Time: 1-2 seconds average
- Throughput: 5-10 req/s
- Availability: 99.9%
- Cost: $8-12/month for 10K requests

### Target Performance
- Response Time: < 1 second average
- Throughput: 50+ req/s
- Availability: 99.99%
- Cost: Maintain under $20/month

---

## 📝 Notes

- **Cold starts** affect first request (2-3s)
- **Warm requests** are much faster (200-500ms)
- **AI processing** takes 1-2 seconds
- **Network latency** adds 50-200ms
- **DynamoDB** operations are fast (< 10ms)

---

## 🔗 Related Documentation

- [AWS Lambda Performance](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [DynamoDB Performance](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

## ✅ Checklist

Before running benchmarks:
- [ ] API endpoint is correct
- [ ] AWS credentials configured
- [ ] Dependencies installed
- [ ] Sufficient AWS quota
- [ ] CloudWatch logging enabled

After running benchmarks:
- [ ] Review results
- [ ] Check for errors
- [ ] Compare with baseline
- [ ] Document findings
- [ ] Optimize if needed
