"""Unit tests for workbench chat prompt builder."""

from veupath_chatbot.ai.prompts.workbench_chat import build_workbench_system_prompt


class TestBuildWorkbenchSystemPrompt:
    def test_includes_site_id(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={"experimentId": "exp-1"},
        )
        assert "plasmodb" in prompt

    def test_includes_experiment_context(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={
                "experimentId": "exp-1",
                "metrics": {"sensitivity": 0.85},
            },
        )
        assert "exp-1" in prompt
        assert "sensitivity" in prompt

    def test_includes_base_system_prompt(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={},
        )
        # Base prompt is substantial (system.md + safety.md + site_hints.md)
        assert len(prompt) > 100

    def test_includes_workbench_instructions(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={},
        )
        assert "Workbench" in prompt or "workbench" in prompt

    def test_empty_context_omits_context_block(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={},
        )
        assert "## Experiment Context" not in prompt

    def test_nonempty_context_includes_json_block(self) -> None:
        prompt = build_workbench_system_prompt(
            site_id="plasmodb",
            experiment_context={"status": "complete"},
        )
        assert "## Experiment Context" in prompt
        assert "```json" in prompt
        assert '"status"' in prompt
