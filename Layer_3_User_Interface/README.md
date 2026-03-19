# Layer_3_User_Interface

The application layer provides user interfaces and interaction points for the agentic reasoning system.

## 🎯 Purpose

Layer_3_User_Interface sits on top of Layer_2_Agentic_Reasoning (the core framework) and provides:
- Web interfaces
- API endpoints
- User interaction flows
- Progress tracking and visualization

## 📁 Structure

```
Layer_3_User_Interface/
├── __init__.py
├── web_app.py           # Flask web interface
├── progress_flow.py     # Progress tracking workflow
├── templates/           # HTML templates
│   └── index.html
└── README.md
```

## 🚀 Running the Web App

```bash
cd Layer_3_User_Interface
python web_app.py
```

Then open your browser to: `http://localhost:5001`

## 🔌 Dependencies

Layer_3_User_Interface depends on:
- **Layer_2_Agentic_Reasoning** for core reasoning capabilities
- **Flask** for web server
- **LangGraph** for workflow execution

## 📊 Architecture

```
Layer_3_User_Interface (UI)
    ↓ uses
Layer_2_Agentic_Reasoning (Framework)
    ↓ uses
Layer_1_Extraction/Layer_1a (Hose Data)
Layer_1_Extraction/Layer_1b (Coupling Data)
```

### Separation of Concerns

- **Layer_1_Extraction/Layer_1a / Layer_1_Extraction/Layer_1b**: Data extraction and storage (PDF → Database)
- **Layer_2_Agentic_Reasoning**: Core reasoning framework (Goal → Strategy → Function)
- **Layer_3_User_Interface**: User interfaces and applications (Web UI, APIs)

## 🔧 Configuration

The web app automatically configures paths to access Layer_2_Agentic_Reasoning:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2_Agentic_Reasoning'))
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
- Ensure Layer_2_Agentic_Reasoning exists at `../Layer_2_Agentic_Reasoning/`
- Check Python path configuration in web_app.py

**Flask not found:**
```bash
pip install flask
```

## 🤝 Contributing

When adding new applications to Layer_3_User_Interface:
1. Keep business logic in Layer_2_Agentic_Reasoning
2. Only handle UI/UX concerns in Layer_3_User_Interface
3. Use progress_flow.py for execution tracking
4. Follow Flask best practices
5. Document new endpoints

---

**Layer_3_User_Interface Status: ACTIVE** ✅  
**Dependencies: Layer_2_Agentic_Reasoning** ✅  
**Web Interface: Flask** ✅
