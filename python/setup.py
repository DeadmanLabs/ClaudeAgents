from setuptools import setup, find_packages

setup(
    name="claude_agents",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.8.0",
        "pydantic>=2.0.0",
        "pytest>=7.0.0",
        "requests>=2.0.0",
        "typing-extensions>=4.0.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",  # For better BeautifulSoup HTML parsing
        "chardet>=5.0.0",  # For character encoding detection
        "attrs>=22.0.0",  # For dataclasses in older Python versions
        "asyncio>=3.4.3",  # For async support
    ],
    extras_require={
        "dev": [
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.0.0",
            "pytest-cov>=4.0.0"
        ]
    },
    python_requires=">=3.9",
)