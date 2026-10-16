from setuptools import setup, find_packages

setup(
    name="ezshell",
    version="0.1.0",
    description="Intelligent terminal popup and assistant powered by Groq LLMs",
    author="ezShell Team",
    packages=find_packages(),
    install_requires=[
        "groq>=0.11.0",
        "prompt_toolkit>=3.0.40",
        "rich>=13.7.0",
        "pyte>=0.8.2",
        "python-dotenv>=1.0.0",
        "textual>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ezshell=src.main:main",
            "ezsh=src.main:main",
            "eszh=src.main:main",
        ],
    },
    python_requires=">=3.10",
)
