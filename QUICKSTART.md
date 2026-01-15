# Parallax Index - Quick Start Guide

## Installation

1. **Install Python 3.12+**
   ```bash
   # Check your version
   python3 --version
   ```

2. **Clone and setup**
   ```bash
   cd ParallaxIndex
   
   # Option A: Automated setup (recommended)
   # Linux/macOS:
   bash setup_venv.sh
   # Windows:
   setup_venv.bat
   
   # Option B: Manual setup
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Verify setup**
   ```bash
   # Make sure venv is activated
   python setup_check.py
   ```

4. **Run the application**
   ```bash
   # Make sure venv is activated
   python main.py
   
   # Or use VS Code task:
   # Ctrl/Cmd+Shift+P → Tasks: Run Task → Run: Start Application
   ```

5. **Access the dashboard**
   Open http://localhost:8000 in your browser

## Quick Example

1. Click "Add Source"
2. Select "Numeric Index" plugin
3. Configure:
   - Name: "Test Metric"
   - URL: `https://api.coindesk.com/v1/bpi/currentprice.json`
   - JSON Path: `bpi.USD.rate_float`
   - Schedule: `*/5 * * * *` (every 5 minutes)
4. Enable and save
5. Wait 5 minutes or click "Collect Now"
6. View results on dashboard

## Using VS Code Tasks

After opening the project in VS Code, you can use tasks:

**Setup Tasks:**
- `Setup: Complete Setup (venv + deps)` - One-click setup
- `Setup: Install Dependencies` - Install/update packages

**Run Tasks:**
- `Run: Start Application` - Start the server
- `Run: Start Application (Debug Mode)` - Start with full output
- `Run: Verify Setup` - Check dependencies

**Database Tasks:**
- `Database: Clean (Delete DB)` - Delete database for fresh start
- `Database: Clean and Restart` - Clean DB and restart app

**Development Tasks:**
- `Dev: Install Package` - Add a new package to venv
- `Dev: Upgrade Dependencies` - Update all packages

Access tasks with: `Ctrl/Cmd+Shift+P` → `Tasks: Run Task`

## Troubleshooting

**Import errors**: Make sure virtual environment is activated (`source venv/bin/activate`)
**Database errors**: Use VS Code task "Database: Clean" or delete `parallax_index.db` and restart
**Port 8000 in use**: Change port in `main.py` (line with `port=8000`)
**VS Code not using venv**: Check `.vscode/settings.json` python.defaultInterpreterPath

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Create custom plugins in `/plugins` directory
- Explore the API at http://localhost:8000/docs
