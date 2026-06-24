# iGosa — Product Requirements Document v1.0
## WhatsApp AI Agent Platform for South African Estate Agents

---

## 1. EXECUTIVE SUMMARY

**iGosa** turns any estate agent's WhatsApp number into a 24/7 AI-powered property assistant. Business owners connect their WhatsApp to iGosa once. From that moment, every customer who messages them gets instant AI responses — property searches, valuations, bond affordability checks, viewing bookings, document collection, and automated follow-ups. No app to install. No website needed. Just WhatsApp.

**Target Market:** Independent estate agents and small agencies in Johannesburg townships and suburbs (Soweto, Pimville, Diepkloof, Alexandra, Tembisa, Lenasia, etc.)

**Core Promise:** "Your phone now works 24/7. You sell more houses. We handle the tech."

---

## 2. USER PERSONAS

### 2.1 Primary: Real Estate Business Owner (Agent)
- **Name:** Thabiso (example)
- **Profile:** Independent agent or small agency owner (1–5 agents)
- **Tech level:** Comfortable with WhatsApp, not with websites/CRMs
- **Pain points:** Can't reply to all inquiries, loses leads when busy, forgets follow-ups, no pipeline visibility
- **Goal:** Close more deals without working more hours

### 2.2 Secondary: Property Buyer/Client
- **Profile:** Individual looking to buy, rent, or sell property
- **Tech level:** Uses WhatsApp daily
- **Behavior:** Messages multiple agents, expects fast replies, shops around
- **Pain points:** Agents take hours/days to reply, asks same questions repeatedly, gets forgotten

### 2.3 Tertiary: Tenant/Landlord
- **Profile:** Renter or property owner with rental portfolio
- **Pain points:** Late rent reminders, maintenance requests ignored, lease tracking

---

## 3. HOW BUSINESS OWNERS SHARE THE WHATSAPP AGENT

### The Core Distribution Model

The agent shares **one WhatsApp number** — their existing business number connected to Evolution API. Customers message this number like they would any agent. The difference: iGosa is running behind it.

### Sharing Methods

#### Method A: Direct Number Sharing (Primary)
```
Agent tells customers: "WhatsApp me on 061 298 0377"
```

Where they share it:
- Business cards
- Facebook Marketplace listings
- Gumtree ads
- Property24/Private Property listings
- "For Sale" boards outside properties
- Community WhatsApp groups
- Word of mouth

The customer messages the number → iGosa responds instantly.

#### Method B: WhatsApp Click-to-Chat Link
```
https://wa.me/27612980377?text=Hi%2C%20I%27m%20looking%20for%20a%20property
```

Where it's used:
- Facebook posts and ads → "Message us on WhatsApp"
- Instagram bio link
- Email signatures
- Digital business cards
- Property listing descriptions

#### Method C: QR Code
A QR code that opens WhatsApp chat with the agent. Printed on:
- Property flyers and brochures
- Office windows
- Open house signs
- Business cards

#### Method D: Facebook/Instagram "WhatsApp" Button
Connected to the business Facebook page. Customer clicks → WhatsApp opens → iGosa handles it.

#### Method E: Property Portal Forwarding
Agent lists their WhatsApp number on Property24, Private Property, or Gumtree. Inquiries come via WhatsApp → iGosa qualifies the lead automatically.

---

## 4. COMPLETE USER JOURNEY

### 4.1 AGENT ONBOARDING JOURNEY

```
DAY 0 — Sign Up
─────────────────
1. Agent visits iGosa website or is contacted by sales
2. Selects plan: Starter (R499/mo) / Pro (R999/mo) / Enterprise (R1,999/mo)
3. Provides WhatsApp number
4. iGosa backend creates agent record
5. Agent receives WhatsApp message: "🎉 Welcome to iGosa! Your AI assistant is now active..."

DAY 0 — Setup (5 minutes)
───────────────────────────
6. Agent adds their service areas (e.g., "Soweto, Pimville")
7. Agent adds first listings via WhatsApp:
   Agent: "add listing: 3 bed Pimville R450K"
   iGosa: "✅ Listing Created! ID: abc12345. Send photos to add them."
8. Agent forwards their existing WhatsApp contacts/prospects
9. Agent shares their number with customers (methods above)

DAY 1+ — Daily Use
───────────────────
10. Customer messages the agent's WhatsApp number
11. iGosa responds within 2 seconds
12. Agent sees conversations in dashboard (Lovable frontend)
13. Agent intervenes only when deal is warm
14. Agent checks pipeline: sends "pipeline" to their own WhatsApp
15. Agent gets morning briefing: "📊 3 new leads overnight, 2 follow-ups due"
```

### 4.2 BUYER JOURNEY (Cold → Closed Deal)

```
STAGE 1: DISCOVERY
──────────────────
Buyer sees agent's WhatsApp number on a Facebook listing:
"🏠 3 bed Pimville R450K — WhatsApp 061 298 0377"

Buyer messages: "Is this still available?"

iGosa responds (within 2 seconds):
"Hi! 👋 Yes, the 3-bed in Pimville is still available at R450K.
📍 Pimville | 🛏 3 bed | 🛁 2 bath | 💰 R450,000
Would you like to book a viewing? 📅"

┌─────────────────────────────────────────┐
│ BEHIND THE SCENES                       │
│ • Intent classified: property_search    │
│ • Lead created in database              │
│ • Lead score: 45 (warm — budget unclear)│
│ • Agent NOT notified yet (score < 70)   │
└─────────────────────────────────────────┘

STAGE 2: QUALIFICATION
───────────────────────
Buyer: "Yes I'd like to see it. I have about R400K budget."

iGosa:
"Great! R400K budget works for this area. 🏠
Quick question — are you pre-approved for a bond, or paying cash?
I can connect you with a bond originator at no cost to you."

Buyer: "I need a bond. I earn about R15,000 per month."

iGosa:
"Based on R15,000/month income, you could qualify for approximately R380,000–R450,000 bond.
🎉 You may also qualify for a FLISP government subsidy of up to R130,000!

Would you like me to:
1. Connect you with a bond originator?
2. Book a viewing for Saturday?
3. Send similar properties in your budget?"

┌─────────────────────────────────────────┐
│ BEHIND THE SCENES                       │
│ • Bond affordability calculated         │
│ • FLISP eligibility checked (R15K = YES)│
│ • Lead score updated: 72 (HOT 🔥)       │
│ • Agent notified: "🔔 HOT LEAD"         │
│ • Lead stored with preferences          │
└─────────────────────────────────────────┘

STAGE 3: VIEWING
─────────────────
Buyer: "Book viewing for Saturday morning."

iGosa:
"📅 Viewing Booked!
🏠 23 Jabu Street, Pimville
📅 Saturday, 10:00 AM
👤 Your agent: Thabiso
📞 061 298 0377

📍 Google Maps: [link]
Please arrive on time. Reply to reschedule."

┌─────────────────────────────────────────┐
│ BEHIND THE SCENES                       │
│ • Viewing added to agent's calendar     │
│ • Deal created in pipeline: "viewing"   │
│ • Follow-up scheduled for post-viewing  │
│ • Document collection started in bg     │
└─────────────────────────────────────────┘

STAGE 4: POST-VIEWING FOLLOW-UP
─────────────────────────────────
[48 hours after viewing — automatic]

iGosa messages buyer:
"Hi! 👋 How did you feel about the Pimville property?
Any questions I can answer? The seller is open to offers."

Buyer: "I liked it. I want to make an offer of R420K."

iGosa:
"Excellent! 🎉 I'll prepare the Offer to Purchase.
To proceed, I'll need:
📄 Copy of your ID (both sides)
📄 Proof of address (not older than 3 months)
📄 3 months bank statements

You can send photos of these right here on WhatsApp."

┌─────────────────────────────────────────┐
│ BEHIND THE SCENES                       │
│ • Deal stage updated: viewing → offer   │
│ • Agent notified of offer               │
│ • OTP preparation started               │
│ • Document request sent automatically   │
└─────────────────────────────────────────┘

STAGE 5: CLOSING
─────────────────
Buyer sends documents as WhatsApp photos.

iGosa:
"✅ Documents received! Your Offer to Purchase is being prepared.
Your agent Thabiso will review and send it for signing."

Agent (intervening now):
"Offer to Purchase is ready. I've sent it to the seller.
They have 48 hours to respond. Your bond application is with Standard Bank."

[5 days later — automatic update]

iGosa:
"🎉 Great news! Your bond has been approved by Standard Bank.
Next step: The transferring attorney will contact you to arrange registration."

[30 days later — automatic check-in]

iGosa:
"Hi! 🏠 Hope you're enjoying your new home in Pimville!
Everything settled in okay? Need any recommendations for nearby services?"

┌─────────────────────────────────────────┐
│ BEHIND THE SCENES                       │
│ • Deal closed: R420K                    │
│ • Commission: R29,400 (7%)              │
│ • 30-day post-sale follow-up triggered  │
│ • Buyer added to "past clients" list    │
│ • Re-engagement scheduled for 6 months  │
└─────────────────────────────────────────┘
```

### 4.3 THE AGENT'S EXPERIENCE DURING THIS JOURNEY

```
WHAT THE AGENT SEES & DOES:

DAY 1 (Buyer Discovery)
  📱 Phone buzzes: nothing — iGosa handled it
  📊 Dashboard: +1 new lead (Warm, Score 45)

DAY 1 (Buyer Qualification)
  📱 Phone buzzes: "🔔 HOT LEAD: Midrand buyer, R400K budget, needs bond"
  📊 Dashboard: Lead moved to Hot (Score 72)
  🤖 Agent action: None needed — iGosa is handling qualification

DAY 3 (Viewing Day)
  📱 Phone buzzes: "📅 Viewing: 10am, 23 Jabu St, Pimville"
  👤 Agent action: Shows up for viewing, answers questions
  📊 Dashboard: Deal in "viewing" stage, R420K potential

DAY 5 (Post-Viewing)
  📱 Phone buzzes: "💰 OFFER MADE: R420K on Pimville property"
  👤 Agent action: Reviews OTP, negotiates with seller
  📊 Dashboard: Deal moved to "negotiation"

DAY 10 (Closing)
  📱 Nothing — iGosa tracking bond progress
  📊 Dashboard: Deal in "bond_pending", documents all received ✅
  👤 Agent action: Connects with transferring attorney

DAY 40 (Post-Sale)
  📱 Nothing — automated check-in sent
  📊 Dashboard: Deal CLOSED 🎉 | R29,400 commission
  👤 Agent action: None — iGosa nurturing for future referrals
```

---

## 5. SYSTEM ARCHITECTURE (User-Facing View)

```
┌──────────────────────────────────────────────────────┐
│                   CUSTOMER/CLIENT                      │
│                                                       │
│  "Is the 3-bed in Pimville still available?"          │
│  Sends WhatsApp message to agent's number             │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│              WHATSAPP (Meta Platform)                  │
│  Message delivered to Evolution API instance          │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│            iGosa AI ENGINE (Render)                    │
│                                                       │
│  1. Intent Classifier → "property_search"             │
│  2. Entity Extractor → {beds:3, area:Pimville}        │
│  3. Listing Search → Found 2 matching properties      │
│  4. Smart Responder → Generates natural reply         │
│  5. Lead Scorer → Score: 72 (Hot)                     │
│  6. FollowUp Scheduler → Schedule 48h check-in        │
│  7. Response sent back via Evolution API              │
└────────────────────┬─────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Supabase │ │ Agent   │ │ Agent   │
    │(DB)     │ │ Phone   │ │Dashboard│
    │         │ │(Alerts) │ │(Lovable)│
    └─────────┘ └─────────┘ └─────────┘
```

---

## 6. FEATURE SET

### 6.1 For Customers (WhatsApp)
| Feature | Trigger | Example |
|---------|---------|---------|
| Instant property search | "2 bed Soweto R400K" | iGosa replies with matching listings in 2s |
| Bond affordability | "Can I afford R500K?" | Calculates max bond, checks FLISP |
| Property valuation | "Value my house" | Area benchmark estimate |
| Viewing booking | "I want to see it" | Books viewing, sends confirmation |
| Document collection | Auto after offer | Requests FICA docs via WhatsApp |
| 24/7 availability | Any message, any time | Always responds |

### 6.2 For Agents (Dashboard + WhatsApp Commands)
| Feature | How |
|---------|-----|
| Pipeline view | Send "pipeline" to your WhatsApp |
| Add listing | "add listing: 3 bed Pimville R450K" |
| Market report | "market report Soweto" |
| Lead status | Dashboard shows all leads scored |
| Deal tracking | Kanban board on dashboard |
| Rental management | "rentals" — see portfolio |
| Morning briefing | Daily automated WhatsApp message |

---

## 7. PRICING & PLANS

| Tier | Price | Key Features |
|------|-------|-------------|
| **Starter** | R499/mo | 50 listings, basic auto-reply, 10 valuations/mo, weekly market report |
| **Pro** | R999/mo | 200 listings, smart follow-ups, social auto-poster, bond calculator, document collection |
| **Enterprise** | R1,999/mo | Unlimited everything, rental manager, voice response, multi-agent pool, white label |

---

## 8. SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Response time | < 3 seconds |
| Lead capture rate | 100% (every message creates a lead) |
| Follow-up completion | 90%+ (AI never forgets) |
| Agent time saved | 15–25 hours/week |
| Lead-to-viewing conversion | 2x improvement |
| Viewing-to-offer conversion | 1.5x improvement |

---

## 9. COMPETITIVE MOAT

1. **WhatsApp-only** — No app install. No website. Agents already use WhatsApp.
2. **SA-specific** — Knows RDP, FLISP, township areas, code-switching
3. **End-to-end** — From first message to closed deal, not just a chatbot
4. **Agent-owned number** — Customers message the agent's real number, not a bot number
5. **Pipeline visibility** — Agent sees exactly where every lead is

---

*PRD v1.0 — June 2026*
