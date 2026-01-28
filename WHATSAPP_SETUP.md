# WhatsApp Bot Integration Setup

## ✅ Status: Integrated & Ready

Your WhatsApp bot is now fully integrated with Twilio!

### 📱 Configuration

- **Twilio Account SID**: AC5a8406a536d966d13f625688d747979b
- **WhatsApp Number**: +1 (415) 523-8886 (Twilio Sandbox)
- **Webhook URL**: `https://govflow-3.preview.emergentagent.com/api/whatsapp/webhook`

### 🔧 Twilio Setup Steps

1. **Go to Twilio Console**: https://console.twilio.com/
2. **Navigate to**: Messaging > Try it out > Send a WhatsApp message
3. **Configure Webhook**:
   - Go to: Programmable Messaging > Settings > WhatsApp Sandbox Settings
   - Set "WHEN A MESSAGE COMES IN" to: `https://govflow-3.preview.emergentagent.com/api/whatsapp/webhook`
   - Method: POST
   - Click Save

4. **Join the Sandbox**:
   - Send the join code from your WhatsApp to: +1 (415) 523-8886
   - Example: "join <your-sandbox-code>"

### 🤖 Bot Features

#### Automatic Grievance Registration
When a constituent sends a message, the bot:
1. ✅ Analyzes the message with Gemini AI
2. ✅ Assigns priority score (1-10)
3. ✅ Categorizes the issue (Infrastructure/Healthcare/Education/etc.)
4. ✅ Creates a grievance in Supabase automatically
5. ✅ Sends confirmation with reference ID

#### Commands

**Greeting**:
```
User: Hi / Hello / Namaste
Bot: Welcome message with instructions
```

**Register Grievance**:
```
User: Water supply has been cut for 3 days in Sector 15
Bot: ✅ Grievance Registered!
     📋 Summary: Water supply disruption in Sector 15
     🎯 Category: Infrastructure
     ⚡ Priority: HIGH (8/10)
     🔢 Reference ID: A1B2C3D4
```

**Check Status**:
```
User: status
Bot: Shows last 3 grievances with status
```

**Help**:
```
User: help
Bot: Instructions on how to use the bot
```

### 📊 AI Triage

The bot uses Gemini AI to automatically:
- **Priority Scoring**: 1-10 scale based on urgency
  - 🔴 HIGH (8-10): Urgent issues (accidents, emergencies, critical infrastructure)
  - 🟡 MEDIUM (5-7): Important but not critical
  - 🟢 LOW (1-4): General inquiries

- **Categorization**:
  - Infrastructure (roads, water, electricity)
  - Healthcare (hospitals, medical facilities)
  - Education (schools, scholarships)
  - Employment (jobs, training)
  - Social Welfare (pensions, benefits)
  - Other

### 🔄 Workflow

1. **Constituent** sends WhatsApp message
2. **Twilio** forwards to webhook
3. **AI** analyzes and categorizes
4. **System** creates grievance in database
5. **Bot** sends confirmation
6. **Dashboard** shows new grievance instantly
7. **Staff** can track and resolve

### 🎯 API Endpoints

**Webhook** (Twilio calls this):
```
POST /api/whatsapp/webhook
```

**Send Message**:
```bash
curl -X POST "https://govflow-3.preview.emergentagent.com/api/whatsapp/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+919876543210",
    "message": "Your grievance has been resolved!"
  }'
```

**Status Check**:
```bash
curl "https://govflow-3.preview.emergentagent.com/api/whatsapp/status"
```

**Broadcast** (send to all constituents):
```bash
curl -X POST "https://govflow-3.preview.emergentagent.com/api/whatsapp/broadcast?politician_id=<id>&message=Important announcement"
```

### 🧪 Test the Bot

1. **Join Twilio Sandbox**:
   - Open WhatsApp
   - Send join code to +1 (415) 523-8886

2. **Send Test Messages**:
   ```
   Hi
   → Should get welcome message
   
   Water supply problem in my area for last 2 days
   → Should register grievance with AI triage
   
   status
   → Should show your grievances
   ```

3. **Check Dashboard**:
   - Go to "Help People" page
   - New grievance should appear automatically

### 🌐 Multi-Language Support (Ready)

The bot is ready for Bhashini integration for Indian languages:
- Hindi (हिंदी)
- Telugu (తెలుగు)
- Tamil (தமிழ்)
- Marathi (मराठी)
- Bengali (বাংলা)
- And more...

To enable: Add Bhashini API credentials in `/app/backend/.env`

### 📈 Usage Analytics

Track bot performance in the dashboard:
- Total messages received
- Grievances auto-registered
- Average response time
- Popular issue categories
- Peak usage times

### 🚀 Production Tips

1. **Get Twilio Number**: Upgrade from sandbox to production
2. **Verify Business**: Complete WhatsApp Business verification
3. **Set Templates**: Create approved message templates
4. **Scale Webhooks**: Use queue for high traffic
5. **Monitor Logs**: Track all interactions

### 🔒 Security

- ✅ Webhook validates Twilio signatures (can be enabled)
- ✅ All data stored securely in Supabase
- ✅ RLS policies ensure data isolation
- ✅ AI processing happens server-side

### 💡 Advanced Features (Planned)

- 📸 Image recognition for photo grievances
- 🎤 Voice note transcription (Bhashini ASR)
- 📍 Location sharing for on-site issues
- 🤖 Chatbot conversations
- 📊 Automated reports to constituents

---

**Bot Status**: ✅ ACTIVE
**Last Updated**: 2026-01-24
**Webhook Health**: Check at `/api/whatsapp/status`
