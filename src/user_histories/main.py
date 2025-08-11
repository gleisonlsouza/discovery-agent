from __future__ import annotations

import json
import os
from typing import Any, Dict

from user_histories.crew import UserHistoriesCrew
from user_histories.tools import GenerateGherkinStoriesTool


def _deterministic_generate(analysis_path: str, output_dir: str) -> Dict[str, Any]:
    tool = GenerateGherkinStoriesTool()
    result_json = tool._run(
        analysis_path=analysis_path,
        output_dir=output_dir,
        group_by_persona=True,
        strict_mode=True,
    )
    try:
        return json.loads(result_json)
    except Exception:
        return {"written": [], "error": "unexpected tool output"}


def run():
    analysis_path = os.environ.get("ANALYSIS_JSON", "analysis.json")
    output_dir = os.environ.get("USER_STORIES_DIR", "user_stories")

    # Deterministic generation, bypassing LLM agent to avoid malformed Action Inputs
    result = _deterministic_generate(analysis_path=analysis_path, output_dir=output_dir)
    print(json.dumps(result, ensure_ascii=False))


def replay():
    task_id = os.environ.get("TASK_ID", "")
    UserHistoriesCrew().crew().replay(task_id=task_id)


def train():
    # Not typically used for deterministic generation
    pass


def test():
    # Not typically used here
    pass


