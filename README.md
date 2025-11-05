# PSA Tool

PSA (Public Safety Assessment) Tool - A streamlined document processing system for vulnerability analysis and options for consideration.

## 🏗️ Architecture

- **Backend**: Flask (Python) with modular route blueprints
- **Frontend**: Next.js (React)
- **AI Processing**: Ollama integration
- **Database**: Supabase
- **Tunnel**: Cloudflare tunnel for external access

## 📁 Project Structure

```
PSA-Tool/
├── app.py                    # Main Flask entry point
├── routes/                   # Route blueprints
│   ├── system.py            # Health, version, progress
│   ├── files.py             # File management
│   ├── process.py           # Document processing
│   └── library.py           # Library search
├── services/                 # Business logic
│   ├── ollama_client.py     # Ollama API integration
│   ├── supabase_client.py   # Supabase operations
│   └── processor.py          # File processing
├── data/                     # Data directories
│   ├── incoming/            # Files to process
│   ├── processed/           # Processed files
│   └── errors/              # Failed files
├── app/                      # Next.js frontend
└── docs/                     # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- Ollama (running as NSSM service)
- Supabase account
- Cloudflare tunnel (for external access)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/frosty865/PSA_Tool.git
   cd PSA_Tool
   ```

2. **Install Python dependencies**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```powershell
   Copy-Item env.example .env
   # Edit .env with your credentials
   ```

4. **Start Flask server**
   ```powershell
   .\start.ps1
   # Or: python app.py
   ```

5. **Start Next.js frontend** (separate terminal)
   ```powershell
   npm install
   npm run dev
   ```

## 📡 API Endpoints

### System
- `GET /` - Service info
- `GET /api/system/health` - Health check (Flask, Ollama, Supabase, Tunnel)
- `GET /api/version` - Version information
- `GET /api/progress` - Processing progress

### Files
- `GET /api/files/list` - List incoming files
- `GET /api/files/info?filename=...` - File information
- `GET /api/files/download/<filename>` - Download file
- `POST /api/files/write` - Write file to folder

### Processing
- `POST /api/process/start` - Start file processing
- `POST /api/process/document` - Process document
- `GET /api/process/<filename>` - Process specific file

### Library
- `GET /api/library/search?q=...` - Search library
- `POST /api/library/search` - Search library (POST)
- `GET /api/library/entry?id=...` - Get library entry

All endpoints return JSON with `"service": "PSA Processing Server"` metadata.

## 🔧 Configuration

### Environment Variables

See `env.example` for required variables:

- `FLASK_ENV=production`
- `FLASK_PORT=8080`
- `SUPABASE_URL=...`
- `OLLAMA_HOST=http://127.0.0.1:11434`
- `TUNNEL_URL=https://flask.frostech.site`

### NSSM Services

The system assumes the following NSSM services are running:
- `VOFC-Flask` - Flask backend
- `VOFC-Ollama` - Ollama AI service
- `VOFC-Tunnel` - Cloudflare tunnel

## 📚 Documentation

- [Deployment Guide](docs/DEPLOYMENT-FINAL.md)
- [Route Reference](docs/ROUTE-REFERENCE.md)
- [Migration Guide](docs/MIGRATION-SUMMARY.md)
- [Next Steps](docs/NEXT-STEPS.md)

## 🧪 Testing

```powershell
# Test root endpoint
Invoke-WebRequest -Uri "http://localhost:8080/" | Select-Object -ExpandProperty Content

# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8080/api/system/health" | Select-Object -ExpandProperty Content
```

## 📝 License

[Add your license here]

## 👤 Author

frosty865

## 🔗 Links

- Repository: https://github.com/frosty865/PSA_Tool
- Documentation: See `docs/` directory

