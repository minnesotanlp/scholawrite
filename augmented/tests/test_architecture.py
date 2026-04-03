"""Architecture validation tests to prevent code duplication.

These tests enforce single-responsibility modules and prevent
accidental duplication of core functionality.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Set


# Path to scholawrite package
SRC_PATH = Path(__file__).parent.parent / "scholawrite"


def _get_function_definitions(file_path: Path) -> List[str]:
    """Extract MODULE-LEVEL function names from a Python file.

    Only returns top-level functions, not methods inside classes.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        # Only get functions at module level (direct children of Module)
        return [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]
    except (SyntaxError, UnicodeDecodeError):
        return []


def _find_duplicate_functions(directory: Path) -> Dict[str, List[str]]:
    """Find functions defined in multiple files within src/scholawrite."""
    function_locations: Dict[str, List[str]] = {}

    for py_file in directory.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        functions = _get_function_definitions(py_file)
        for func in functions:
            if func not in function_locations:
                function_locations[func] = []
            function_locations[func].append(py_file.name)

    # Return only functions that appear in multiple files
    return {k: v for k, v in function_locations.items() if len(v) > 1}


class TestNoDuplicateFunctions:
    """Ensure no function is defined in multiple modules."""

    # Known acceptable duplicates (documented reasons)
    ALLOWED_DUPLICATES = {
        # has_prompt_leakage: text.py has comprehensive multi-layer detection,
        # injection.py has simpler pattern-based detection. Both serve different
        # use cases: text.py for general validation, injection.py for quick checks
        # during injection processing. Could be consolidated in future refactor.
        "has_prompt_leakage": ["injection.py", "text.py"],
    }

    def test_no_duplicate_functions(self) -> None:
        """Core functions should be defined in exactly one location."""
        duplicates = _find_duplicate_functions(SRC_PATH)

        # Remove allowed duplicates
        unexpected = {
            k: v for k, v in duplicates.items()
            if k not in self.ALLOWED_DUPLICATES
        }

        if unexpected:
            msg = "Functions defined in multiple files:\n"
            for func, files in unexpected.items():
                msg += f"  - {func}: {', '.join(files)}\n"
            msg += "\nConsolidate to a single module or add to ALLOWED_DUPLICATES with justification."
            raise AssertionError(msg)


class TestModuleResponsibilities:
    """Verify modules have clear responsibility docstrings."""

    REQUIRED_MODULES = [
        "text.py",
        "agentic.py",
        "injection.py",
        "labels.py",
        "metrics.py",
    ]

    def test_modules_have_responsibility_docstrings(self) -> None:
        """Key modules must have docstrings explaining their responsibility."""
        missing = []

        for module_name in self.REQUIRED_MODULES:
            module_path = SRC_PATH / module_name
            if not module_path.exists():
                missing.append(f"{module_name}: file not found")
                continue

            content = module_path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if not docstring:
                    missing.append(f"{module_name}: no module docstring")
                elif len(docstring) < 50:
                    missing.append(f"{module_name}: docstring too short ({len(docstring)} chars)")
            except SyntaxError:
                missing.append(f"{module_name}: syntax error")

        if missing:
            raise AssertionError("Module responsibility issues:\n  - " + "\n  - ".join(missing))


class TestLabelModule:
    """Tests for the consolidated labels module."""

    def test_parse_label_exists(self) -> None:
        """labels.py should export parse_label function."""
        from scholawrite.labels import parse_label
        assert callable(parse_label)

    def test_parse_label_exact_match(self) -> None:
        """parse_label should return exact matches unchanged."""
        from scholawrite.labels import parse_label
        assert parse_label("Clarity") == "Clarity"
        assert parse_label("Text Production") == "Text Production"

    def test_parse_label_substring_extraction(self) -> None:
        """parse_label should extract label from verbose LLM output."""
        from scholawrite.labels import parse_label
        assert parse_label("The intention is Clarity because...") == "Clarity"
        assert parse_label("I think this is Text Production.") == "Text Production"

    def test_parse_label_fallback(self) -> None:
        """parse_label should return fallback for unrecognized input."""
        from scholawrite.labels import parse_label
        assert parse_label("gibberish") == "Invalid"
        assert parse_label("gibberish", fallback="Unknown") == "Unknown"

    def test_writing_intentions_constant(self) -> None:
        """WRITING_INTENTIONS should have 15 labels."""
        from scholawrite.labels import WRITING_INTENTIONS
        assert len(WRITING_INTENTIONS) == 15
        assert "Clarity" in WRITING_INTENTIONS
        assert "Text Production" in WRITING_INTENTIONS


class TestMetricsModule:
    """Tests for the consolidated metrics module."""

    def test_compute_classification_metrics_exists(self) -> None:
        """metrics.py should export compute_classification_metrics function."""
        from scholawrite.metrics import compute_classification_metrics
        assert callable(compute_classification_metrics)

    def test_compute_classification_metrics_basic(self) -> None:
        """compute_classification_metrics should compute accuracy correctly."""
        from scholawrite.metrics import compute_classification_metrics

        y_true = ["A", "B", "A", "B", "A"]
        y_pred = ["A", "B", "A", "A", "A"]

        result = compute_classification_metrics(y_true, y_pred, verbose=False)

        assert result["accuracy"] == 0.8  # 4/5 correct
        assert "macro_f1" in result
        assert "per_class" in result

    def test_compute_classification_metrics_empty(self) -> None:
        """compute_classification_metrics should handle empty inputs."""
        from scholawrite.metrics import compute_classification_metrics

        result = compute_classification_metrics([], [], verbose=False)
        assert result["accuracy"] == 0.0


class TestInjectionModule:
    """Tests for the injection module naming conventions."""

    def test_generate_deterministic_placeholder_exists(self) -> None:
        """injection.py should export generate_deterministic_placeholder."""
        from scholawrite.injection import generate_deterministic_placeholder
        assert callable(generate_deterministic_placeholder)

    def test_generate_placeholder_text_backward_compat(self) -> None:
        """Deprecated generate_placeholder_text should still work."""
        from scholawrite.injection import generate_placeholder_text
        from scholawrite.schema import InjectionLevel

        # Should produce same output as new function
        text = generate_placeholder_text(InjectionLevel.NAIVE, seed=42)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_deterministic_placeholder_reproducible(self) -> None:
        """Same seed should produce same placeholder text."""
        from scholawrite.injection import generate_deterministic_placeholder
        from scholawrite.schema import InjectionLevel

        text1 = generate_deterministic_placeholder(InjectionLevel.TOPICAL, seed=12345)
        text2 = generate_deterministic_placeholder(InjectionLevel.TOPICAL, seed=12345)

        assert text1 == text2
