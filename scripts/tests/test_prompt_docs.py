from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_quality  # noqa: E402


class PromptDocsTest(unittest.TestCase):
    def test_main_path_prompt_docs_stay_within_limit(self) -> None:
        result = check_quality.check_prompt_doc_limits()
        self.assertTrue(result.ok, result.details)

    def test_project_manager_references_exist_and_are_linked(self) -> None:
        result = check_quality.check_project_manager_references()
        self.assertTrue(result.ok, result.details)

    def test_prompt_doc_routing_prefers_progressive_disclosure(self) -> None:
        result = check_quality.check_prompt_doc_routing()
        self.assertTrue(result.ok, result.details)

    def test_prompt_doc_limit_check_catches_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            oversized = repo / "AGENTS.md"
            oversized.write_text("\n".join("x" for _ in range(101)) + "\n", encoding="utf-8")
            original_limits = check_quality.PROMPT_DOC_LIMITS
            try:
                check_quality.PROMPT_DOC_LIMITS = {oversized: 100}
                result = check_quality.check_prompt_doc_limits()
            finally:
                check_quality.PROMPT_DOC_LIMITS = original_limits
            self.assertFalse(result.ok)
            self.assertIn("101 lines > 100", result.details)


if __name__ == "__main__":
    unittest.main()
