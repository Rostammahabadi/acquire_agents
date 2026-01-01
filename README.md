# Acquire Agents

An AI-powered business acquisition platform that automates the discovery, analysis, and evaluation of SaaS and online businesses for acquisition opportunities.

## Overview

This system scrapes business listings from marketplaces like Acquire.com and Flippa, then uses a comprehensive LangGraph workflow with specialized AI agents to:

- **Categorize** business data into structured canonical records using deterministic extraction
- **Score** businesses with multi-dimensional component analysis and weighted total scoring
- **Generate** targeted follow-up questions only for high-potential businesses (A/B tier, ≥70 score)
- **Track** the entire analysis pipeline with immutable audit trails

The platform uses LangGraph for orchestrating AI agent workflows, PostgreSQL for structured data storage, and Pydantic for schema validation.

## Architecture

### Data Flow

```
Marketplace Scraping → Raw Data Storage → Categorization Node → Canonical Records → Scoring Node → Scoring Records → Follow-up Node → Questions
```

### LangGraph Workflow

The system implements a deterministic LangGraph workflow with three sequential nodes:

1. **`categorize_listing`**: Extracts structured canonical data from raw HTML/text
2. **`score_business`**: Evaluates acquisition potential with component scoring
3. **`generate_follow_up_questions`**: Generates targeted questions (gated by A/B tier + ≥70 score)

### Core Components

#### 1. Data Ingestion (`raw_listings` table)

- Append-only storage of scraped business listings
- Preserves verbatim marketplace data without interpretation
- Supports multiple scrapes per business over time

#### 2. Categorization Node (`canonical_business_records` table)

- Uses GPT-4o-mini with structured output to extract 9 business domains
- Implements content-hash-based versioning for immutable updates
- Domains: financials, product, customers, operations, technology, growth, risks, seller, confidence_flags
- Validates output against comprehensive Pydantic schemas

#### 3. Scoring Node (`scoring_records` table)

- Evaluates 7 component scores (0-100 scale): price efficiency, revenue quality, moat, AI leverage, operations, risk, trust
- Applies deterministic weighted calculation (20/15/20/15/10/10/10 weights)
- Generates tier rankings (A: ≥85, B: 70-84, C: 55-69, D: <55)
- Penalizes data quality issues (missing financials, assumptions, contradictions)

#### 4. Follow-up Node (`follow_up_questions` table)

- **Gated execution**: Only runs for A/B tier businesses with total_score ≥ 70
- Analyzes confidence flags and missing domains for decision-blocking uncertainties
- Generates ≤8 targeted questions tied to specific fields with severity mapping
- Priorities: critical (IP, financials) → high (churn, dependencies) → medium (operations) → low (details)

#### 5. Monitoring (`agent_execution_logs` table)

- Tracks agent performance, success rates, and execution times
- Enables debugging and optimization of AI workflows

## Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Docker & Docker Compose
- OpenAI API key (for GPT-4o-mini LLM integration)

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd acquire_agents
   ```

2. **Create virtual environment**

   ```bash
   python -m venv langgraph_env
   source langgraph_env/bin/activate  # On Windows: langgraph_env\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Start PostgreSQL database**

   ```bash
   docker-compose up -d postgres
   ```

5. **Initialize database**

   ```bash
   python init_db.py
   ```

6. **Set up environment variables**

   Create a `.env` file with your OpenAI API key:

   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   DATABASE_URL=postgresql://acquire_user:acquire_pass@localhost:5432/acquire_agents
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://acquire_user:acquire_pass@localhost:5432/acquire_agents

# OpenAI API Configuration (required for LangGraph workflows)
OPENAI_API_KEY=your_openai_api_key_here
```

### UI Setup

The project includes a Next.js control surface for managing the acquisition pipeline:

```bash
cd ui
npm install
npm run dev
```

The UI will be available at `http://localhost:3000` and connects to both the database and the Python backend for real-time pipeline control.

### Database Schema

The system uses PostgreSQL with the following key tables:

- `raw_listings` - Raw scraped business data
- `canonical_business_records` - AI-categorized structured business facts
- `scoring_records` - Acquisition scoring and analysis
- `follow_up_questions` - Auto-generated seller questions
- `agent_execution_logs` - AI agent execution tracking

## Usage

### Option 1: Command Line Workflow

Run the full LangGraph workflow for business acquisition analysis:

```bash
python categorization_workflow.py
```

This executes the complete pipeline:

1. **Categorization**: Extracts canonical business data from raw listings
2. **Scoring**: Evaluates acquisition potential with component analysis
3. **Follow-up**: Generates targeted questions (only for A/B tier businesses ≥70 score)

### Option 2: Web Interface (Recommended)

Start the full web application with control interface:

1. **Start the backend API server**:

   ```bash
   python main.py
   ```

   The API server will run on `http://localhost:8000`

2. **Start the UI** (in a separate terminal):

   ```bash
   cd ui && npm run dev
   ```

   The UI will run on `http://localhost:3000`

3. **Access the control interface**:
   Open `http://localhost:3000` in your browser to access the business pipeline control interface.

The web interface provides:

- **Business Pipeline Overview**: View all scraped businesses and their processing status
- **Manual Workflow Control**: Trigger canonicalization, scoring, and follow-up generation on demand
- **Detailed Business View**: Inspect raw data, canonical records, scoring results, and follow-up questions
- **Response Management**: Save seller responses to follow-up questions

### Database Operations

#### Initialize with sample data:

```bash
python init_db.py --sample
```

#### Connect to database programmatically:

```python
from database import get_session_sync

session = get_session_sync()
# Use session for database operations
```

### LangGraph Workflow Integration

The platform implements a deterministic LangGraph workflow with three specialized nodes:

1. **`categorize_listing`**: GPT-4o-mini powered extraction into 9 structured domains with content-hash versioning
2. **`score_business`**: Multi-dimensional scoring (7 components) with weighted total calculation and tier mapping
3. **`generate_follow_up_questions`**: Targeted question generation with severity-based prioritization (gated execution)

## API Models

### Business Listing Response

```python
{
    "business_id": "uuid",
    "marketplace": "acquire.com",
    "listing_url": "https://...",
    "latest_scrape": "2024-01-01T00:00:00Z",
    "canonical_data": {...},
    "latest_score": {...},
    "requires_followup": true,
    "created_at": "2024-01-01T00:00:00Z"
}
```

### Scoring Response

```python
{
    "record_id": "uuid",
    "component_scores": {
        "price_efficiency_score": 90.0,
        "revenue_quality_score": 85.0,
        "moat_score": 80.0,
        "ai_leverage_score": 88.0,
        "operations_score": 82.0,
        "risk_score": 75.0,
        "trust_score": 95.0
    },
    "top_buy_reasons": ["Strong recurring revenue", "Growing market"],
    "top_risks": ["Single customer concentration", "Technical debt"],
    "total_score": 82.45,
    "tier": "B"
}
```

### Follow-up Questions Response

```python
{
    "questions": [
        {
            "id": "uuid",
            "question_text": "Can you provide detailed financial statements for the past 12-24 months, including revenue, expenses, and profit/loss?",
            "triggered_by_field": "financials.missing_financial_data",
            "severity": "critical"
        },
        {
            "id": "uuid",
            "question_text": "What are the primary customer acquisition channels and recent growth trends?",
            "triggered_by_field": "growth.missing",
            "severity": "high"
        }
    ],
    "count": 2
}
```

## Development

### Database Migrations

The project uses SQLAlchemy with Alembic for database migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "Add new feature"

# Apply migration
alembic upgrade head
```

### Testing

Add sample data for development:

```bash
python init_db.py --sample
```

### Project Structure

```
acquire_agents/
├── models.py                    # SQLModel database models and Pydantic schemas
├── database.py                  # Database configuration and utilities
├── categorization_workflow.py   # Complete LangGraph acquisition workflow
├── init_db.py                  # Database initialization script
├── hello_langgraph.py          # Basic LangGraph example
├── schema.sql                  # PostgreSQL schema definition
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Docker services
└── langgraph_env/              # Python virtual environment
```

### Key Files

- **`categorization_workflow.py`**: Main LangGraph implementation with three nodes
  - `categorize_listing`: GPT-4o-mini powered canonical data extraction
  - `score_business`: Multi-dimensional scoring with weighted calculation
  - `generate_follow_up_questions`: Gated question generation for high-potential businesses

## Data Domains & Scoring Components

### Canonical Data Domains (Categorization)

#### Financials

- Asking price, monthly/annual revenue, profit metrics
- Revenue growth rates, profit margins
- Financial health indicators and valuation signals

#### Product

- Business type, vertical, product category
- Core features, target market, business model
- Competitive positioning and market fit

#### Customers

- Total/paying customer counts, monthly active users
- Churn rates, customer concentration risk
- Customer segments and retention metrics

#### Operations

- Owner hours per week, full/part-time employees
- Key dependencies, scalability factors
- Key person risk and operational efficiency

#### Technology

- Tech stack, hosting provider, code ownership
- API dependencies, data storage solutions
- Development status and technical documentation

#### Growth

- Growth channels, monthly growth rates
- Customer acquisition cost, lifetime value
- Marketing spend effectiveness and growth trends

#### Risks

- Platform dependencies, regulatory risks
- Competitive threats, technical debt
- IP ownership and market risk factors

#### Seller

- Geographic location, selling motivations
- Post-sale involvement preferences
- Business age, transition support availability

#### Confidence Flags

- Missing financial data, assumed values
- Contradictory information, follow-up requirements
- Data quality scores and uncertainty indicators

### Scoring Components (0-100 Scale)

#### Price Efficiency (20% weight)

- Valuation relative to revenue/profit quality
- Market comparables and pricing rationality
- Asking price justification and negotiation potential

#### Revenue Quality (15% weight)

- Revenue stability, predictability, and growth trends
- Contract quality and customer retention factors
- Recurring revenue concentration and diversification

#### Competitive Moat (20% weight)

- Network effects, proprietary technology
- Switching costs, brand strength
- Market position and defensibility factors

#### AI Leverage (15% weight)

- Automation potential, data-rich processes
- ML/AI integration opportunities
- Operational efficiency through technology

#### Operations (10% weight)

- Scalability, process documentation
- Owner dependency reduction potential
- Operational maturity and efficiency metrics

#### Risk Assessment (10% weight)

- Platform dependencies, regulatory exposure
- Customer concentration, competitive threats
- Overall risk mitigation and insurance factors

#### Trust Score (10% weight)

- Data quality, verification confidence
- Assumption levels, contradictory information
- Transparency and disclosure quality

### Scoring Calculation

**Total Score** = (Price Efficiency × 0.20) + (Revenue Quality × 0.15) + (Moat × 0.20) + (AI Leverage × 0.15) + (Operations × 0.10) + (Risk × 0.10) + (Trust × 0.10)

**Tier Mapping**:

- **A**: ≥85 (Excellent acquisition target)
- **B**: 70-84.99 (Strong candidate)
- **C**: 55-69.99 (Moderate potential)
- **D**: <55 (High risk/reject)

### Follow-up Question Severity

- **Critical**: IP ownership, unverifiable financials, revenue ownership uncertainty
- **High**: Unknown churn rates, customer concentration, platform dependencies
- **Medium**: Unclear owner hours, support burden, operational details
- **Low**: Minor tooling preferences, administrative details

## Contributing

1. Follow the existing code structure and naming conventions
2. Add comprehensive docstrings to new functions and classes
3. Include type hints for all function parameters and return values
4. Test database operations thoroughly
5. Update this README for any new features or configuration changes

## License

[Add your license information here]
