#!/usr/bin/env python3
"""Test script to verify imports and basic structure without GUI."""
import sys
import ast

def test_file_syntax(filepath):
    """Test if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        print(f"✓ {filepath} - Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {filepath} - Syntax Error: {e}")
        return False
    except Exception as e:
        print(f"✗ {filepath} - Error: {e}")
        return False

def main():
    files_to_test = [
        'app/plugins/home.py',
        'app/ui/main_window.py',
        'app/plugins/profile.py',
        'app/plugins/roadmap.py',
    ]
    
    print("Testing Python files syntax...\n")
    all_ok = True
    for filepath in files_to_test:
        if not test_file_syntax(filepath):
            all_ok = False
    
    print("\n" + "="*50)
    if all_ok:
        print("All files passed syntax check! ✓")
        return 0
    else:
        print("Some files have syntax errors! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
