# iGosa — Evolution API Setup Guide
## Connecting Your Evolution API Instance to iGosa

### Current Status

| Item | Value |
|------|-------|
| Evolution API URL | `https://bankbook-whatsapp-my-evolution-api.onrender.com` |
| Evolution Version | `2.3.7` ✅ |
| Instance Name | `realestate` |
| Global API Key | `BankBook_Secret_99` |
| Instance Token | `igosa_realestate_2026` (needs verification) |

### Step 1: Verify Instance Token

The global API key (`BankBook_Secret_99`) is for manager operations (create/delete instances).
**Instance operations** (send messages, connect WhatsApp, set webhooks) use the **instance token**.

Find your instance token:
1. Open your Evolution API dashboard: `https://bankbook-whatsapp-my-evolution-api.onrender.com/manager`
2. Find the "realestate" instance
3. Note the instance token/key

Or test via API:
```bash
# Try different tokens with the connect endpoint
curl "https://bankbook-whatsapp-my-evolution-api.onrender.com/instance/connect/realestate" \
  -H "apikey: YOUR_INSTANCE_TOKEN"
```

### Step 2: Connect WhatsApp

Once you have the correct instance token:
```bash
curl "https://bankbook-whatsapp-my-evolution-api.onrender.com/instance/connect/realestate" \
  -H "apikey: YOUR_INSTANCE_TOKEN"
```

This returns a QR code. Scan it with WhatsApp on your phone (Linked Devices).

### Step 3: Set Webhook

After WhatsApp is connected, point the webhook at iGosa:
```bash
curl -X POST "https://bankbook-whatsapp-my-evolution-api.onrender.com/webhook/set/realestate" \
  -H "apikey: YOUR_INSTANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "url": "https://igosa.onrender.com/webhook/evolution",
    "events": ["MESSAGES_UPSERT"],
    "webhook_by_events": false
  }'
```

### Step 4: Update .env

After finding the correct instance token, update `.env`:
```bash
EVOLUTION_INSTANCE_TOKEN=YOUR_ACTUAL_INSTANCE_TOKEN
```

### Step 5: Deploy

1. Push to GitHub
2. Connect repo to Render
3. Set environment variables in Render dashboard
4. Deploy!

### Troubleshooting

| Error | Likely Cause |
|-------|-------------|
| `401 Unauthorized` on instance endpoints | Wrong instance token in `apikey` header |
| `401 Unauthorized` on create/delete | Wrong global API key |
| `404 instance does not exist` | Instance name doesn't match |
| `403 name already in use` | Instance already exists (normal) |
| WhatsApp not receiving messages | QR not scanned; webhook not set |
