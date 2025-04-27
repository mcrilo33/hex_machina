from setuptools import setup, find_packages

setup(
    name="ttd",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "metaflow",
        "pydantic",
        "tinydb",
        "scikit-learn",
        "matplotlib",
        "numpy",
        "evaluate",
        "rouge_score",
        "absl-py",
        "bert_score"
    ],
    python_requires=">=3.9",
)