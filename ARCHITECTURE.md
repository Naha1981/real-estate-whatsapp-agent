# iGosa — Full System Architecture v2.0
## Multi-Repo Integration Design

---

## The Complete Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     WHATSAPP (User-Facing)                    │
│                   Evolution API (Self-Hosted)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    iGOSA — Core Platform                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Webhook      │  │ Orchestrator │  │ FollowUp Scheduler│  │
│  │ Handler      │  │ (14 intents) │  │ (6 sequences)     │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘  │
│         │                 │                                   │
│  ┌──────┴─────────────────┴──────────────────────────────┐  │
│  │              AGENT SKILLS LAYER                         │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ Adapted from HyperAgent Public Skills format      │  │  │
│  │  │ 4 SA-specific skill files:                        │  │  │
│  │  │  • Buyer Conversation Agent                       │  │  │
│  │  │  • Lead Qualifier & Scorer                        │  │  │
│  │  │  • Structured Output Generator                    │  │  │
│  │  │  • Agent Behavior Templates (5 personas)          │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │               AI ENGINE (OpenAI GPT-4o-mini)            │  │
│  │  Intent Classifier │ Responder │ Entity Extractor       │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   SUPABASE   │  │  EVOMEM      │  │   HORIZON    │
│  (Database)  │  │  (Memory)    │  │ (Intelligence)│
├──────────────┤  ├──────────────┤  ├──────────────┤
│ • PostgreSQL │  │ • Long-term  │  │ • Market      │
│ • PostGIS    │  │   agent      │  │   monitoring  │
│ • Auth       │  │   memory     │  │ • Price drop  │
│ • Storage    │  │ • Session    │  │   detection   │
│ • Realtime   │  │   continuity │  │ • Lead        │
│              │  │ • Preference │  │   discovery   │
│              │  │   recall     │  │ • Daily       │
│              │  │ • Cross-     │  │   briefings   │
│              │  │   session    │  │               │
│              │  │   context    │  │               │
└──────┬───────┘  └──────┬───────┘  └──────┬────────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │   MAP3D (Premium)  │
              │  • 3D neighborhood │
              │  • Estate context   │
              │  • Luxury tours     │
              │  • GLB exports      │
              └────────────────────┘
```

---

## Component Integration Details

### 1. HyperAgent Public Skills → iGosa Skills Layer ✅ VERIFIED

**Status:** Fully compatible and adapted.

The HyperAgent skills format uses JSON with a `data.skillMdBody` containing markdown system prompts, workflows, tool references, and output schemas. We've created 4 SA-real-estate-specific skills following the same format:

| iGosa Skill | Purpose | HyperAgent Pattern Used |
|------------|---------|------------------------|
| `skill-sa-buyer-conversation.json` | WhatsApp conversation handler for buyers | System prompt + workflow steps + examples |
| `skill-sa-lead-qualifier.json` | Lead scoring + ranking | Scoring dimensions + output templates |
| `skill-sa-structured-outputs.json` | 6 WhatsApp output formats | Structured template definitions |
| `skill-sa-agent-behaviors.json` | 5 agent personas | Persona definitions + tone + workflow |

**How it works in iGosa:**
- `SkillsLoader` loads all `skill-*.json` files from `/skills/`
- `build_agent_system_prompt(role)` combines relevant skills into a composite system prompt
- The AI engine uses this as context when generating responses
- Skills can be updated without code changes — just edit the JSON

**Verification:** The HyperAgent repo (943 stars) contains 14 skills in this exact format. Our 4 skills follow the identical structure: `{version, type, exportedAt, data: {name, description, tags, whenToUse, skillMdBody}}`.

---

### 2. EvoMem → iGosa Memory Layer

**Status:** Planned integration.

EvoMem (Rust-based, knowledge infrastructure for AI agents) provides:
- Long-term conversational memory
- Session continuity across days/weeks
- Preference and context recall
- Cross-agent shared memory

**Integration Plan:**
```
WhatsApp Message → iGosa Webhook → Orchestrator
                                         │
                          ┌──────────────┤
                          ▼              ▼
                    EvoMem Query    Intent Handler
                    "What does      (uses EvoMem
                     this user       context to
                     want/need?"    personalize)
                          │              │
                          └──────┬───────┘
                                 ▼
                          AI Response
                          + Store in EvoMem
```

**Key use cases in iGosa:**
- User returns after 2 weeks → agent remembers their budget, area, preferences
- Lead was cold → agent recalls last conversation context
- User rejected 5 apartments → agent stops recommending apartments
- Multi-agent: buyer agent + viewing agent share same user memory

---

### 3. Horizon → iGosa Intelligence Layer

**Status:** Planned integration.

Horizon (7,262 stars, Python) provides:
- Multi-source monitoring (RSS, Reddit, Telegram, social feeds)
- AI scoring, deduplication, enrichment
- Daily briefing generation
- Webhook delivery

**Integration Plan for SA Real Estate:**
```
Horizon monitors:
├── Property24 RSS feeds (new listings, price changes)
├── Private Property alerts
├── Facebook Marketplace property groups
├── Municipal development announcements (CoJ)
├── SARB interest rate announcements
└── Estate agency social media

         ↓ Daily Briefing (JSON via Webhook)

iGosa receives → Stores in Supabase → WhatsApp alerts to agents

Agent gets morning message:
"📊 Morning Briefing:
• 12 new listings in Soweto (avg R420K)
• 3 price drops in Pimville (avg -R45K)
• SARB held rates at 11.5%
• New development approved in Diepkloof"
```

**Custom Sources to Configure in Horizon:**
- Property24 category pages (scrape or RSS)
- Facebook group RSS bridges
- Municipal planning portals
- SA Reserve Bank announcements
- Estate agency competitor feeds

---

### 4. Map3D → iGosa Premium Visual Layer

**Status:** Future enhancement (luxury tier).

Map3D (React-Three-Fiber, 3D building mapping) provides:
- 3D neighborhood visualization from OpenStreetMap data
- Building context, roads, terrain
- GLB file exports
- Interactive 3D scenes

**Integration Plan:**
```
Luxury buyer asks about a property
         ↓
iGosa qualifies lead + finds match
         ↓
Generates Map3D scene:
├── Property location marker
├── Surrounding buildings
├── Nearby schools, malls, hospitals
├── Main roads and access routes
└── Estate boundaries
         ↓
Sends WhatsApp message:
"🏠 I've prepared a 3D view of the neighborhood:
🔗 [MAP3D_LINK]
You can see schools, shops, and access routes."
```

**When to use Map3D:**
- Luxury listings (R1.5M+) — adds perceived value
- New developments — visualize the area before construction
- Investment properties — show growth corridors
- Estate living — show security boundaries and amenities
- NOT for: Township RDP listings (R200K–R500K) — overkill

---

### 5. Supabase + PostGIS → Data Layer

**Status:** Planned migration from SQLite.

Supabase provides:
- Hosted PostgreSQL with PostGIS extension
- Spatial queries for property matching
- Authentication + Row Level Security
- Realtime subscriptions
- Storage for property photos and documents
- Admin dashboard

**Spatial Queries iGosa will use:**
```sql
-- Find properties within 3km of a school
SELECT * FROM listings 
WHERE ST_DWithin(location, school_location, 3000)
AND price BETWEEN 400000 AND 600000;

-- Find properties in a specific estate boundary
SELECT * FROM listings 
WHERE ST_Within(location, estate_boundary);

-- Find nearest amenities to a listing
SELECT name, ST_Distance(location, listing_location) as dist
FROM amenities
WHERE ST_DWithin(location, listing_location, 5000)
ORDER BY dist LIMIT 5;
```

---

## Implementation Phases

### Phase 1: Current (Built) ✅
- [x] iGosa core platform (26 Python files, 14 services)
- [x] WhatsApp webhook + Evolution API integration
- [x] Intent classifier (14 intents, 100% fallback accuracy)
- [x] 4 SA-specific skill files (HyperAgent format)
- [x] SkillsLoader with composite prompt builder
- [x] Web dashboard

### Phase 2: Deploy & Test (Next)
- [ ] Deploy to Render with Evolution API
- [ ] Pilot with 5-10 Soweto agents
- [ ] Iterate on skill prompts based on real conversations
- [ ] Add voice note transcription (Whisper)

### Phase 3: Memory Layer (EvoMem) — Month 2
- [ ] Deploy EvoMem instance
- [ ] Integrate with iGosa orchestrator
- [ ] Test cross-session memory recall
- [ ] Implement lead preference storage

### Phase 4: Intelligence Layer (Horizon) — Month 3
- [ ] Configure Horizon for SA property sources
- [ ] Build Property24 + Facebook scraping
- [ ] Daily briefing pipeline → Supabase → WhatsApp
- [ ] Price drop + new listing alerts

### Phase 5: Spatial + Visual (Supabase/PostGIS + Map3D) — Month 4-5
- [ ] Migrate from SQLite to Supabase PostgreSQL
- [ ] Enable PostGIS + spatial indexes
- [ ] Build spatial query layer for property matching
- [ ] Integrate Map3D for luxury tier
- [ ] 3D neighborhood preview for premium listings

---

## Cost Projections

| Component | Monthly Cost (Est.) |
|-----------|---------------------|
| Render (iGosa API) | $0 (free tier) |
| Evolution API hosting | $0 (self-hosted) |
| OpenAI API (GPT-4o-mini) | $20–$100 |
| Supabase | $0–$25 (free tier → pro) |
| EvoMem hosting | $0 (self-hosted) |
| Horizon hosting | $0 (self-hosted or free tier) |
| Map3D hosting | $0 (static hosting) |
| **Total Monthly** | **$20–$125** |

---

*Architecture v2.0 — June 2026*
