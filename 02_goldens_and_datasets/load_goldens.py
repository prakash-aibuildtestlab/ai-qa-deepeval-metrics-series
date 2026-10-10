import json # to read json file
from pathlib import Path # to work with file paths 

#This functions takes a file path, Opens the json file in read mode
def load_goldens(file_path):
    with open(file_path, "r") as file:
        return json.load(file) #converts json data into python data
#our JSON file starts with [ ], Python reads it as a list of dictionaries.


if __name__ == "__main__": #Run the code below only when this file is executed directly.
    goldens_path = Path(__file__).parent / "goldens.json" #Path(__file__).parent means the folder where load_goldens.py is located.
    goldens = load_goldens(goldens_path)

    print("AI QA Golden Dataset")
    print("--------------------")

    for golden in goldens: #Loops through each test case in the JSON file.
        print(f"ID: {golden['id']}")
        print(f"Input: {golden['input']}")
        print(f"Expected Output: {golden['expected_output']}")
        print(f"Expected Tools: {golden['expected_tools']}")
        print(f"Tags: {golden['tags']}")
        print()

