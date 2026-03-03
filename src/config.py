MODEL_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-8d53b7dbd534447c920d8a47671a44cf",
        "model": "deepseek-chat",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "AIzaSyCYFa7WsoX-hTWznh8PgRBzbDIbE-dW5SE",
        "model": "gemini-2.0-flash",
    },
}

DEFAULT_PROVIDER = "deepseek"

AGENT_CONFIG = {
    "max_iterations": 6,
    "enable_planner": True,
    "memory_backend": "file",
    "memory_file_path": ".jarvis/memory.json",
}

