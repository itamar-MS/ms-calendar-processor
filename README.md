# Calendar Extractor

A Python application for extracting calendar events, generating instructor reports, and syncing with external services like Base44 and HubSpot.

## 🏗️ Project Structure

```
calendar_extractor/
├── src/                          # Source code
│   ├── core/                     # Core application logic
│   │   ├── main.py              # Main entry point
│   │   └── config.py            # Configuration management
│   ├── data/                     # Data handling
│   │   ├── database/            # Database operations
│   │   └── parsers/             # Data parsing utilities
│   ├── services/                 # External service integrations
│   │   ├── base44_service.py    # Base44 API integration
│   │   ├── hubspot_service.py   # HubSpot API integration
│   │   └── s3_service.py        # AWS S3 operations
│   ├── reports/                  # Report generation
│   │   ├── generators.py        # Report generation logic
│   │   └── handlers.py          # Report output handlers
│   └── utils/                    # Utility functions
│       ├── calendar_utils.py    # Calendar-specific utilities
│       └── helpers.py           # General utilities
├── data/                         # Data files
│   ├── raw/                     # Raw data files
│   └── processed/               # Processed data (auto-generated)
├── output/                       # Generated reports and outputs
├── tests/                        # Test files
├── docs/                         # Documentation
├── scripts/                      # Setup and deployment scripts
├── .github/workflows/           # GitHub Actions workflows
├── run.py                       # Simple runner script
├── setup.py                     # Package setup
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database access
- Required API keys (see Configuration section)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd calendar_extractor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   # Generate instructor reports for current month
   python run.py --instructor-reports --current-month --handlers csv
   
   # Generate event list
   python run.py --event-list
   
   # Sync with Base44
   python run.py --instructor-reports --current-month --handlers base44sync
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database
CAMPUS_DB_CONN=postgresql://user:password@host:port/campusdb
LMS_DB_CONN=postgresql://user:password@host:port/lmsdb

# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your_s3_bucket

# API Keys
HUBSPOT_API_KEY=your_hubspot_api_key
BASE44_API_KEY=your_base44_api_key
```

### Required Secrets

- **CAMPUS_DB_CONN**: PostgreSQL connection string for campus database
- **HUBSPOT_API_KEY**: HubSpot API key for contact updates
- **BASE44_API_KEY**: Base44 API key for time tracking sync

## 📋 Usage

### Command Line Options

```bash
python run.py [OPTIONS]

Options:
  --event-list              Generate event list CSV files
  --instructor-reports      Generate instructor reports
  --month YYYY-MM          Target month for reports (format: YYYY-MM)
  --current-month          Generate reports for current month
  --handlers [csv|s3|base44sync]  Output handlers (default: csv)
  --duplicate-events SOURCE_EMAIL TARGET_EMAIL  Duplicate events for testing
```

### Examples

```bash
# Generate event list
python run.py --event-list

# Generate instructor reports for specific month
python run.py --instructor-reports --month 2025-01 --handlers csv

# Generate reports for current month and sync with Base44
python run.py --instructor-reports --current-month --handlers base44sync

# Use multiple handlers
python run.py --instructor-reports --month 2025-01 --handlers csv s3 base44sync
```

## 🔄 Automated Workflows

### GitHub Actions

The project includes a GitHub Actions workflow that runs every 3 hours:

- **File**: `.github/workflows/calendar-sync.yml`
- **Schedule**: Every 3 hours (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC)
- **Command**: `python run.py --instructor-reports --current-month --handlers base44sync`

See `GITHUB_WORKFLOW_SETUP.md` for detailed setup instructions.

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install -e .

# Run tests
python -m pytest tests/
```

### Code Structure

- **`src/core/main.py`**: Main application entry point
- **`src/data/parsers/calendar_parser.py`**: Calendar event parsing logic
- **`src/reports/generators.py`**: Report generation functions
- **`src/reports/handlers.py`**: Output handlers (CSV, S3, Base44)
- **`src/services/`**: External service integrations

### Adding New Features

1. **New Service**: Add to `src/services/`
2. **New Report Type**: Add to `src/reports/generators.py`
3. **New Handler**: Add to `src/reports/handlers.py`
4. **New Utility**: Add to `src/utils/`

## 📊 Output Files

The application generates several output files in the `output/` directory:

- `events_list.csv`: Complete list of calendar events
- `monthly_instructor_hours.csv`: Monthly instructor statistics
- `instructor_reports/`: Individual instructor reports (CSV format)
- `not_found_contacts_*.csv`: Contacts not found in HubSpot

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the documentation in `docs/`
2. Review the GitHub workflow setup guide
3. Open an issue on GitHub 