#!/usr/bin/env python3
"""
RedInsight - Reddit数据分析工具
安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取 README 文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取 requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="redinsight",
    version="1.0.0",
    author="RedInsight Team",
    author_email="redinsight@example.com",
    description="Reddit数据分析工具 - 抓取Reddit数据并使用大模型进行分析",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/chaos-of-dawn/RedInsight",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
        "gui": [
            "streamlit>=1.28.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "redinsight=main:main",
            "redinsight-launcher=launcher:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.json"],
    },
    keywords="reddit, data-analysis, llm, ai, scraping, sentiment-analysis",
    project_urls={
        "Bug Reports": "https://github.com/chaos-of-dawn/RedInsight/issues",
        "Source": "https://github.com/chaos-of-dawn/RedInsight",
        "Documentation": "https://github.com/chaos-of-dawn/RedInsight#readme",
    },
)
