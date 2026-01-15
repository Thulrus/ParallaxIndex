#!/usr/bin/env python3
"""
Setup script for Parallax Index.

Checks requirements and provides setup instructions.
"""

import sys
import subprocess


def check_python_version():
    """Check if Python version meets requirements."""
    if sys.version_info < (3, 12):
        print("❌ Python 3.12 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    required = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'apscheduler',
        'aiosqlite',
        'httpx',
        'jinja2'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} (missing)")
    
    return missing


def main():
    """Run setup checks."""
    print("=" * 60)
    print("Parallax Index - Setup Check")
    print("=" * 60)
    
    print("\nChecking Python version...")
    if not check_python_version():
        sys.exit(1)
    
    print("\nChecking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print("\n" + "=" * 60)
        print("Missing dependencies detected!")
        print("=" * 60)
        print("\nTo install missing packages, run:")
        print("\n    pip install -r requirements.txt")
        print("\nOr install individually:")
        print(f"\n    pip install {' '.join(missing)}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ All checks passed!")
    print("=" * 60)
    print("\nTo start the application, run:")
    print("\n    python main.py")
    print("\nThe dashboard will be available at:")
    print("    http://localhost:8000")


if __name__ == "__main__":
    main()
