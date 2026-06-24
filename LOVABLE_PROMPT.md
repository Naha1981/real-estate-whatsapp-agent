# iGosa Dashboard — Lovable.dev Prompt

Copy everything below and paste into Lovable.dev as your project prompt.

---

Build a real estate business owner dashboard for "iGosa" — a WhatsApp AI agent platform for South African estate agents.

## BACKEND API (already deployed)
Base URL: https://real-estate-whatsapp-agent.onrender.com

Endpoints:
- GET /api/dashboard/{agent_id} — Full dashboard data
- GET /api/agents/{agent_id} — Agent profile
- PUT /api/agents/{agent_id} — Update agent settings
- GET /api/tasks/pending/{agent_id} — Pending follow-ups
- POST /api/agents — Register new agent

## DATABASE (Supabase — native integration)
Connect to Supabase and create these tables:

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    whatsapp_number VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(200),
    logo_url TEXT,
    areas TEXT[],
    subscription_tier VARCHAR(20) DEFAULT 'starter',
    subscription_status VARCHAR(20) DEFAULT 'active',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

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
    photos TEXT[],
    features TEXT[],
    rdp_restricted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    whatsapp_number VARCHAR(20) NOT NULL,
    display_name VARCHAR(100),
    lead_type VARCHAR(20),
    lead_status VARCHAR(20) DEFAULT 'new',
    qualification_score INT,
    budget_min DECIMAL,
    budget_max DECIMAL,
    preferred_areas TEXT[],
    preferred_type VARCHAR(30),
    pre_approved BOOLEAN DEFAULT false,
    lead_source VARCHAR(30),
    last_contacted TIMESTAMPTZ,
    next_follow_up TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    listing_id UUID REFERENCES listings(id),
    lead_id UUID REFERENCES leads(id),
    deal_type VARCHAR(20) DEFAULT 'sale',
    deal_value DECIMAL,
    commission_estimate DECIMAL,
    deal_stage VARCHAR(30) DEFAULT 'lead',
    offer_amount DECIMAL,
    bond_status VARCHAR(30),
    estimated_close_date DATE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    lead_id UUID REFERENCES leads(id),
    direction VARCHAR(10),
    message_text TEXT,
    intent_classified VARCHAR(30),
    ai_responded BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable realtime for live updates
ALTER PUBLICATION supabase_realtime ADD TABLE leads;
ALTER PUBLICATION supabase_realtime ADD TABLE deals;
ALTER PUBLICATION supabase_realtime ADD TABLE conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE listings;
```

## PAGES TO BUILD

### 1. Overview Dashboard (/)
Stats cards at top showing:
- Active Listings (count)
- Pipeline Value (Rands)
- Hot Leads (count)
- Commission This Month (Rands)
- Pending Follow-ups (count)
- Rental Collection Rate (%)

Below stats: Recent activity feed from conversations table, and a mini pipeline chart.

### 2. Properties Page (/properties)
- Grid or table of all listings with status badges (Active 🟢, Under Offer 🟡, Sold 🔴, Rented 🔵)
- Filter by status, suburb, property type, price range
- Click a property to see detail card
- Add Property button (form: title, bedrooms, bathrooms, price, suburb, type, description, features)

### 3. Pipeline Kanban (/pipeline)
- Kanban board with columns: Lead → Viewing → Offer → Negotiation → Accepted → Bond Pending → Closed
- Drag deals between columns to update stage
- Each card shows: lead name, property, deal value, days in stage
- Total pipeline value and estimated commission at top
- Color-code cards by age (red if in stage >7 days, yellow >3 days)

### 4. Leads Page (/leads)
- Table with columns: Name, Phone, Type, Score, Status, Area, Budget, Last Contact
- Sort by score (highest first), filter by status/type
- Lead detail panel showing conversation history
- Hot/Warm/Cold color coding based on score
- Quick actions: Message, Schedule Follow-up, Create Deal

### 5. Conversations Page (/conversations)
- Chat-like interface showing WhatsApp conversations
- Left sidebar: list of leads with last message preview
- Right panel: conversation thread with inbound/outbound bubbles
- Show AI responses with 🤖 icon, human messages with 👤 icon

### 6. Settings Page (/settings)
- Agent profile: name, business name, phone number, logo
- Areas served (multi-select: Soweto, Pimville, Diepkloof, etc.)
- Property types handled
- Subscription tier display
- Save button

## API CLIENT SETUP
Create an API client file:

```typescript
const API_BASE = "https://real-estate-whatsapp-agent.onrender.com";

export async function fetchDashboard(agentId: string) {
  const res = await fetch(`${API_BASE}/api/dashboard/${agentId}`);
  return res.json();
}

export async function fetchAgent(agentId: string) {
  const res = await fetch(`${API_BASE}/api/agents/${agentId}`);
  return res.json();
}

export async function updateAgent(agentId: string, data: any) {
  const res = await fetch(`${API_BASE}/api/agents/${agentId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchPendingTasks(agentId: string) {
  const res = await fetch(`${API_BASE}/api/tasks/pending/${agentId}`);
  return res.json();
}
```

## DESIGN SYSTEM
- Colors: Primary #128C7E (WhatsApp green), Dark #075E54, Background #F0F2F5
- Font: Inter or system sans-serif
- Cards: White background, 10px border radius, subtle shadow
- Mobile responsive — agents use this on phones too
- Use Lucide icons
- Toast notifications for success/error

## KEY BEHAVIORS
- On first load, show a setup wizard if no agent exists (POST /api/agents)
- Use Supabase realtime subscriptions so pipeline, leads, and conversations update live
- Cache API responses in Supabase for offline resilience
- Use the demo agent ID "demo" for testing if no real agent configured
- Show loading skeletons while fetching data
- Handle Render cold starts gracefully (show "Waking up server..." with retry)

## DEMO MODE
If no agent ID is configured, show a demo dashboard with sample data so the UI can be previewed. Add a banner: "Connect your agent to see live data".
