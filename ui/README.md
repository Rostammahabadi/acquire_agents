# Acquire Agents UI

A minimal internal control surface for the automated SaaS acquisition pipeline.

## Overview

This Next.js application provides a simple interface for operators to:

- View all businesses in the acquisition pipeline
- Monitor pipeline status for each business
- Manually trigger agent runs (canonicalization, scoring, follow-up generation)
- Inspect outputs at each stage of the pipeline
- Manage seller responses to follow-up questions

## Features

### Businesses List (`/businesses`)

- Table view of all businesses with key metrics
- Pipeline status indicators (scraped, canonicalized, scored, follow-ups, awaiting response)
- Quick access to detailed business views

### Business Detail (`/businesses/[business_id]`)

Four main sections stacked vertically:

1. **Raw Listing**: View scraped data with manual re-run option
2. **Canonical Record**: JSON view of structured business data with re-run option
3. **Scoring**: Component scores, tier, buy reasons, and risks with conditional follow-up trigger
4. **Follow-up Questions**: Question management with response collection

## Tech Stack

- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **Tailwind CSS** (minimal utility classes)
- **Server Actions** for backend integration

## API Integration

### Frontend API (Next.js)

The UI provides these endpoints:

```
GET    /api/businesses              # List all businesses from database
GET    /api/businesses/[id]         # Get business details from database
POST   /api/run/canonicalize        # Trigger canonicalization via backend
POST   /api/run/score               # Trigger scoring via backend
POST   /api/run/follow-ups          # Trigger follow-up generation via backend
POST   /api/follow-ups/respond      # Save seller response to database
```

### Backend Integration

The UI connects to the Python/LangGraph backend running on `http://localhost:8000`:

- **Authentication**: Uses demo token endpoint `/int-agent-mvp/api/v1/auth/demo-token`
- **Canonicalization**: Calls `/api/run/canonicalize` with business_id
- **Scoring**: Calls `/api/run/score` with business_id
- **Follow-ups**: Calls `/api/run/follow-ups` with business_id

All trigger buttons now make real HTTP calls to the Python backend using LangGraph workflows with OpenAI GPT models.

## Development

```bash
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

## Design Principles

- **No authentication**: Single operator use case
- **No styling beyond basic layout**: Control surface, not product
- **Manual control only**: No auto-triggering or polling
- **Inspectable and debuggable**: Clear status indicators and error handling
- **Minimal abstractions**: Direct API calls, simple components
