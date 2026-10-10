import json
from pathlib import Path


def load_goldens(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


if __name__ == "__main__":
    goldens_path = Path(__file__).parent / "goldens.json"
    goldens = load_goldens(goldens_path)

    print("AI QA Golden Dataset")
    print("--------------------")

    for golden in goldens:
        print(f"ID: {golden['id']}")
        print(f"Input: {golden['input']}")
        print(f"Expected Output: {golden['expected_output']}")
        print(f"Expected Tools: {golden['expected_tools']}")
        print(f"Tags: {golden['tags']}")
        print()