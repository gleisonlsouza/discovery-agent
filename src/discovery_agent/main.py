#!/usr/bin/env python
import os
import sys
import warnings
from datetime import datetime

from discovery_agent.crew import DiscoveryAgent

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def _default_paths():
    repo_root = os.environ.get("REPO_ROOT", os.getcwd())
    return repo_root


def run():
    """Run the crew for repository reverse engineering and JSON analysis output."""
    repo_root = _default_paths()
    inputs = {
        "repo_root": repo_root,
        "current_year": str(datetime.now().year),
    }
    try:
        DiscoveryAgent().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """Train the crew for a given number of iterations."""
    repo_root = _default_paths()
    inputs = {
        "repo_root": repo_root,
        "current_year": str(datetime.now().year),
    }
    try:
        DiscoveryAgent().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """Replay the crew execution from a specific task."""
    try:
        DiscoveryAgent().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """Test the crew execution and returns the results."""
    repo_root = _default_paths()
    inputs = {
        "repo_root": repo_root,
        "current_year": str(datetime.now().year),
    }
    try:
        DiscoveryAgent().crew().test(
            n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
