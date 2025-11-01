# Layer_3-Application

The application layer provides user interfaces and interaction points for the agentic reasoning system.

## 🎯 Purpose

Layer_3-Application sits on top of Layer_2-Agentic (the core framework) and provides:
- Web interfaces
- API endpoints
- User interaction flows
- Progress tracking and visualization

## 📁 Structure

```
Layer_3-Application/
├── __init__.py
├── web_app.py           # Flask web interface
├── progress_flow.py     # Progress tracking workflow
├── templates/           # HTML templates
│   └── index.html
└── README.md
```

## 🚀 Running the Web App

```bash
cd Layer_3-Application
python web_app.py
```

Then open your browser to: `http://localhost:5001`

## 🔌 Dependencies

Layer_3-Application depends on:
- **Layer_2-Agentic** for core reasoning capabilities
- **Flask** for web server
- **LangGraph** for workflow execution

## 📊 Architecture

```
Layer_3-Application (UI)
    ↓ uses
Layer_2-Agentic (Framework)
    ↓ uses
Layer_1-Extraction (Data)
```

### Separation of Concerns

- **Layer_1-Extraction**: Data extraction and storage (PDF → Database)
- **Layer_2-Agentic**: Core reasoning framework (Goal → Strategy → Function)
- **Layer_3-Application**: User interfaces and applications (Web UI, APIs)

## 🔧 Configuration

The web app automatically configures paths to access Layer_2-Agentic:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2-Agentic'))
```

## 📝 Features

### Web Interface
- Submit natural language queries
- Real-time progress tracking
- Display structured answers
- Session management
- Export results

### Progress Flow
- Track workflow execution
- Show goal → strategy → function progression
- Display function outputs
- Validation status

## 🎨 Customization

You can extend Layer 3 by:
1. Adding new web endpoints
2. Creating different UI themes
3. Building mobile apps
4. Adding API integrations
5. Creating dashboards

## 📄 Example Usage

```python
# Run the web app
python web_app.py

# Or import for custom use
from web_app import app
app.run(host='0.0.0.0', port=5001)
```

## 🔍 Troubleshooting

**Port already in use:**
```bash
# Find process using port 5001
lsof -i :5001

# Kill the process
kill -9 <PID>
```

**Import errors:**
- Ensure Layer_2-Agentic exists at `../Layer_2-Agentic/`
- Check Python path configuration in web_app.py

**Flask not found:**
```bash
pip install flask
```

## 🤝 Contributing

When adding new applications to Layer_3-Application:
1. Keep business logic in Layer_2-Agentic
2. Only handle UI/UX concerns in Layer_3-Application
3. Use progress_flow.py for execution tracking
4. Follow Flask best practices
5. Document new endpoints

---

**Layer_3-Application Status: ACTIVE** ✅  
**Dependencies: Layer_2-Agentic** ✅  
**Web Interface: Flask** ✅
