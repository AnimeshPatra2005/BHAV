"""Bhav - what is this worth, and where does it actually go?"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root on import, so GEMINI_API_KEY works whether you
# run the agent, the tools, or a test.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

__version__ = "0.1.0"
