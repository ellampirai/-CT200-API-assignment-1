
import json

from app.schemas import GenerationOutput


def mock_generate_cases(source_nodes: list[dict]) -> str:
    """Generate deterministic test cases from selected manual sections."""
    if not source_nodes:
        raise ValueError("No source sections were provided.")

    source_text = "\n".join(
        f"{node.get('heading', 'Section')}: {node.get('body', '')}"
        for node in source_nodes
    ).strip()

    if not source_text:
        raise ValueError("Selected sections contain no text.")

    excerpt = source_text[:500]

    cases = {
        "test_cases": [
            {
                "title": "Verify documented requirement",
                "requirement": f"Validate the selected manual content: {excerpt}",
                "preconditions": ["The system under test is available."],
                "steps": [
                    "Open the relevant system or feature.",
                    "Perform the operation described in the selected manual section."
                ],
                "expected_result": "The system behaves according to the selected manual requirement.",
                "priority": "high"
            },
            {
                "title": "Verify invalid input handling",
                "requirement": "Check how the feature handles invalid or unsupported input.",
                "preconditions": ["The relevant feature is available for testing."],
                "steps": [
                    "Open the relevant feature.",
                    "Provide an invalid or unsupported input.",
                    "Observe the system response."
                ],
                "expected_result": "The system handles the invalid input safely and provides an appropriate response.",
                "priority": "medium"
            },
            {
                "title": "Verify repeated operation",
                "requirement": "Check that the documented operation behaves consistently when repeated.",
                "preconditions": ["The system is available and correctly configured."],
                "steps": [
                    "Perform the documented operation once.",
                    "Repeat the same operation.",
                    "Compare both results."
                ],
                "expected_result": "The operation produces consistent results and does not cause unexpected errors.",
                "priority": "medium"
            }
        ]
    }

    return json.dumps(cases)


def generate_cases(source_nodes: list[dict], max_attempts: int = 2) -> GenerationOutput:
    """Validate generated JSON and retry once if the response is invalid."""
    last_error = None

    for _ in range(max_attempts):
        try:
            raw_output = mock_generate_cases(source_nodes)
            parsed = json.loads(raw_output)
            return GenerationOutput.model_validate(parsed)
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            last_error = exc

    raise RuntimeError(
        f"Test-case generation failed after {max_attempts} attempts: {last_error}"
    )
