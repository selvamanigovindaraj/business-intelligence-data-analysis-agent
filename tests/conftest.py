from __future__ import annotations

import os

# Must be set at module level — settings is instantiated on import, before any fixture runs.
os.environ.setdefault("DEEPSEEK_API_KEY", "test-deepseek-key")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("EMBED_API_KEY", "test-embed-key")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
