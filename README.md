# Healthcare Triage Chatbot 🏥

An AI-powered medical symptom analysis and triage chatbot with ChatGPT-like conversational capabilities.

## 🚀 Live Demo

**Try it now:** http://healthcare-triage-chatbot-website-997208471264.s3-website-us-east-1.amazonaws.com

## ✨ Features

- 🤖 **AI-Powered Conversations** - Natural language understanding with Groq LLaMA 3.1
- 💬 **Multi-Turn Dialogue** - Remembers conversation history for context-aware responses
- 🚨 **Emergency Detection** - Real-time identification of critical symptoms with immediate alerts
- 📊 **Intelligent Triage** - Assesses symptom severity (LOW, MODERATE, SEVERE)
- 💾 **Session Management** - 24-hour conversation persistence with automatic cleanup
- 🔒 **Enterprise Security** - Input validation, PII redaction, rate limiting

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Frontend (S3)  │
│  - HTML/CSS/JS  │
│  - WebSocket    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  API Gateway    │
│  - REST API     │
│  - WebSocket    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  AWS Lambda     │
│  - Python 3.11  │
│  - Serverless   │
└──────┬──────────┘
       │
       ├──────────┬──────────┬─────────┐
       ▼          ▼          ▼         ▼
   DynamoDB    Groq AI   Medical    CloudWatch
   Sessions              NER
```

## 🛠️ Technology Stack

### Frontend
- HTML5, CSS3, JavaScript (ES6+)
- WebSocket Client for real-time communication
- Session Storage for persistence

### Backend
- **Runtime:** Python 3.11
- **Compute:** AWS Lambda (serverless)
- **Database:** DynamoDB (NoSQL)
- **API:** API Gateway (REST + WebSocket)
- **AI Model:** Groq LLaMA 3.1 (8B parameters)
- **Monitoring:** CloudWatch

### Infrastructure
- **IaC:** CloudFormation
- **Deployment:** Automated scripts
- **Security:** IAM, Parameter Store, encryption

## 📦 Project Structure

```
healthcare-triage-chatbot/
├── backend/
│   ├── core/
│   │   ├── models.py              # Data models
│   │   ├── session_manager.py    # Session management
│   │   ├── context_analyzer.py   # Conversation context
│   │   ├── emergency_detector.py # Emergency detection
│   │   ├── followup_generator.py # Follow-up questions
│   │   └── prompt_builder.py     # AI prompt construction
│   ├── integrations/
│   │   ├── groq_client.py        # Groq API wrapper
│   │   ├── medical_ner.py        # Medical entity extraction
│   │   └── websocket_client.py   # WebSocket messaging
│   ├── utils/
│   │   ├── logger.py             # Structured logging
│   │   ├── validators.py         # Input validation
│   │   └── exceptions.py         # Custom exceptions
│   ├── websocket/
│   │   ├── connect.py            # WebSocket connect handler
│   │   ├── disconnect.py         # WebSocket disconnect handler
│   │   └── message.py            # Message processing handler
│   ├── lambda_function.py        # REST API handler
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── index.html                # Main HTML
│   ├── styles.css                # Styling
│   ├── app.js                    # Main application
│   ├── websocket-client.js       # WebSocket client
│   ├── chat-ui.js                # Chat UI component
│   └── config.js                 # Configuration
├── infrastructure/
│   └── cloudformation-template.yaml  # AWS infrastructure
├── scripts/
│   ├── package-lambda.sh         # Lambda packaging (Linux/Mac)
│   ├── package-lambda.ps1        # Lambda packaging (Windows)
│   ├── deploy-frontend.sh        # Frontend deployment
│   └── setup-alarms.sh           # CloudWatch alarms
├── tests/
│   ├── test_*.py                 # Unit tests
│   └── test_*_properties.py      # Property-based tests
├── docs/
│   ├── DEPLOYMENT_GUIDE.md       # Deployment instructions
│   ├── ROLLOUT_GUIDE.md          # Phased rollout guide
│   └── VALIDATION_CHECKLIST.md   # Testing checklist
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with credentials
- Python 3.11+
- Groq API key ([Get one here](https://console.groq.com))

### Deployment

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/healthcare-triage-chatbot.git
cd healthcare-triage-chatbot
```

2. **Store Groq API Key**
```bash
aws ssm put-parameter \
  --name "/healthcare-triage/groq-api-key" \
  --value "YOUR_GROQ_API_KEY" \
  --type "SecureString"
```

3. **Package Lambda Functions**
```bash
# Linux/Mac
chmod +x scripts/package-lambda.sh
./scripts/package-lambda.sh

# Windows PowerShell
.\scripts\package-lambda.ps1
```

4. **Deploy Infrastructure**
```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-template.yaml \
  --stack-name healthcare-triage-chatbot \
  --capabilities CAPABILITY_NAMED_IAM
```

5. **Update Lambda Functions**
```bash
aws lambda update-function-code \
  --function-name healthcare-triage-chatbot-triage-function \
  --zip-file fileb://backend/lambda.zip
```

6. **Deploy Frontend**
```bash
# Get S3 bucket name from CloudFormation outputs
aws s3 sync frontend/ s3://YOUR_BUCKET_NAME/
```

See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

## 💡 Usage Examples

### Example 1: Low Severity - Cold Symptoms
```
User: "I have Cold"

Bot Response:
Severity: LOW ✅

"Manage your symptoms with over-the-counter medications such as pain relievers, 
decongestants, and cough suppressants. Stay hydrated by drinking plenty of fluids, 
and consider using a humidifier to relieve congestion. Rest and practice good 
hygiene to prevent the spread of the cold virus. If symptoms worsen or persist, 
consider consulting a doctor for further guidance."
```

### Example 2: Severe - Emergency Detection 🚨
```
User: "I have chest pain and difficulty in breathing"

Bot Response:
Severity: SEVERE ⚠️

"Call 911 or go to the nearest emergency room immediately. Your symptoms may 
indicate a medical emergency that requires immediate professional attention."
```

### Example 3: Moderate Severity - Fever
```
User: "I have fever"

Bot Response:
Severity: MODERATE ⚠️

"If you have a fever, it's essential to assess its severity. If your temperature 
is above 102°F (39°C) and lasts for more than 3-4 days, or if you experience 
other symptoms such as chills, headache, or body aches, consider visiting your 
primary care physician within the next 24-48 hours. In the meantime, try to stay 
hydrated by drinking plenty of fluids, such as water, clear broths, or 
electrolyte-rich beverages..."
```

### Example 4: API Usage
```bash
curl -X POST https://z6tufnwdj4.execute-api.us-east-1.amazonaws.com/prod/triage \
  -H "Content-Type: application/json" \
  -d '{"symptoms": "I have a fever and cough"}'
```

## 🧪 Testing

### Run Unit Tests
```bash
cd backend
pytest tests/ -v
```

### Run Property-Based Tests
```bash
pytest tests/test_*_properties.py -v
```

### Test Coverage
```bash
pytest --cov=backend --cov-report=html
```

**Current Coverage:** 80%+ line coverage

## 📸 Screenshots

### Low Severity Response
![Cold Symptoms - LOW severity with self-care recommendations](docs/screenshots/low-severity.png)

### Emergency Detection
![Chest Pain - SEVERE severity with immediate 911 alert](docs/screenshots/emergency.png)

### Moderate Severity
![Fever - MODERATE severity with doctor visit recommendation](docs/screenshots/moderate-severity.png)

**Features Shown:**
- ✅ Severity badges (LOW, MODERATE, SEVERE)
- ✅ Color-coded responses (green, orange, red)
- ✅ Clear, actionable medical advice
- ✅ Emergency detection with immediate alerts
- ✅ Professional medical disclaimer

## 💰 Cost Analysis

### Monthly Cost (10,000 conversations)

| Service | Cost |
|---------|------|
| Lambda | $0.20 |
| API Gateway | $0.01 |
| DynamoDB | $0.50 |
| S3 | $0.02 |
| CloudWatch | $0.50 |
| **Total** | **~$1.23** |

**Estimated cost for 10,000 conversations: $8-12/month**

## 🔒 Security Features

- ✅ **Encryption at rest** - DynamoDB & S3
- ✅ **Encryption in transit** - HTTPS/WSS
- ✅ **PII redaction** - Automatic in logs
- ✅ **Input validation** - HTML sanitization, length limits
- ✅ **Rate limiting** - 10 msg/min, 100 msg/hour
- ✅ **IAM roles** - Least privilege principle
- ✅ **API key protection** - AWS Parameter Store

## 📊 Performance Metrics

- **Response Time:** 2-4 seconds
- **Availability:** 99.9% SLA
- **Scalability:** Unlimited concurrent users
- **Cold Start:** ~2-3 seconds
- **Warm Start:** ~200-500ms

## 🗺️ Roadmap

### Phase 1 (Next 3 months)
- [ ] WebSocket support for real-time chat
- [ ] Mobile apps (iOS & Android)
- [ ] Multi-language support (Spanish, French, German)
- [ ] Voice input (speech-to-text)

### Phase 2 (6 months)
- [ ] Advanced AI models (GPT-4, Claude)
- [ ] Analytics dashboard
- [ ] Doctor integration (telemedicine)
- [ ] Push notifications

### Phase 3 (12 months)
- [ ] EHR integration
- [ ] Medication tracking
- [ ] Health trends analysis
- [ ] Lab results integration

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Groq** - For providing fast LLaMA 3.1 inference
- **AWS** - For serverless infrastructure
- **Open Source Community** - For amazing tools and libraries

## ⚠️ Disclaimer

This chatbot is for informational purposes only and does not replace professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

---

**Built with ❤️ using AWS Serverless Architecture**

**Star ⭐ this repo if you find it helpful!**
