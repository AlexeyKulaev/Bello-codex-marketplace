from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "bello" / "skills" / "bello-config-advisor"
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("bello_validate_config", SKILL / "scripts" / "validate_config.py")
INSPECTOR = load_module("bello_inspect_config", SKILL / "scripts" / "inspect_config.py")
MODEL_INSPECTOR = load_module("bello_inspect_models", SKILL / "scripts" / "inspect_models.py")


def first_json_block(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n(\{.*?\})\n```", text, flags=re.DOTALL)
    if match is None:
        raise AssertionError(f"no JSON block in {path}")
    return json.loads(match.group(1))


class ConfigAdvisorTests(unittest.TestCase):
    def test_reference_config_passes_canonical_advice_validator(self) -> None:
        config = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        self.assertEqual(VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False), [])

    def test_independently_composed_candidate_matrix_is_valid(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        candidates = []

        luna_high = copy.deepcopy(base)
        luna_high["coder_intelligence"] = "high"
        candidates.append(luna_high)

        luna_with_completion = copy.deepcopy(base)
        luna_with_completion.update(
            coder_intelligence="xhigh",
            completion_intelligence="xhigh",
            completion_review=True,
            max_completion_returns_before_adversary=1,
        )
        candidates.append(luna_with_completion)

        luna_adversary_only = copy.deepcopy(base)
        luna_adversary_only.update(
            coder_intelligence="xhigh",
            completion_intelligence="xhigh",
            adversary_intelligence="max",
            completion_review=True,
            adversary=True,
            max_adversary_runs=1,
            max_completion_returns_before_adversary=0,
            max_completion_returns_after_adversary=0,
        )
        candidates.append(luna_adversary_only)

        terra_with_adversary = copy.deepcopy(base)
        terra_with_adversary.update(
            coder_mod="gpt-5.6-terra",
            coder_intelligence="xhigh",
            completion_intelligence="max",
            adversary_intelligence="max",
            completion_review=True,
            adversary=True,
            max_adversary_runs=1,
            max_completion_returns_before_adversary=1,
        )
        candidates.append(terra_with_adversary)

        two_returns_then_adversary = copy.deepcopy(terra_with_adversary)
        two_returns_then_adversary.update(
            max_completion_returns_before_adversary=2,
            max_adversary_runs=1,
            max_completion_returns_after_adversary=0,
        )
        candidates.append(two_returns_then_adversary)

        returns_after_adversary = copy.deepcopy(terra_with_adversary)
        returns_after_adversary.update(
            max_completion_returns_before_adversary=1,
            max_adversary_runs=1,
            max_completion_returns_after_adversary=1,
        )
        candidates.append(returns_after_adversary)

        multiple_review_and_adversary_cycles = copy.deepcopy(terra_with_adversary)
        multiple_review_and_adversary_cycles.update(
            max_completion_returns_before_adversary=3,
            max_adversary_runs=2,
            max_completion_returns_after_adversary=2,
        )
        candidates.append(multiple_review_and_adversary_cycles)

        sol_direct = copy.deepcopy(base)
        sol_direct.update(coder_mod="gpt-5.6-sol", coder_intelligence="xhigh")
        candidates.append(sol_direct)

        delegated = copy.deepcopy(luna_with_completion)
        delegated["multi_agent"].update(enabled=True, max_concurrent=2)
        candidates.append(delegated)

        delegated_completion = copy.deepcopy(luna_with_completion)
        delegated_completion["completion_multi_agent"].update(enabled=True, max_concurrent=2)
        candidates.append(delegated_completion)

        delegated_adversary = copy.deepcopy(terra_with_adversary)
        delegated_adversary["adversary_multi_agent"].update(enabled=True, max_concurrent=3)
        candidates.append(delegated_adversary)

        revision_profile = copy.deepcopy(luna_with_completion)
        revision_profile.update(
            revision_coder_enabled=True,
            revision_coder_mod="gpt-5.6-luna",
            revision_coder_intelligence="max",
        )
        candidates.append(revision_profile)

        for config in candidates:
            with self.subTest(config=config):
                self.assertEqual(VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False), [])

    def test_validator_allows_explicitly_authorized_unbounded_review_schedule(self) -> None:
        config = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        config.update(
            completion_review=True,
            adversary=True,
            max_completion_returns_before_adversary="unlimited",
            max_adversary_runs=3,
            max_completion_returns_after_adversary="unlimited",
        )

        self.assertTrue(VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False))
        self.assertEqual(VALIDATOR.validate(config, allow_clean=False, allow_unlimited=True), [])

    def test_validator_rejects_unsafe_or_impossible_combinations(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        cases = []

        luna_ultra = copy.deepcopy(base)
        luna_ultra["coder_intelligence"] = "ultra"
        cases.append(luna_ultra)

        adversary_without_completion = copy.deepcopy(base)
        adversary_without_completion.update(adversary=True, max_adversary_runs=1)
        cases.append(adversary_without_completion)

        clean = copy.deepcopy(base)
        clean["clean"] = True
        cases.append(clean)

        invalid_child = copy.deepcopy(base)
        invalid_child["multi_agent"]["default"]["intelligence"] = "max"
        cases.append(invalid_child)

        for config in cases:
            with self.subTest(config=config):
                self.assertTrue(VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False))

    def test_validator_validates_each_multi_agent_policy_independently(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        for field in (
            "multi_agent",
            "completion_multi_agent",
            "adversary_multi_agent",
        ):
            config = copy.deepcopy(base)
            config[field]["default"]["intelligence"] = "max"
            errors = VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False)
            with self.subTest(field=field):
                self.assertTrue(any(error.startswith(f"{field}.default:") for error in errors), errors)

    def test_validator_requires_revision_coder_profile_and_validates_effort(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")

        missing = copy.deepcopy(base)
        del missing["revision_coder_mod"]
        missing_errors = VALIDATOR.validate(missing, allow_clean=False, allow_unlimited=False)
        self.assertTrue(any("revision_coder_mod" in error for error in missing_errors))

        invalid = copy.deepcopy(base)
        invalid.update(
            revision_coder_enabled=True,
            revision_coder_mod="gpt-5.6-luna",
            revision_coder_intelligence="ultra",
        )
        invalid_errors = VALIDATOR.validate(invalid, allow_clean=False, allow_unlimited=False)
        self.assertTrue(any("revision_coder_intelligence" in error for error in invalid_errors))

        runtime_only = copy.deepcopy(base)
        runtime_only["revision_coder_enabled"] = True
        runtime_only_errors = VALIDATOR.validate(runtime_only, allow_clean=False, allow_unlimited=False)
        self.assertTrue(any("runtime-only" in error for error in runtime_only_errors))

    def test_validator_allows_luna_for_active_supervisor_roles_but_rejects_legacy(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")

        luna_pipeline = copy.deepcopy(base)
        luna_pipeline.update(
            runtime_mod="gpt-5.6-luna",
            completion_mod="gpt-5.6-luna",
            adversary_mod="gpt-5.6-luna",
            runtime_intelligence="xhigh",
            completion_intelligence="xhigh",
            adversary_intelligence="max",
            completion_review=True,
            adversary=True,
            max_adversary_runs=1,
            max_completion_returns_before_adversary=1,
            max_completion_returns_after_adversary=0,
        )
        self.assertEqual(
            VALIDATOR.validate(luna_pipeline, allow_clean=False, allow_unlimited=False),
            [],
        )

        for role in ("runtime", "completion", "adversary"):
            config = copy.deepcopy(luna_pipeline)
            config[f"{role}_mod"] = "gpt-5.5"
            config[f"{role}_intelligence"] = "xhigh"
            errors = VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False)
            with self.subTest(role=role):
                self.assertTrue(any(error.startswith(f"{role}_mod: advisor") for error in errors), errors)

    def test_validator_rejects_run_only_plan_path_as_project_config(self) -> None:
        config = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        config["plan_path"] = "PLAN.md"

        errors = VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False)

        self.assertTrue(any(error.startswith("root: unknown keys") for error in errors), errors)
        self.assertTrue(any("plan_path" in error for error in errors), errors)

    def test_validator_requires_a_canonical_project_relative_task_path(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")

        nested = copy.deepcopy(base)
        nested["task"] = "tasks/TASK.md"
        self.assertEqual(
            VALIDATOR.validate(nested, allow_clean=False, allow_unlimited=False),
            [],
        )

        invalid_paths = (
            None,
            "",
            " ",
            ".",
            "./TASK.md",
            "tasks//TASK.md",
            "/tmp/TASK.md",
            r"C:\tmp\TASK.md",
            r"C:TASK.md",
            r"\\server\share\TASK.md",
            "../TASK.md",
            "tasks/../../TASK.md",
        )
        for task in invalid_paths:
            config = copy.deepcopy(base)
            config["task"] = task
            errors = VALIDATOR.validate(config, allow_clean=False, allow_unlimited=False)
            with self.subTest(task=task):
                self.assertTrue(any(error.startswith("task:") for error in errors), errors)

    def test_validator_resolves_and_matches_the_exact_input_task(self) -> None:
        base = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = root / "tasks" / "TASK.md"
            task.parent.mkdir()
            task.write_text("task", encoding="utf-8")
            expected = VALIDATOR._resolve_expected_task(root, task)

            self.assertEqual(expected, "tasks/TASK.md")
            base["task"] = expected
            self.assertEqual(
                VALIDATOR.validate(
                    base,
                    allow_clean=False,
                    allow_unlimited=False,
                    expected_task=expected,
                ),
                [],
            )

            base["task"] = "TASK.md"
            errors = VALIDATOR.validate(
                base,
                allow_clean=False,
                allow_unlimited=False,
                expected_task=expected,
            )
            self.assertTrue(any("resolved input task" in error for error in errors), errors)

        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as other_tmp:
            outside = Path(other_tmp) / "TASK.md"
            outside.write_text("task", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the project root"):
                VALIDATOR._resolve_expected_task(Path(root_tmp), outside)

    def test_inspector_round_trips_revision_and_each_multi_agent_policy(self) -> None:
        expected = first_json_block(SKILL / "references" / "CONFIG_SCHEMA.md")
        expected.update(
            task="TASK.md",
            revision_coder_enabled=True,
            revision_coder_mod="gpt-5.6-luna",
            revision_coder_intelligence="max",
            completion_review=True,
            adversary=True,
            max_adversary_runs=1,
            max_completion_returns_before_adversary=1,
            max_completion_returns_after_adversary=1,
        )
        expected["multi_agent"] = {
            "enabled": True,
            "max_concurrent": 2,
            "default": {"model": "gpt-5.6-luna", "intelligence": "medium"},
            "allowed": {"gpt-5.6-luna": ["medium", "xhigh"]},
        }
        expected["completion_multi_agent"] = {
            "enabled": True,
            "max_concurrent": 3,
            "default": {"model": "gpt-5.6-terra", "intelligence": "high"},
            "allowed": {
                "gpt-5.6-luna": ["high"],
                "gpt-5.6-terra": ["high"],
            },
        }
        expected["adversary_multi_agent"] = {
            "enabled": True,
            "max_concurrent": 4,
            "default": {"model": "gpt-5.6-luna", "intelligence": "xhigh"},
            "allowed": {"gpt-5.6-luna": ["xhigh", "max"]},
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            payload = {**expected, "status": "complete", "unrelated_runtime_counter": 17}
            (state / "config.json").write_text(json.dumps(payload), encoding="utf-8")
            result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)

        self.assertTrue(result["source_config_valid"], result["source_config_errors"])
        self.assertEqual(result["current_project_config"], expected)
        self.assertEqual(
            VALIDATOR.validate(
                result["current_project_config"],
                allow_clean=False,
                allow_unlimited=False,
            ),
            [],
        )

    def test_inspector_reports_invalid_reviewer_multi_agent_source_by_role(self) -> None:
        for field in ("completion_multi_agent", "adversary_multi_agent"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = root / ".supervisor"
                state.mkdir()
                (state / "config.json").write_text(
                    json.dumps(
                        {
                            "review_limit_format": "explicit",
                            field: {"enabled": "yes"},
                        }
                    ),
                    encoding="utf-8",
                )
                result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
            with self.subTest(field=field):
                self.assertFalse(result["source_config_valid"])
                self.assertTrue(
                    any(error.startswith(field) for error in result["source_config_errors"]),
                    result["source_config_errors"],
                )

    def test_sparse_revision_profile_inherits_normalized_coder_profile(self) -> None:
        current = INSPECTOR._normalize(
            {
                "review_limit_format": "explicit",
                "coder_mod": " gpt-5.6-luna ",
                "coder_intelligence": " MAX ",
            },
            config_exists=True,
        )
        self.assertFalse(current["revision_coder_enabled"])
        self.assertEqual(current["revision_coder_mod"], "gpt-5.6-luna")
        self.assertEqual(current["revision_coder_intelligence"], "max")

    def test_inspector_normalizes_runtime_aliases_and_detects_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            payload = {
                "status": "running",
                "task_path": "TASK.md",
                "coder_model": "gpt-5.6-terra",
                "runtime_model": "gpt-5.6-luna",
                "completion_model": "gpt-5.6-luna",
                "adversary_model": "gpt-5.6-luna",
                "coder_intelligence": "xhigh",
                "runtime_intelligence": "high",
                "completion_intelligence": "max",
                "adversary_intelligence": "max",
                "completion_review_enabled": True,
                "adversary": False,
                "max_adversary_runs": 0,
                "review_limit_format": "explicit",
                "max_completion_returns_before_adversary": 1,
                "max_completion_returns_after_adversary": 0,
                "protected_paths": ["golden"],
                "unrelated_runtime_counter": 99,
            }
            (state / "config.json").write_text(json.dumps(payload), encoding="utf-8")

            result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
            current = result["current_project_config"]
            self.assertTrue(result["status_indicates_active"])
            self.assertEqual(result["apply_guard"], "uncertain")
            self.assertEqual(result["version_compatibility"], "unverified")
            self.assertEqual(current["task"], "TASK.md")
            self.assertEqual(current["coder_mod"], "gpt-5.6-terra")
            self.assertTrue(current["completion_review"])
            self.assertEqual(current["protected_path"], ["golden"])
            self.assertNotIn("unrelated_runtime_counter", current)

    def test_version_compatibility(self) -> None:
        self.assertEqual(INSPECTOR.TARGET_VERSION, "0.5.0")
        self.assertEqual(INSPECTOR._version_compatibility("0.4.1"), "update_required")
        self.assertEqual(INSPECTOR._version_compatibility("0.5.0"), "verified")
        self.assertEqual(INSPECTOR._version_compatibility("0.5.0rc1"), "unverified")
        self.assertEqual(INSPECTOR._version_compatibility("0.6.0"), "unverified")
        self.assertEqual(INSPECTOR._version_compatibility(None), "unverified")

    def test_absent_config_uses_current_defaults_not_legacy_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = INSPECTOR.inspect(Path(tmp), include_bello_version=False, timeout_seconds=1)
        current = result["current_project_config"]
        self.assertFalse(result["config_exists"])
        self.assertEqual(result["apply_guard"], "clear")
        self.assertEqual(current["max_completion_returns_before_adversary"], 1)
        self.assertEqual(current["max_completion_returns_after_adversary"], 0)

    def test_inspector_surfaces_invalid_source_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            (state / "config.json").write_text(
                json.dumps(
                    {
                        "review_limit_format": "future",
                        "multi_agent": [],
                        "fast": "yes",
                        "adversary": "yes",
                        "speed": [],
                    }
                ),
                encoding="utf-8",
            )
            result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
        self.assertFalse(result["source_config_valid"])
        self.assertTrue(any("review_limit_format" in item for item in result["source_config_errors"]))
        self.assertTrue(any("multi_agent" in item for item in result["source_config_errors"]))
        self.assertTrue(any("adversary" in item for item in result["source_config_errors"]))
        self.assertTrue(any("speed" in item for item in result["source_config_errors"]))

    def test_inspector_normalizes_choices_before_model_effort_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            (state / "config.json").write_text(
                json.dumps(
                    {
                        "review_limit_format": "explicit",
                        "coder_mod": " gpt-5.6-luna ",
                        "coder_intelligence": " ULTRA ",
                    }
                ),
                encoding="utf-8",
            )
            result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
        self.assertEqual(result["current_project_config"]["coder_mod"], "gpt-5.6-luna")
        self.assertEqual(result["current_project_config"]["coder_intelligence"], "ultra")
        self.assertFalse(result["source_config_valid"])

    def test_reused_live_pid_does_not_permanently_block_terminal_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            (state / "config.json").write_text(
                json.dumps({"review_limit_format": "explicit", "status": "complete"}),
                encoding="utf-8",
            )
            run_dir = root / ".codex" / "bello-run"
            run_dir.mkdir(parents=True)
            (run_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")
            with mock.patch.object(INSPECTOR, "_pid_identity", return_value="mismatch"):
                recent = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
            old = time.time() - 10
            os.utime(state / "config.json", (old, old))
            with mock.patch.object(INSPECTOR, "_pid_identity", return_value="mismatch"):
                settled = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
        self.assertEqual(recent["process_observation"]["liveness"], "alive")
        self.assertEqual(recent["process_observation"]["identity"], "mismatch")
        self.assertEqual(recent["apply_guard"], "uncertain")
        self.assertEqual(settled["apply_guard"], "clear")

    def test_pid_identity_requires_bello_command_and_matching_workspace(self) -> None:
        root = Path.cwd().resolve()
        with (
            mock.patch.object(INSPECTOR, "_read_process_command", return_value="/venv/bin/python /venv/bin/bello"),
            mock.patch.object(INSPECTOR, "_read_process_cwd", return_value=root),
        ):
            self.assertEqual(INSPECTOR._pid_identity(123, root), "confirmed")
        with mock.patch.object(INSPECTOR, "_read_process_command", return_value="python tests.py"):
            self.assertEqual(INSPECTOR._pid_identity(123, root), "mismatch")
        with (
            mock.patch.object(INSPECTOR, "_read_process_command", return_value='"C:\\venv\\bello.exe" --task T'),
            mock.patch.object(INSPECTOR, "_read_process_cwd", return_value=None),
        ):
            self.assertEqual(INSPECTOR._pid_identity(123, root), "probable")

    def test_confirmed_live_bello_identity_blocks_apply(self) -> None:
        guard, reason = INSPECTOR._apply_guard(
            config_exists=True,
            status="complete",
            config_path=Path("unused"),
            liveness="alive",
            identity="confirmed",
        )
        self.assertEqual(guard, "blocked")
        self.assertIn("confirmed", reason)

    def test_sparse_explicit_config_uses_current_review_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".supervisor"
            state.mkdir()
            (state / "config.json").write_text(
                json.dumps({"review_limit_format": "explicit"}),
                encoding="utf-8",
            )
            result = INSPECTOR.inspect(root, include_bello_version=False, timeout_seconds=1)
        current = result["current_project_config"]
        self.assertEqual(current["max_completion_returns_before_adversary"], 1)
        self.assertEqual(current["max_completion_returns_after_adversary"], 0)

    def test_inspector_preserves_legacy_zero_as_unlimited(self) -> None:
        before, after = INSPECTOR._normalized_review_limits(
            {
                "max_completion_returns_before_adversary": 0,
                "max_completion_returns_after_adversary": 0,
            }
        )
        self.assertEqual(before, "unlimited")
        self.assertEqual(after, "unlimited")

    def test_skill_references_packaged_helpers_and_apply_guard(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("$SKILL_DIR", text)
        self.assertIn("scripts/inspect_config.py", text)
        self.assertIn("scripts/inspect_models.py", text)
        self.assertIn("scripts/validate_config.py", text)
        self.assertIn("active", text.lower())

    def test_model_inspector_summarizes_family_and_effort_separately(self) -> None:
        payload = {
            "models": [
                {
                    "slug": slug,
                    "description": description,
                    "default_reasoning_level": "medium",
                    "supported_reasoning_levels": [
                        {"effort": "high", "description": "deeper"},
                        {"effort": "max", "description": "maximum"},
                    ],
                    "additional_speed_tiers": ["fast"],
                }
                for slug, description in (
                    ("gpt-5.6-sol", "frontier"),
                    ("gpt-5.6-terra", "balanced"),
                    ("gpt-5.6-luna", "affordable"),
                )
            ]
        }

        summary = MODEL_INSPECTOR.summarize_catalog(payload)

        self.assertEqual([item["model"] for item in summary], list(MODEL_INSPECTOR.TARGET_MODELS))
        self.assertEqual(summary[1]["description"], "balanced")
        self.assertEqual(
            summary[2]["supported_efforts"],
            [
                {"effort": "high", "description": "deeper"},
                {"effort": "max", "description": "maximum"},
            ],
        )

    def test_model_inspector_falls_back_when_current_catalog_is_incomplete(self) -> None:
        incomplete = {"models": []}
        complete = {
            "models": [
                {
                    "slug": slug,
                    "description": description,
                    "default_reasoning_level": "medium",
                    "supported_reasoning_levels": [
                        {"effort": "medium", "description": "default"},
                    ],
                }
                for slug, description in (
                    ("gpt-5.6-sol", "frontier"),
                    ("gpt-5.6-terra", "balanced"),
                    ("gpt-5.6-luna", "affordable"),
                )
            ]
        }
        responses = [
            mock.Mock(stdout=json.dumps(incomplete)),
            mock.Mock(stdout=json.dumps(complete)),
        ]

        with mock.patch.object(MODEL_INSPECTOR.subprocess, "run", side_effect=responses) as run:
            models, source = MODEL_INSPECTOR.load_catalog(timeout_seconds=1, bundled_only=False)

        self.assertEqual(source, "bundled fallback")
        self.assertEqual([item["model"] for item in models], list(MODEL_INSPECTOR.TARGET_MODELS))
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][-1], "--bundled")

    def test_policy_rejects_unproven_cross_family_ordering(self) -> None:
        policy = (SKILL / "references" / "SELECTION_POLICY.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "OUTPUT_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("Sol xhigh", policy)
        self.assertIn("Terra max", policy)
        self.assertIn("quality ordering as approximate or uncertain", policy)
        self.assertIn("model comparison", contract)

    def test_policy_routes_tradeoffs_to_current_official_model_economics(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        economics = (SKILL / "references" / "MODEL_ECONOMICS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("MODEL_ECONOMICS.md", skill)
        self.assertIn("https://learn.chatgpt.com/docs/models", economics)
        self.assertIn("https://learn.chatgpt.com/docs/pricing", economics)
        self.assertIn("https://developers.openai.com/api/docs/models/compare", economics)
        self.assertIn("$openai-docs", economics)
        self.assertIn("before choosing any family or effort", economics)
        self.assertIn("Use the retrieved information internally", economics)
        self.assertIn("ChatGPT-authenticated Codex", economics)
        self.assertIn("API-key Codex", economics)

    def test_model_economics_separates_unit_rates_from_trajectory_outcomes(self) -> None:
        economics = (SKILL / "references" / "MODEL_ECONOMICS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("same-ledger unit-price ratios", economics)
        self.assertIn("not expected whole-run ratios", economics)
        self.assertIn("does not publish a fixed", economics)
        self.assertIn("compare candidates internally", economics)
        self.assertIn("Approximate numerical planning priors", economics)
        self.assertIn("Reasoning-depth index", economics)
        self.assertIn("Expected time band", economics)
        self.assertIn("promotional", economics)
        self.assertIn("avoid fake precision", economics)
        self.assertIn("Do not generalize that API multiplier", economics)
        self.assertIn("model-token component", economics)
        self.assertIn("non-token charge", economics)
        self.assertIn("regional-processing", economics)

    def test_advisor_uses_rough_estimates_internally_but_does_not_report_them(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "OUTPUT_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        economics = (SKILL / "references" / "MODEL_ECONOMICS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Do not expose the internal selection process", skill)
        self.assertIn("cost, time, quality estimate", contract)
        self.assertIn("coarse priors", economics)
        self.assertIn("broad relative ranges", economics)
        self.assertIn("fake precision", economics)
        self.assertIn("not benchmark results", economics)

    def test_advisor_uses_only_the_four_allowed_selection_inputs(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        policy = (SKILL / "references" / "SELECTION_POLICY.md").read_text(
            encoding="utf-8"
        )
        economics = (SKILL / "references" / "MODEL_ECONOMICS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("exactly four inputs", skill)
        self.assertIn("Ignore tests and test directories", skill)
        self.assertIn("Do not make their presence or absence change", policy)
        self.assertIn("The advisor receives only the task", economics)
        self.assertIn("must not influence profile or schedule selection", economics)

    def test_revision_coder_requires_an_active_review_and_worthwhile_handoff(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        policy = (SKILL / "references" / "SELECTION_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("explicit revision-coder yes/no decision", skill)
        self.assertIn("dormant in runtime-only runs", policy)
        self.assertIn("worth the handoff", policy)

    def test_skill_requires_one_recommendation_and_advisory_planning(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        policy_text = (SKILL / "references" / "SELECTION_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("one usable Bello configuration", skill_text)
        self.assertIn("built-in Plan Mode", skill_text)
        self.assertIn("do not create a replanning loop", skill_text)
        self.assertIn("Existing implementations", skill_text)
        self.assertIn("existing test suite is not an additional input", policy_text)

    def test_output_contract_requires_only_plan_parameter_and_project_config(self) -> None:
        contract = (SKILL / "references" / "OUTPUT_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Return exactly one selected setup and nothing else", contract)
        self.assertIn("Plan: none", contract)
        self.assertIn("Plan: gpt-5.6-terra max -> PLAN.md", contract)
        self.assertIn("exactly one complete JSON code block", contract)
        self.assertIn("Validate the selected config silently", contract)
        self.assertIn("project-root-relative path", contract)
        self.assertIn("--project-root PROJECT_ROOT --task-file TASK_FILE", contract)
        self.assertIn("Do not include a heading", contract)
        self.assertIn("Do not add `planning`, `plan`, or `plan_path`", contract)
        self.assertNotIn("bello-config-advice/v3", contract)
        self.assertNotIn("selected_config", contract)


if __name__ == "__main__":
    unittest.main()
