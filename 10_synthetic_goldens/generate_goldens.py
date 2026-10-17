import json
import os
from pathlib import Path

from dotenv import load_dotenv
from deepeval.synthesizer import Synthesizer


# Load the shared .env file from the project root.
project_root = Path(__file__).resolve().parents[1]
load_dotenv(project_root / ".env") #Loads the project API key

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is missing from the project-level .env file.")


# Locate the source business document. Identifies the source document
policy_path = Path(__file__).parent / "hotel_booking_policy.txt"


# OpenAI acts as the generation model. Creates the Synthesizer
#The LLM reads the policy and generates realistic questions and expected answers.
synthesizer = Synthesizer(
    model="gpt-4o-mini",
    async_mode=False,
    cost_tracking=True,
)


# Generate synthetic test cases from the policy.
#For each document context, DeepEval generates up to two test cases containing:
goldens = synthesizer.generate_goldens_from_docs(
    document_paths=[str(policy_path)],
    include_expected_output=True,
    max_goldens_per_context=6,
)


# Convert the Golden objects into JSON-friendly dictionaries.
goldens_data = []

for index, golden in enumerate(goldens, start=1):
    golden_record = {
        "id": f"SYNTHETIC_{index:03}",
        "input": golden.input,
        "expected_output": golden.expected_output,
        "context": golden.context,
        "source_file": policy_path.name,
        "review_status": "pending_human_review",
    }

    goldens_data.append(golden_record)

    print(f"\nGolden {index}")
    print("-" * 50)
    print(f"Input: {golden.input}")
    print(f"Expected Output: {golden.expected_output}")
    print(f"Context: {golden.context}")


# Save generated goldens for review and future evaluation.
output_path = Path(__file__).parent / "synthetic_goldens.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(goldens_data, file, indent=2, ensure_ascii=False)


print(f"\nGenerated {len(goldens_data)} synthetic goldens.")
print(f"Saved to: {output_path}")
print("\nImportant: These goldens require human review before being used in regression testing.")