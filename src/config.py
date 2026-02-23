"""Configuration loader for synlogos.json"""
import json
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from returns.result import Result, Success, Failure


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a specific model"""
    model: str
    extra_options: dict[str, Any]


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a provider (opencode, ollama, togetherai)"""
    name: str
    npm: str
    base_url: str
    api_key: str | None
    models: dict[str, ModelConfig]


@dataclass(frozen=True)
class AgentTypeConfig:
    """Configuration for a specific agent type (explore, code, etc.)"""
    agent_type: str
    provider: str
    model: str
    instructions: str


@dataclass(frozen=True)
class OpenCodeConfig:
    """Main configuration loaded from synlogos.json"""
    theme: str
    instructions_files: list[str]
    default_model: str
    providers: dict[str, ProviderConfig]
    agent_types: dict[str, AgentTypeConfig]
    raw_instructions: str = ""  # Combined instructions from files


def load_json_config(config_path: str | None = None) -> Result[OpenCodeConfig, str]:
    """Load configuration from synlogos.json"""
    if config_path is None:
        # Look for config in standard locations
        possible_paths = [
            Path.cwd() / "synlogos.json",
            Path.cwd() / ".synlogos.json",
            Path.home() / ".synlogos.json",
            Path("/etc/synlogos/synlogos.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break
        
        if config_path is None:
            return Failure("Could not find synlogos.json in any standard location")
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return Failure(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        return Failure(f"Invalid JSON in config file: {e}")
    except Exception as e:
        return Failure(f"Error reading config file: {e}")
    
    try:
        # Parse providers
        providers = {}
        for provider_name, provider_data in data.get("provider", {}).items():
            models = {}
            for model_name, model_data in provider_data.get("models", {}).items():
                # Extract model string and any extra options
                if isinstance(model_data, dict):
                    model_str = model_data.get("model", model_name)
                    extra = {k: v for k, v in model_data.items() if k != "model"}
                else:
                    model_str = model_name
                    extra = {}
                models[model_name] = ModelConfig(model=model_str, extra_options=extra)
            
            providers[provider_name] = ProviderConfig(
                name=provider_name,
                npm=provider_data.get("npm", ""),
                base_url=provider_data.get("options", {}).get("baseURL", ""),
                api_key=provider_data.get("options", {}).get("apiKey"),
                models=models
            )
        
        # Parse agent types
        agent_types = {}
        for agent_name, agent_data in data.get("agent", {}).items():
            model_str = agent_data.get("model", "")
            
            # Parse model string like "ollama/qwen3:8b" or "togetherai/moonshotai/Kimi-K2.5"
            parts = model_str.split("/")
            if len(parts) >= 2:
                provider = parts[0]
                model = "/".join(parts[1:])
            else:
                provider = ""
                model = model_str
            
            agent_types[agent_name] = AgentTypeConfig(
                agent_type=agent_name,
                provider=provider,
                model=model,
                instructions=agent_data.get("instructions", "")
            )
        
        # Load instructions from files
        raw_instructions = ""
        for instr_file in data.get("instructions", []):
            instr_path = Path(config_path).parent / instr_file
            if instr_path.exists():
                try:
                    with open(instr_path, 'r') as f:
                        raw_instructions += f"\n\n{f.read()}"
                except Exception:
                    pass  # Skip files that can't be read
        
        config = OpenCodeConfig(
            theme=data.get("theme", "default"),
            instructions_files=data.get("instructions", []),
            default_model=data.get("model", ""),
            providers=providers,
            agent_types=agent_types,
            raw_instructions=raw_instructions.strip()
        )
        
        return Success(config)
    except Exception as e:
        return Failure(f"Error parsing config: {e}")


def get_agent_config(
    config: OpenCodeConfig,
    agent_type: str | None = None,
    model_override: str | None = None
) -> Result[tuple[str, str, str, str], str]:
    """
    Get the resolved configuration for an agent.
    
    Returns: (provider_name, model_name, api_key, instructions)
    """
    if agent_type and agent_type in config.agent_types:
        agent_config = config.agent_types[agent_type]
        provider_name = agent_config.provider
        model_name = agent_config.model
        instructions = agent_config.instructions
    elif model_override and model_override.strip():
        # Parse model override like "ollama/qwen3:8b"
        parts = model_override.split("/")
        if len(parts) >= 2:
            provider_name = parts[0]
            model_name = "/".join(parts[1:])
        else:
            return Failure(f"Invalid model format: {model_override}. Expected 'provider/model'")
        instructions = ""
    else:
        # Use default model
        parts = config.default_model.split("/")
        if len(parts) >= 2:
            provider_name = parts[0]
            model_name = "/".join(parts[1:])
        else:
            return Failure(f"Invalid default model format: {config.default_model}")
        instructions = ""
    
    # Get provider config
    if provider_name not in config.providers:
        return Failure(f"Unknown provider: {provider_name}")
    
    provider_config = config.providers[provider_name]
    
    # Get API key - from env var if not in config
    api_key = provider_config.api_key
    if not api_key:
        env_var_name = f"{provider_name.upper()}_API_KEY"
        api_key = os.environ.get(env_var_name, "")
    
    return Success((provider_name, model_name, api_key, instructions))


# Global config cache
_config_cache: OpenCodeConfig | None = None


def get_cached_config() -> Result[OpenCodeConfig, str]:
    """Get cached config or load from disk"""
    global _config_cache
    if _config_cache is None:
        result = load_json_config()
        if isinstance(result, Failure):
            return result
        _config_cache = result.unwrap()
    return Success(_config_cache)


def clear_config_cache():
    """Clear the config cache (useful for testing)"""
    global _config_cache
    _config_cache = None


def list_agent_types() -> list[str]:
    """List available agent types from config"""
    result = get_cached_config()
    if isinstance(result, Success):
        return list(result.unwrap().agent_types.keys())
    return []


def get_agent_info(agent_type: str) -> dict | None:
    """Get information about a specific agent type"""
    result = get_cached_config()
    if isinstance(result, Success):
        config = result.unwrap()
        if agent_type in config.agent_types:
            agent_config = config.agent_types[agent_type]
            return {
                "type": agent_type,
                "provider": agent_config.provider,
                "model": agent_config.model,
                "has_custom_instructions": bool(agent_config.instructions)
            }
    return None
