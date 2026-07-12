# GoHighLevel connection (Frontline sub-account)

This repo registers GoHighLevel's official MCP server in `.mcp.json`, giving
Claude Code sessions access to the Frontline sub-account (contacts,
conversations, calendars, opportunities) once two things are configured.
No secrets are committed — the config reads them from environment variables.

## One-time setup

### 1. Environment variables

In your Claude Code environment settings (claude.ai/code → your environment →
environment variables), add:

| Variable | Value |
|---|---|
| `GHL_PIT` | Private Integration Token from the sub-account (Settings → Private Integrations, starts with `pit-`) |
| `GHL_LOCATION_ID` | The sub-account's Location ID (Settings → Business Profile) |

### 2. Network policy

The environment's network policy must allow outbound HTTPS to:

- `services.leadconnectorhq.com` (GoHighLevel API + MCP server)

Without this, sessions get a proxy 403 when contacting GoHighLevel.

## Verifying

In a new session, ask Claude to list GoHighLevel tools or fetch the location:

```
curl -sS \
  -H "Authorization: Bearer $GHL_PIT" \
  -H "Version: 2021-07-28" \
  "https://services.leadconnectorhq.com/locations/$GHL_LOCATION_ID"
```

A JSON payload with the location name confirms the connection.

## Token hygiene

- Scope the Private Integration Token to only the permissions you need.
- Rotate it in GoHighLevel (Settings → Private Integrations) if it is ever
  exposed; update `GHL_PIT` afterward.
