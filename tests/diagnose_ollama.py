"""
Comprehensive Ollama diagnostic and repair script.

Diagnoses common Ollama issues and provides automated fixes for:
- Service status and health
- Model availability and corruption
- Memory and resource issues
- Configuration problems
"""

import subprocess
import sys
import time
import psutil
from pathlib import Path

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    """Print formatted section header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def run_command(cmd, shell=True, capture=True):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_ollama_service():
    """Check if Ollama service is running."""
    print_header("OLLAMA SERVICE STATUS")
    
    # Check for ollama processes
    ollama_procs = [p for p in psutil.process_iter(['name']) if 'ollama' in p.info['name'].lower()]
    
    if ollama_procs:
        print(f"{GREEN}✅ Ollama process found:{RESET}")
        for proc in ollama_procs:
            try:
                p = psutil.Process(proc.pid)
                memory_mb = p.memory_info().rss / 1024 / 1024
                cpu_percent = p.cpu_percent(interval=0.1)
                print(f"   PID: {proc.pid}, Memory: {memory_mb:.1f} MB, CPU: {cpu_percent:.1f}%")
            except:
                pass
    else:
        print(f"{RED}❌ No Ollama process running{RESET}")
        print(f"{YELLOW}💡 Try: ollama serve{RESET}")
        return False
    
    # Test Ollama API
    success, stdout, stderr = run_command("ollama list")
    if success:
        print(f"\n{GREEN}✅ Ollama API responding{RESET}")
        print("\nInstalled models:")
        print(stdout)
        return True
    else:
        print(f"\n{RED}❌ Ollama API not responding{RESET}")
        print(f"Error: {stderr}")
        return False


def check_system_resources():
    """Check available system resources."""
    print_header("SYSTEM RESOURCES")
    
    # Memory
    mem = psutil.virtual_memory()
    mem_gb = mem.total / (1024**3)
    mem_avail_gb = mem.available / (1024**3)
    mem_percent = mem.percent
    
    print(f"Total RAM: {mem_gb:.1f} GB")
    print(f"Available: {mem_avail_gb:.1f} GB ({100-mem_percent:.1f}% free)")
    
    if mem_avail_gb < 2:
        print(f"{RED}⚠️  Low memory! Need 2GB+ available{RESET}")
        return False
    elif mem_avail_gb < 4:
        print(f"{YELLOW}⚠️  Limited memory. Consider smaller models{RESET}")
    else:
        print(f"{GREEN}✅ Sufficient memory available{RESET}")
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    print(f"\nCPU: {cpu_count} cores, {cpu_percent:.1f}% usage")
    
    if cpu_percent > 90:
        print(f"{YELLOW}⚠️  High CPU usage{RESET}")
    else:
        print(f"{GREEN}✅ CPU available{RESET}")
    
    return True


def check_model_availability():
    """Check if required models are available."""
    print_header("MODEL AVAILABILITY")
    
    required_models = ["llama3.2:latest", "llama3.2:1b", "llama3.2:3b"]
    
    success, stdout, _ = run_command("ollama list")
    if not success:
        print(f"{RED}❌ Cannot check models{RESET}")
        return False
    
    installed = []
    for line in stdout.split('\n')[1:]:  # Skip header
        if line.strip():
            model_name = line.split()[0]
            installed.append(model_name)
    
    print("Required models:")
    all_found = True
    for model in required_models:
        if any(model in m for m in installed):
            print(f"{GREEN}✅ {model}{RESET}")
        else:
            print(f"{RED}❌ {model} - NOT INSTALLED{RESET}")
            print(f"   Install: ollama pull {model}")
            all_found = False
    
    return all_found


def test_model_inference():
    """Test basic model inference."""
    print_header("MODEL INFERENCE TEST")
    
    print("Testing llama3.2:latest with simple prompt...")
    cmd = 'ollama run llama3.2:latest "Say hello in one word"'
    
    start = time.time()
    success, stdout, stderr = run_command(cmd)
    elapsed = time.time() - start
    
    if success and stdout.strip():
        print(f"{GREEN}✅ Model inference successful ({elapsed:.1f}s){RESET}")
        print(f"Response: {stdout.strip()[:100]}")
        return True
    else:
        print(f"{RED}❌ Model inference failed{RESET}")
        print(f"Error: {stderr}")
        
        if "exit status 2" in stderr:
            print(f"\n{YELLOW}💡 'exit status 2' detected!{RESET}")
            print("   This usually means:")
            print("   1. Model is corrupted → Run: ollama rm llama3.2:latest && ollama pull llama3.2:latest")
            print("   2. Out of memory → Close other apps or use smaller model")
            print("   3. Context too large → Reduce num_ctx in config")
        
        return False


def suggest_fixes(results):
    """Suggest fixes based on diagnostic results."""
    print_header("RECOMMENDED FIXES")
    
    if not results['service']:
        print(f"{YELLOW}1. Start Ollama service:{RESET}")
        print("   ollama serve")
        print()
    
    if not results['resources']:
        print(f"{YELLOW}2. Free up memory:{RESET}")
        print("   - Close unnecessary applications")
        print("   - Use smaller model: llama3.2:1b")
        print()
    
    if not results['models']:
        print(f"{YELLOW}3. Install missing models:{RESET}")
        print("   ollama pull llama3.2:latest")
        print("   ollama pull llama3.2:1b")
        print()
    
    if not results['inference']:
        print(f"{YELLOW}4. Fix model corruption:{RESET}")
        print("   ollama rm llama3.2:latest")
        print("   ollama pull llama3.2:latest")
        print()
        
        print(f"{YELLOW}5. Update config for smaller models:{RESET}")
        print("   Edit: agentic_reasoning/config/config.yaml")
        print("   Change: model: llama3.2:1b")
        print()
    
    if all(results.values()):
        print(f"{GREEN}✅ All checks passed!{RESET}")
        print("   If still experiencing issues:")
        print("   1. Restart Ollama: Get-Process ollama* | Stop-Process -Force")
        print("   2. Clear cache: Remove-Item -Recurse ~/.ollama/tmp")
        print("   3. Check logs: Get-Content ~/.ollama/logs/server.log -Tail 50")


def main():
    """Run all diagnostics."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}OLLAMA DIAGNOSTIC TOOL{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print("\nDiagnosing common issues for 'exit status 2' errors...")
    
    results = {
        'service': check_ollama_service(),
        'resources': check_system_resources(),
        'models': check_model_availability(),
        'inference': False
    }
    
    # Only test inference if service is running
    if results['service']:
        results['inference'] = test_model_inference()
    
    # Suggest fixes
    suggest_fixes(results)
    
    # Summary
    print_header("SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 System is healthy!{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  Issues detected. Follow recommended fixes above.{RESET}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        exit_code = 130
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)
