# CO₂ Retention Simulator

FastAPI backend application with web UI for estimating CO₂ removal through enhanced rock weathering.

## Project Structure

```
/
├── app/                          # Backend application
│   ├── services/                 # Business logic
│   │   ├── ingestion_service.py
│   │   ├── model_state_service.py
│   │   ├── simulation_service.py
│   │   ├── results_service.py
│   │   └── config_service.py
│   ├── models/                   # Database models
│   ├── routes/                   # API endpoints
│   ├── constants.py              # Application constants
│   └── main.py                   # Application entry point
├── static/                       # Frontend files
│   └── index.html                # Web UI (single-page application)
├── docs/                         # Documentation
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── BUILD_INSTRUCTIONS.md
│   └── CODE_REVIEW_*.md
├── builds/                       # Compiled executables
│   └── windows/
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container image definition
├── requirements.txt              # Python dependencies
└── start_embedded.py             # Standalone launcher (Windows .exe)
```

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker Compose

1. Start the services:
```bash
docker-compose up -d
```

2. The API will be available at `http://localhost:8000`
3. **Web UI** will be available at `http://localhost:8000/ui`
4. API documentation will be available at `http://localhost:8000/docs`

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start PostgreSQL (using Docker):
```bash
docker-compose up -d db
```

3. Set environment variables:
```bash
cp .env.example .env
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## Web UI

Access the interactive web interface at `http://localhost:8000/ui` to:
- Create configurations
- Ingest lab and field data
- Update model state
- Run simulations
- View results

## API Endpoints

### Main Routes (Root Level)
- `POST /config` - Create configuration
- `GET /config/{config_id}` - Get configuration
- `PUT /config/{config_id}` - Update configuration
- `POST /lab-data/ingest` - Ingest lab data
- `POST /field-data/ingest` - Ingest field data
- `POST /model/update-state` - Update model state
- `POST /simulate` - Run simulation
- `GET /results/{config_id}` - Get results summary

### Legacy API v1 Routes
- `/api/v1/ingestion` - Data ingestion endpoints
- `/api/v1/model-state` - Model state management
- `/api/v1/simulation` - Simulation operations
- `/api/v1/results` - Results management
- `/api/v1/config` - Configuration management

## Database

PostgreSQL database is configured via Docker Compose. Default credentials:
- User: `mining_user`
- Password: `mining_password`
- Database: `mining_db`
- Port: `5432`

## Documentation

All project documentation is located in the `/docs` directory:

- **[TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)** - Detailed technical rationale, model explanation, and scientific methodology
- **[BUILD_INSTRUCTIONS.md](docs/BUILD_INSTRUCTIONS.md)** - Instructions for building the Windows executable
- **[CODE_REVIEW_SUMMARY.md](docs/CODE_REVIEW_SUMMARY.md)** - Code review findings and testing checklist
- **[CODE_REVIEW_ISSUES.md](docs/CODE_REVIEW_ISSUES.md)** - Detailed list of identified issues
- **[FIXES_APPLIED.md](docs/FIXES_APPLIED.md)** - Documentation of applied fixes
- **[ISSUES_FOUND.md](docs/ISSUES_FOUND.md)** - Historical issue tracking
