# iGosa + Lovable.dev Integration Guide
## Building the Real Estate Business Owner Dashboard

---

## Architecture

```
┌────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Lovable.dev   │────▶│   iGosa API     │────▶│  Evolution API    │
│  (Dashboard)   │     │  (Render)        │     │  (Render, already │
│                │◀────│                  │◀────│   deployed)       │
└───────┬────────┘     └────────┬────────┘     └──────────────────┘
        │                       │
        │              ┌────────▼────────┐
        └──────────────▶    Supabase     │
                       │  (Hosted DB)    │
                       │  + PostGIS      │
                       └─────────────────┘
```

---

## Part 1: iGosa API Endpoints (Feed to Lovable)

Once deployed to Render, your Lovable dashboard calls these:

### Base URL
```
https://igosa.onrender.com
```

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | None | Service info + endpoint list |
| `GET` | `/webhook/health` | None | Health check |
| `POST` | `/api/agents` | None | Register new agent |
| `GET` | `/api/agents/{id}` | None | Get agent details |
| `PUT` | `/api/agents/{id}` | None | Update agent settings |
| `GET` | `/api/dashboard/{agent_id}` | None | Full dashboard data |
| `GET` | `/api/tasks/pending/{agent_id}` | None | Pending follow-ups |
| `POST` | `/api/tasks/process` | None | Trigger task processing |

### Dashboard Response Shape (what Lovable will render)

```json
{
  "agent": {
    "name": "Thabiso",
    "business": "iGosa Test Properties",
    "tier": "starter"
  },
  "listings": {
    "total": 12,
    "active": 8,
    "under_offer": 2,
    "sold": 2,
    "avg_price": 450000
  },
  "pipeline": {
    "active_deals": 5,
    "pipeline_value": 2100000,
    "est_commission": 147000,
    "closed_this_month": 2,
    "hot_deals": 3
  },
  "leads": {
    "total": 34,
    "new": 7
  },
  "tasks": {
    "pending_follow_ups": 12,
    "pending_total": 15
  },
  "rentals": {
    "units": 4,
    "collected": 8500,
    "outstanding": 1500
  },
  "market": [
    {"area": "Soweto", "trend": "up", "avg": 420000},
    {"area": "Pimville", "trend": "up", "avg": 450000}
  ]
}
```

---

## Part 2: Supabase Schema (Lovable Native Integration)

When you create a Supabase project and connect it to Lovable, use this schema:

### Tables

```sql
-- Agents (business owners)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_number VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(200),
    logo_url TEXT,
    areas TEXT[],           -- ['Soweto', 'Pimville']
    subscription_tier VARCHAR(20) DEFAULT 'starter',
    subscription_status VARCHAR(20) DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Properties
CREATE TABLE listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    status VARCHAR(20) DEFAULT 'active',
    title VARCHAR(300) NOT NULL,
    description TEXT,
    bedrooms INT,
    bathrooms INT,
    price DECIMAL NOT NULL,
    suburb VARCHAR(100),
    city VARCHAR(50) DEFAULT 'Johannesburg',
    property_type VARCHAR(30) DEFAULT 'house',
    photos TEXT[],          -- URLs
    features TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Leads / Contacts
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    whatsapp_number VARCHAR(20) NOT NULL,
    display_name VARCHAR(100),
    lead_type VARCHAR(20),  -- buyer/seller/tenant
    lead_status VARCHAR(20) DEFAULT 'new',
    qualification_score INT,
    budget_min DECIMAL,
    budget_max DECIMAL,
    preferred_areas TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Deals Pipeline
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    listing_id UUID REFERENCES listings(id),
    lead_id UUID REFERENCES leads(id),
    deal_stage VARCHAR(30) DEFAULT 'lead',
    deal_value DECIMAL,
    commission_estimate DECIMAL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Conversations (for activity feed)
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    lead_id UUID REFERENCES leads(id),
    direction VARCHAR(10),   -- inbound/outbound
    message_text TEXT,
    intent_classified VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Part 3: Lovable.dev Setup Steps

### Step 1: Create Supabase Project
- Go to supabase.com → New Project
- Copy the SQL above into SQL Editor → Run
- Copy Project URL + anon key

### Step 2: New Lovable Project
- Go to lovable.dev → New Project
- Select "Supabase" as backend
- Paste your Supabase URL + anon key
- Lovable auto-generates types from your schema

### Step 3: Define API Calls
In Lovable, create an API client that calls your iGosa Render backend:

```typescript
// api/client.ts
const IGOSA_API = "https://igosa.onrender.com";

export async function getDashboard(agentId: string) {
  const res = await fetch(`${IGOSA_API}/api/dashboard/${agentId}`);
  return res.json();
}

export async function updateAgent(agentId: string, data: any) {
  const res = await fetch(`${IGOSA_API}/api/agents/${agentId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}
```

### Step 4: Dashboard Pages to Build

1. **Overview** — Stats cards (active listings, pipeline value, leads, commission)
2. **Properties** — Listing grid with status filters, add/edit
3. **Pipeline** — Kanban board (lead → viewing → offer → closed)
4. **Leads** — Lead table with scores, filters, activity timeline
5. **Conversations** — WhatsApp chat log viewer
6. **Settings** — Agent profile, areas, subscription

---

## Part 4: Data Flow

```
1. WhatsApp message arrives
   ↓
2. Evolution API → webhook → iGosa API (Render)
   ↓
3. iGosa processes: intent → AI response → send back via WhatsApp
   ↓
4. iGosa stores structured data in Supabase
   ↓
5. Lovable dashboard reads from Supabase (realtime subscriptions)
   ↓
6. Business owner sees live dashboard updates
```

### Supabase Realtime
Lovable supports Supabase realtime natively. When a new lead comes in or a deal moves to "accepted", the dashboard updates instantly.

```sql
-- Enable realtime on key tables
ALTER PUBLICATION supabase_realtime ADD TABLE leads;
ALTER PUBLICATION supabase_realtime ADD TABLE deals;
ALTER PUBLICATION supabase_realtime ADD TABLE conversations;
```

---

## Part 5: Evolution API Reference (Already Deployed)

```
URL:      https://bankbook-whatsapp-my-evolution-api.onrender.com
Version:  2.3.7
Instance: realestate
State:    open (WhatsApp connected ✅)
Token:    B01B10DDEA28-4A7A-89D2-47F609E7FD87
```

### Webhook (already configured)
```
POST https://igosa.onrender.com/webhook/evolution
Events: MESSAGES_UPSERT
```

### Update webhook after Render deploy:
```bash
curl -X POST "https://bankbook-whatsapp-my-evolution-api.onrender.com/webhook/set/realestate" \
  -H "apikey: B01B10DDEA28-4A7A-89D2-47F609E7FD87" \
  -H "Content-Type: application/json" \
  -d '{"webhook":{"enabled":true,"url":"https://YOUR-RENDER-URL.onrender.com/webhook/evolution","events":["MESSAGES_UPSERT"],"webhookByEvents":false}}'
```

---

## Quick Start Checklist

- [ ] Create Supabase project + run schema SQL
- [ ] Create Lovable project + connect Supabase
- [ ] Deploy iGosa to Render (or give me GitHub access to push)
- [ ] Update Evolution webhook to iGosa Render URL
- [ ] Create agent via `POST /api/agents` 
- [ ] Build dashboard pages in Lovable
- [ ] Test: send WhatsApp message → see lead appear in dashboard
