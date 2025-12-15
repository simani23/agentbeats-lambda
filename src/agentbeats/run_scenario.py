import argparse
import asyncio
import os, sys, time, subprocess, shlex, signal
import re
from pathlib import Path
import tomllib
import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver


load_dotenv(override=True)


# Model name mapping: user-friendly names to API model identifiers
# These identifiers work with common providers (OpenRouter, LiteLLM, Ollama, etc.)
# Users may need to configure appropriate API keys and base URLs in .env
MODEL_MAPPING = {
    # OpenAI models (paid, but gpt-4o-mini is cheap)
    "gpt-4o-mini": "gpt-4o-mini",
    "chatgpt-4o-mini": "gpt-4o-mini",
    
    # Gemini models (free tier available)
    "gemini-2.0-flash": "gemini/gemini-2.0-flash-exp",
    "gemini-1.5-flash": "google/gemini-flash-1.5",  # OpenRouter free tier
    "gemini-flash": "google/gemini-flash-1.5",
    
    # DeepSeek models (free tier available)
    "deepseek-r1": "deepseek/deepseek-r1",
    "deepseek": "deepseek/deepseek-r1",
    
    # Llama models via OpenRouter (free tier available)
    "llama3.0": "meta-llama/Llama-3-70B-Instruct",
    "llama-3-70b": "meta-llama/Llama-3-70B-Instruct",
    "llama-3.2-3b": "meta-llama/llama-3.2-3b-instruct",  # OpenRouter free tier
    "llama3.2-3b": "meta-llama/llama-3.2-3b-instruct",
    
    # Ollama models (local, completely free)
    "llama3.2": "ollama/llama3.2:3b",
    "llama3.2:3b": "ollama/llama3.2:3b",
    "llama3.2:1b": "ollama/llama3.2:1b",
    "llama3.1:8b": "ollama/llama3.1:8b",
    "llama3.1": "ollama/llama3.1:8b",
    "qwen2.5:7b": "ollama/qwen2.5:7b",
    "qwen2.5": "ollama/qwen2.5:7b",
    "mistral:7b": "ollama/mistral:7b",
    "mistral": "ollama/mistral:7b",
    
    # OpenRouter free tier models
    "qwen-2.5-7b": "qwen/qwen-2.5-7b-instruct",  # OpenRouter free tier
    "qwen2.5-7b": "qwen/qwen-2.5-7b-instruct",
}


def get_model_identifier(model_name: str) -> str:
    """Convert user-friendly model name to API model identifier."""
    model_lower = model_name.lower().replace(" ", "-")
    return MODEL_MAPPING.get(model_lower, model_name)


def inject_model_into_cmd(cmd: str, model: str) -> str:
    """Inject or replace --model flag in a command string."""
    if not cmd:
        return cmd
    
    model_identifier = get_model_identifier(model)
    
    # Check if --model flag already exists
    if "--model" in cmd:
        # Replace existing --model flag
        # Pattern: --model followed by optional whitespace and the model value
        pattern = r'--model\s+\S+'
        replacement = f'--model {model_identifier}'
        return re.sub(pattern, replacement, cmd)
    else:
        # Add --model flag before the end of the command
        # Try to add it after the script path but before any other flags
        # Simple approach: append it at the end
        return f"{cmd} --model {model_identifier}"


async def wait_for_agents(cfg: dict, timeout: int = 30) -> bool:
    """Wait for all agents to be healthy and responding."""
    endpoints = []

    # Collect all endpoints to check
    for p in cfg["participants"]:
        if p.get("cmd"):  # Only check if there's a command (agent to start)
            endpoints.append(f"http://{p['host']}:{p['port']}")

    if cfg["green_agent"].get("cmd"):  # Only check if there's a command (host to start)
        endpoints.append(f"http://{cfg['green_agent']['host']}:{cfg['green_agent']['port']}")

    if not endpoints:
        return True  # No agents to wait for

    print(f"Waiting for {len(endpoints)} agent(s) to be ready...")
    start_time = time.time()

    async def check_endpoint(endpoint: str) -> bool:
        """Check if an endpoint is responding by fetching the agent card."""
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resolver = A2ACardResolver(httpx_client=client, base_url=endpoint)
                await resolver.get_agent_card()
                return True
        except Exception:
            # Any exception means the agent is not ready
            return False

    while time.time() - start_time < timeout:
        ready_count = 0
        for endpoint in endpoints:
            if await check_endpoint(endpoint):
                ready_count += 1

        if ready_count == len(endpoints):
            return True

        print(f"  {ready_count}/{len(endpoints)} agents ready, waiting...")
        await asyncio.sleep(1)

    print(f"Timeout: Only {ready_count}/{len(endpoints)} agents became ready after {timeout}s")
    return False


def parse_toml(scenario_path: str, model: str | None = None) -> dict:
    path = Path(scenario_path)
    if not path.exists():
        print(f"Error: Scenario file not found: {path}")
        sys.exit(1)

    data = tomllib.loads(path.read_text())

    def host_port(ep: str):
        s = (ep or "")
        s = s.replace("http://", "").replace("https://", "")
        s = s.split("/", 1)[0]
        host, port = s.split(":", 1)
        return host, int(port)

    green_ep = data.get("green_agent", {}).get("endpoint", "")
    g_host, g_port = host_port(green_ep)
    green_cmd = data.get("green_agent", {}).get("cmd", "")
    
    # Inject model into orchestrator if model is specified (orchestrator now accepts --model)
    # Only inject if the command looks like it's running an agent script (has --host and --port)
    if model and green_cmd and "--host" in green_cmd and "--port" in green_cmd:
        green_cmd = inject_model_into_cmd(green_cmd, model)

    parts = []
    for p in data.get("participants", []):
        if isinstance(p, dict) and "endpoint" in p:
            h, pt = host_port(p["endpoint"])
            cmd = p.get("cmd", "")
            
            # Inject model into participant cmd if model is specified
            # Only inject if the command looks like it's running an agent script (has --host and --port)
            if model and cmd and "--host" in cmd and "--port" in cmd:
                cmd = inject_model_into_cmd(cmd, model)
            
            parts.append({
                "role": str(p.get("role", "")),
                "host": h,
                "port": pt,
                "cmd": cmd
            })

    cfg = data.get("config", {})
    return {
        "green_agent": {"host": g_host, "port": g_port, "cmd": green_cmd},
        "participants": parts,
        "config": cfg,
    }


def main():
    parser = argparse.ArgumentParser(description="Run agent scenario")
    parser.add_argument("scenario", help="Path to scenario TOML file")
    parser.add_argument("--show-logs", action="store_true",
        help="Show agent stdout/stderr")
    parser.add_argument("--serve-only", action="store_true",
        help="Start agent servers only without running evaluation")
    parser.add_argument("--model", type=str, default=None,
        help="Model to use for agents (overrides TOML file model settings). "
             "Supported: gpt-4o-mini, gemini-2.0-flash, gemini-1.5-flash, "
             "deepseek-r1, llama3.0, llama-3.2-3b, llama3.2:3b, llama3.2:1b, "
             "llama3.1:8b, qwen2.5:7b, mistral:7b, qwen-2.5-7b. "
             "See sample.env for API key configuration.")
    args = parser.parse_args()

    cfg = parse_toml(args.scenario, model=args.model)
    
    if args.model:
        print(f"Using model: {args.model} -> {get_model_identifier(args.model)}")

    sink = None if args.show_logs or args.serve_only else subprocess.DEVNULL
    parent_bin = str(Path(sys.executable).parent)
    base_env = os.environ.copy()
    base_env["PATH"] = parent_bin + os.pathsep + base_env.get("PATH", "")
    
    # Replace 'python' with sys.executable in commands to ensure we use the venv Python
    def fix_python_cmd(cmd: str) -> str:
        """Replace 'python' with the actual Python executable path."""
        if not cmd:
            return cmd
        # Replace 'python' at the start of command or after whitespace
        # but not if it's part of another word
        python_exe = str(sys.executable)
        # Pattern: 'python' at start or after space, followed by space or end
        import re
        return re.sub(r'(^|\s)python(\s|$)', rf'\1{python_exe}\2', cmd)

    procs = []
    try:
        # start participant agents
        for p in cfg["participants"]:
            cmd = p.get("cmd", "")
            if cmd:
                # Fix Python path in command
                cmd = fix_python_cmd(cmd)
                cmd_args = shlex.split(cmd)
                print(f"Starting {p['role']} at {p['host']}:{p['port']}")
                procs.append(subprocess.Popen(
                    cmd_args,
                    env=base_env,
                    stdout=sink, stderr=sink,
                    text=True,
                    start_new_session=True,
                ))

        # start host
        green_cmd = cfg["green_agent"].get("cmd", "")
        if green_cmd:
            # Fix Python path in command
            green_cmd = fix_python_cmd(green_cmd)
            green_cmd_args = shlex.split(green_cmd)
            print(f"Starting green agent at {cfg['green_agent']['host']}:{cfg['green_agent']['port']}")
            procs.append(subprocess.Popen(
                green_cmd_args,
                env=base_env,
                stdout=sink, stderr=sink,
                text=True,
                start_new_session=True,
            ))

        # Wait for all agents to be ready
        if not asyncio.run(wait_for_agents(cfg)):
            print("Error: Not all agents became ready. Exiting.")
            return

        print("Agents started. Press Ctrl+C to stop.")
        if args.serve_only:
            while True:
                for proc in procs:
                    if proc.poll() is not None:
                        print(f"Agent exited with code {proc.returncode}")
                        break
                    time.sleep(0.5)
        else:
            # Pass model to client_cli if specified
            client_cmd = [sys.executable, "-m", "agentbeats.client_cli", args.scenario]
            if args.model:
                client_cmd.extend(["--model", args.model])
            
            client_proc = subprocess.Popen(
                client_cmd,
                env=base_env,
                start_new_session=True,
            )
            procs.append(client_proc)
            client_proc.wait()

    except KeyboardInterrupt:
        pass

    finally:
        print("\nShutting down...")
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(1)
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    main()
