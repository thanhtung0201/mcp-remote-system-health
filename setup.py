from setuptools import setup, find_packages

setup(
    name="mcp_system_health",
    version="0.1.0",
    description="MCP server for system health monitoring",
    author="Your Name",
    author_email="thanhtung0201@gmail.com",
    packages=find_packages(),
    install_requires=[
        "mcp",
        "pydantic",
        "asyncio",
    ],
    entry_points={
        "console_scripts": [
            "mcp-system-health=mcp_system_health.bin.run:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)