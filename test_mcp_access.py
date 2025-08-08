#!/usr/bin/env python3
"""
Test script to verify MCP server access to system tools.
This simulates what gemini-cli needs to do when spawning MCP servers.
"""

import os
import subprocess
import sys

def test_system_tools():
    """Test if we can access common system tools that MCP servers need."""
    
    print("=== Testing MCP Server Environment Access ===")
    print(f"Current PATH: {os.environ.get('PATH', 'NOT SET')}")
    print(f"Platform: {sys.platform}")
    
    # Test tools that MCP servers commonly use
    tools_to_test = ['npx', 'node', 'python', 'python3']
    
    for tool in tools_to_test:
        try:
            # Try to find the tool
            result = subprocess.run([tool, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {tool}: {result.stdout.strip()}")
            else:
                print(f"❌ {tool}: command failed with return code {result.returncode}")
        except FileNotFoundError:
            print(f"❌ {tool}: not found in PATH")
        except subprocess.TimeoutExpired:
            print(f"⏰ {tool}: command timed out")
        except Exception as e:
            print(f"❌ {tool}: error - {e}")
    
    # Test npm specifically
    try:
        result = subprocess.run(['npm', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ npm: {result.stdout.strip()}")
        else:
            print(f"❌ npm: command failed with return code {result.returncode}")
    except FileNotFoundError:
        print(f"❌ npm: not found in PATH")
    except Exception as e:
        print(f"❌ npm: error - {e}")

if __name__ == '__main__':
    test_system_tools()
