# VS Code Setup Guide for Parallax Index

This guide explains how to use VS Code effectively with Parallax Index, including the configured tasks, debugging, and virtual environment integration.

## Initial Setup

### 1. Install Recommended Extensions

When you open the project, VS Code will prompt you to install recommended extensions:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Python Debugger** (ms-python.debugpy)

Or install manually: `Ctrl/Cmd+Shift+X` → Search for "Python"

### 2. Select Python Interpreter

1. Open Command Palette: `Ctrl/Cmd+Shift+P`
2. Type: `Python: Select Interpreter`
3. Choose: `./venv/bin/python` (should be auto-detected)

If venv doesn't exist yet, run the setup task first (see below).

## VS Code Tasks

All tasks are configured to use the virtual environment automatically.

### Access Tasks

- **Quick Access**: `Ctrl/Cmd+Shift+P` → `Tasks: Run Task`
- **Keyboard Shortcut**: `Ctrl/Cmd+Shift+B` for default build task

### Available Tasks

#### Setup Tasks

**Setup: Complete Setup (venv + deps)**
- Creates virtual environment
- Installs all dependencies
- One-click setup for new developers
- Run this first if you just cloned the repo

**Setup: Create Virtual Environment**
- Creates `venv/` folder only
- Useful if venv was deleted

**Setup: Install Dependencies**
- Installs packages from requirements.txt
- Assumes venv already exists

#### Run Tasks

**Run: Start Application** ⭐ *Most Common*
- Starts the Parallax Index server
- Background task (runs continuously)
- Access at: http://localhost:8000
- Stop with: `Ctrl+C` in terminal

**Run: Start Application (Debug Mode)**
- Same as above but with full output buffering disabled
- Better for debugging
- Shows all print statements immediately

**Run: Verify Setup**
- Runs `setup_check.py`
- Verifies all dependencies are installed
- Quick health check

#### Database Tasks

**Database: Clean (Delete DB)**
- Deletes `parallax_index.db`
- Use when you want a fresh start
- All sources and snapshots will be lost

**Database: Clean and Restart**
- Deletes database
- Restarts application
- Fresh start in one click

#### Development Tasks

**Dev: Install Package**
- Prompts for package name
- Installs to venv
- Example: `httpx`, `pytest`, etc.

**Dev: Freeze Requirements**
- Updates `requirements.txt` with current packages
- Run after installing new packages

**Dev: Upgrade Dependencies**
- Updates all packages to latest versions
- Use cautiously (may break compatibility)

**Test: Run Tests (when available)**
- Runs pytest test suite
- Currently tests/ folder doesn't exist
- Add tests and this task will work

## Debugging

### Launch Configurations

Three debug configurations are available:

#### 1. Python: Parallax Index (Main)
- Debugs the main application
- Starts `main.py`
- Stops at breakpoints
- **Use for**: Debugging the full application

**How to use:**
1. Set breakpoints in code (click left of line number)
2. Press `F5` or click "Run and Debug" sidebar
3. Select "Python: Parallax Index"
4. Application starts in debug mode

#### 2. Python: Current File
- Debugs whatever file is currently open
- **Use for**: Testing individual modules or plugins

**How to use:**
1. Open a Python file (e.g., `plugins/numeric_index.py`)
2. Press `F5`
3. Select "Python: Current File"

#### 3. Python: Setup Check
- Debugs the setup verification script
- **Use for**: Troubleshooting dependency issues

### Debug Controls

When debugging:
- `F5` - Continue
- `F10` - Step Over
- `F11` - Step Into
- `Shift+F11` - Step Out
- `Ctrl/Cmd+Shift+F5` - Restart
- `Shift+F5` - Stop

### Debug Console

While paused at a breakpoint:
- View variables in left sidebar
- Hover over variables to see values
- Use Debug Console to evaluate expressions
- Example: Type `source.config` to inspect config

## Virtual Environment Integration

### How It Works

The project is configured to use `venv/` for all Python operations:

1. **Tasks**: All tasks use `${workspaceFolder}/venv/bin/python`
2. **Debugging**: Launch configs specify venv Python
3. **Terminal**: Auto-activates venv when opening new terminals
4. **IntelliSense**: Pylance uses venv for autocompletion

### Platform Support

Tasks automatically adjust for your OS:
- **Linux/macOS**: `venv/bin/python`
- **Windows**: `venv\Scripts\python.exe`

### Verify venv is Active

Check the VS Code status bar (bottom left):
- Should show: `Python 3.12.x ('venv')`
- If not, select interpreter manually

### Terminal Integration

When you open a new terminal in VS Code:
1. venv should auto-activate
2. You'll see `(venv)` prefix in prompt
3. `python` command will use venv Python

If not auto-activating:
- Check `.vscode/settings.json` has `python.terminal.activateEnvironment: true`
- Manually activate: `source venv/bin/activate`

## Common Workflows

### Starting Fresh Development Session

1. Open VS Code in project folder
2. `Ctrl/Cmd+Shift+P` → `Tasks: Run Task`
3. Select `Run: Start Application`
4. Open browser to http://localhost:8000
5. Make changes, save files, see results

### Installing a New Package

1. `Ctrl/Cmd+Shift+P` → `Tasks: Run Task`
2. Select `Dev: Install Package`
3. Type package name (e.g., `requests`)
4. Package installs to venv
5. Update requirements.txt:
   - Run `Dev: Freeze Requirements` task
   - Or manually: `pip freeze > requirements.txt`

### Debugging a Collection Issue

1. Set breakpoint in plugin's `collect()` method
2. Press `F5` → Select "Python: Parallax Index"
3. Trigger collection via web UI or wait for schedule
4. Debugger pauses at breakpoint
5. Inspect variables, step through code
6. Fix issue, restart debug session

### Testing a New Plugin

1. Create plugin file in `plugins/`
2. Open file in editor
3. Press `F5` → Select "Python: Current File"
4. Or use task: `Run: Start Application`
5. Check logs for plugin registration
6. Add source via web UI

### Resetting Database

1. Stop application (if running)
2. `Ctrl/Cmd+Shift+P` → `Tasks: Run Task`
3. Select `Database: Clean and Restart`
4. Fresh database with app running

## Keyboard Shortcuts Summary

| Action | Shortcut |
|--------|----------|
| Open Command Palette | `Ctrl/Cmd+Shift+P` |
| Run Task | `Ctrl/Cmd+Shift+P` → "Tasks" |
| Start Debugging | `F5` |
| Toggle Breakpoint | `F9` |
| Open Terminal | `` Ctrl/Cmd+` `` |
| Select Interpreter | `Ctrl/Cmd+Shift+P` → "Python: Select" |
| Go to File | `Ctrl/Cmd+P` |
| Search in Files | `Ctrl/Cmd+Shift+F` |

## Troubleshooting

### "venv/bin/python not found"

**Cause**: Virtual environment doesn't exist  
**Solution**: Run task `Setup: Complete Setup (venv + deps)`

### Tasks using wrong Python

**Cause**: System Python instead of venv  
**Solution**: 
1. Check `.vscode/settings.json` exists
2. Verify `python.defaultInterpreterPath` is correct
3. Reload window: `Ctrl/Cmd+Shift+P` → "Reload Window"

### Terminal not activating venv

**Cause**: Settings not applied  
**Solution**:
1. Close all terminals
2. Open new terminal: `` Ctrl/Cmd+` ``
3. Should see `(venv)` prefix
4. If not, manually: `source venv/bin/activate`

### IntelliSense not working

**Cause**: Pylance not using venv  
**Solution**:
1. Check selected interpreter (bottom left)
2. `Ctrl/Cmd+Shift+P` → `Python: Select Interpreter`
3. Choose `./venv/bin/python`
4. Restart Pylance: `Ctrl/Cmd+Shift+P` → "Pylance: Restart"

### Import errors in editor (red squiggles)

**Cause**: Dependencies not in venv or wrong interpreter  
**Solution**:
1. Verify venv selected as interpreter
2. Run `Setup: Install Dependencies` task
3. Check `requirements.txt` is up to date

### Application doesn't start

**Cause**: Multiple issues possible  
**Solution**:
1. Run `Run: Verify Setup` task
2. Check terminal output for errors
3. Ensure port 8000 is available
4. Try `Database: Clean (Delete DB)` task

## Tips & Tricks

### Quick Application Restart

1. Stop current run: `Ctrl+C` in terminal
2. Up arrow in terminal to recall last command
3. Press Enter

Or use task `Database: Clean and Restart` for fresh start

### Viewing Logs

Application logs appear in:
- Terminal where task is running
- Look for lines starting with `✓` or `✗`
- Scheduler outputs collection results

### Multiple Terminal Windows

- Open multiple terminals: Click `+` in terminal panel
- One for application, one for development commands
- Switch with dropdown in terminal panel

### File Navigation

- `Ctrl/Cmd+P` → Quick file open
- Start typing: `sched` → finds `core/scheduler.py`
- `@` in quick open → Jump to symbol in file

### IntelliSense Features

- `Ctrl+Space` → Trigger suggestions
- `Ctrl+.` → Quick fixes
- `F12` → Go to definition
- `Shift+F12` → Find all references
- Hover over imports/functions for documentation

### Custom Tasks

Edit `.vscode/tasks.json` to add your own tasks:

```json
{
    "label": "My Custom Task",
    "type": "shell",
    "command": "${workspaceFolder}/venv/bin/python",
    "args": ["my_script.py"],
    "options": {
        "cwd": "${workspaceFolder}"
    }
}
```

## Resources

- [VS Code Python Documentation](https://code.visualstudio.com/docs/python/python-tutorial)
- [VS Code Tasks Documentation](https://code.visualstudio.com/docs/editor/tasks)
- [VS Code Debugging Guide](https://code.visualstudio.com/docs/editor/debugging)
- [Parallax Index README](README.md)

---

**Happy Coding!** 🚀
