# Video Demo Script - Healthcare Triage Chatbot

## 🎬 Demo Duration: 3-5 minutes

---

## 📋 Demo Scenario 1: Low Severity - Cold (30 seconds)

**Purpose:** Show basic symptom assessment with self-care advice

### Input:

**You:** `I have Cold`

**Bot Response:** 
- **Severity Badge:** LOW (green)
- **Advice:** "Manage your symptoms with over-the-counter medications such as pain relievers, decongestants, and cough suppressants. Stay hydrated by drinking plenty of fluids, and consider using a humidifier to relieve congestion. Rest and practice good hygiene to prevent the spread of the cold virus. If symptoms worsen or persist, consider consulting a doctor for further guidance."

**What This Shows:**
- ✅ Quick symptom assessment
- ✅ LOW severity classification
- ✅ Self-care recommendations
- ✅ Clear, actionable advice

---

## 🚨 Demo Scenario 2: Emergency Detection (30 seconds)

**Purpose:** Show life-saving emergency detection feature

### Input:

**You:** `I have chest pain and difficulty in breathing`

**Bot Response:** 🚨 **IMMEDIATE EMERGENCY ALERT**
- **Severity Badge:** SEVERE (red)
- **Alert:** "Call 911 or go to the nearest emergency room immediately. Your symptoms may indicate a medical emergency that requires immediate professional attention."

**What This Shows:**
- ✅ Instant emergency recognition
- ✅ SEVERE severity classification
- ✅ Immediate 911 recommendation
- ✅ Life-saving capability
- ✅ No unnecessary delays

---

## 💬 Demo Scenario 3: Moderate Severity - Fever (45 seconds)

**Purpose:** Show moderate severity assessment with doctor recommendation

### Input:

**You:** `I have fever`

**Bot Response:**
- **Severity Badge:** MODERATE (orange)
- **Advice:** "If you have a fever, it's essential to assess its severity. If your temperature is above 102°F (39°C) and lasts for more than 3-4 days, or if you experience other symptoms such as chills, headache, or body aches, consider visiting your primary care physician within the next 24-48 hours. In the meantime, try to stay hydrated by drinking plenty of fluids, such as water, clear broths, or electrolyte-rich beverages. You can also take over-the-counter medications like acetaminophen or ibuprofen to help reduce your fever..."

**What This Shows:**
- ✅ MODERATE severity classification
- ✅ Detailed assessment criteria
- ✅ Timeline for doctor visit (24-48 hours)
- ✅ Self-care instructions
- ✅ Medication recommendations

---

## 🎯 Demo Scenario 4: Quick Emergency (15 seconds)

**Purpose:** Show instant emergency detection

### Input Sequence:

**You:** `I'm having severe chest pain and can't breathe properly`

**Bot Response:** 🚨 **INSTANT EMERGENCY ALERT**
- Immediate 911 recommendation
- No follow-up questions needed

**What This Shows:**
- ✅ Instant emergency recognition
- ✅ No unnecessary delays
- ✅ Critical symptom detection

---

## 🔄 Demo Scenario 5: Session Restoration (30 seconds)

**Purpose:** Show conversation persistence

### Steps:

1. **Start conversation:**
   **You:** `I have a sore throat`
   
2. **Refresh the page** (F5)

3. **Show:** Conversation history is restored

4. **Continue:**
   **You:** `It's been hurting for 3 days`
   
5. **Show:** Bot remembers the sore throat from before refresh

**What This Shows:**
- ✅ 24-hour session persistence
- ✅ Conversation restoration
- ✅ Seamless user experience

---

## 🎥 Complete Video Demo Script (5 minutes)

### Opening (15 seconds)
```
"Hi! Today I'm demonstrating an AI-powered Healthcare Triage Chatbot 
that I built using AWS Lambda, DynamoDB, and Groq's LLaMA 3.1 model.

This chatbot can analyze symptoms, detect emergencies, and provide 
intelligent medical triage - all in real-time."
```

### Demo 1: Basic Conversation (1 minute)
```
"Let me start with a simple symptom. I'll type: 'I have a headache'"

[Type and show response]

"Notice how it asks follow-up questions to gather more information. 
Let me answer: 'About 2 days'"

[Type and show response]

"It's asking about severity. I'll say: 'It's pretty bad, maybe a 7 out of 10'"

[Type and show response]

"And it asks about other symptoms: 'I also feel a bit nauseous'"

[Type and show response]

"Based on all this information, it provides a triage assessment 
recommending I see a doctor within 24 hours."
```

### Demo 2: Emergency Detection (45 seconds)
```
"Now let me show you the most important feature - emergency detection.

I'll start a new conversation: 'I have some discomfort in my chest'"

[Type and show response]

"It's asking me to describe it. Now watch what happens when I mention 
the word 'pain': 'It's a sharp pain and I'm sweating'"

[Type and show response]

"BOOM! Immediate emergency alert! It detected the pattern 'chest' + 'pain' 
across my messages and immediately tells me to call 911.

This feature could literally save lives by recognizing critical symptoms 
that people might not realize are emergencies."
```

### Demo 3: Context Awareness (1 minute)
```
"Let me show how it maintains context throughout the conversation.

Starting fresh: 'I've been feeling tired lately'"

[Type and show responses for full conversation]

"Notice how when I mention 'the tiredness' later, it remembers I said 
that at the beginning. It's maintaining full conversation context, 
just like ChatGPT."
```

### Demo 4: Session Persistence (30 seconds)
```
"One more cool feature - let me start a conversation: 'I have a sore throat'

Now I'm going to refresh the page..."

[Refresh browser]

"And look - the conversation is still here! It's stored in DynamoDB 
with a 24-hour TTL, so users can come back and continue their conversation."
```

### Closing (30 seconds)
```
"So to recap, this chatbot:
- Provides intelligent medical triage
- Detects emergencies in real-time
- Maintains conversation context
- Persists sessions for 24 hours
- Costs only $8-12 per month for 10,000 conversations

The entire system is serverless, auto-scaling, and production-ready.

The code is open source on GitHub, and there's a live demo you can try right now.

Thanks for watching!"
```

---

## 🎬 Quick Demo Script (2 minutes)

For a shorter demo, use these 3 scenarios:

### 1. Simple Symptom (30 seconds)
```
You: "I have a headache"
Bot: [asks duration]
You: "2 days"
Bot: [asks severity]
You: "About a 7"
Bot: [provides assessment]
```

### 2. Emergency (30 seconds)
```
You: "I have chest discomfort"
Bot: [asks to describe]
You: "It's a sharp pain"
Bot: [🚨 CALL 911 IMMEDIATELY]
```

### 3. Context (1 minute)
```
You: "I'm feeling tired"
Bot: [asks duration]
You: "A week"
Bot: [asks other symptoms]
You: "I have a fever"
Bot: [asks about fever]
You: "101°F"
Bot: [comprehensive assessment referencing tiredness]
```

---

## 📝 Demo Tips

### Before Recording:
1. ✅ Clear browser cache
2. ✅ Close unnecessary tabs
3. ✅ Zoom in browser (Ctrl + +) for better visibility
4. ✅ Test all scenarios once
5. ✅ Have script open on second monitor

### During Recording:
1. 🎤 Speak clearly and slowly
2. ⏸️ Pause after each bot response
3. 👆 Point to important parts on screen
4. 🔄 Show page refresh for session persistence
5. 😊 Be enthusiastic about features

### What to Highlight:
- ⚡ Fast response times (2-4 seconds)
- 🧠 Intelligent follow-up questions
- 🚨 Life-saving emergency detection
- 💬 Natural conversation flow
- 💰 Cost-effectiveness ($8-12/month)
- 🔒 Production-ready with tests

### Screen Recording Settings:
- Resolution: 1920x1080 (Full HD)
- Frame rate: 30 fps
- Audio: Clear microphone
- Cursor: Show cursor highlights
- Zoom: 125-150% browser zoom

---

## 🎯 Key Messages to Emphasize

1. **"This is a LIVE, production-ready system"**
2. **"Emergency detection could save lives"**
3. **"Costs only $8-12/month for 10K conversations"**
4. **"Built with AWS serverless architecture"**
5. **"Open source and fully documented"**

---

## 📱 Social Media Clips

### 30-Second Clip (Emergency Detection)
```
"Watch this AI chatbot detect a medical emergency in real-time..."
[Show chest pain scenario]
"This could save lives! 🚨"
```

### 60-Second Clip (Full Demo)
```
"I built an AI medical triage chatbot. Here's what it can do..."
[Show all 3 quick scenarios]
"Live demo in bio! 🏥"
```

---

## 🔗 Demo URLs to Show

**Live Demo:**
http://healthcare-triage-chatbot-website-997208471264.s3-website-us-east-1.amazonaws.com

**GitHub:**
https://github.com/SRINIVASINDIA/healthcare-triage-chatbot

**Show these in video description!**

---

Good luck with your video demo! 🎬🚀
