import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

#Load API Key
load_dotenv(Path(__file__).parent / ".env") # load .env file


def get_llm_response(user_input): #This function takes the user question as input.
    api_key = os.getenv("OPENAI_API_KEY") #This reads the OpenAI key from .env.

    if not api_key: #This checks if the key exists. If not, it stops and shows a clear error.
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")

    client = OpenAI(api_key=api_key) #This creates the OpenAI client.

    response = client.responses.create( #This sends the user question to the LLM.
        model="gpt-4o-mini",
        input=user_input,
    )

    return response.output_text #This returns the actual answer from the LLM.

# Main execution block - the code below runs only when we execute this file directly
if __name__ == "__main__":
    user_input = "Where is my parcel ORD-1042?" #This is our test question

    actual_output = get_llm_response(user_input) #This sends the question to OpenAI and stores the LLM’s answer.

# #Create DeepEval test case - wraps the input and actual output into a format DeepEval understands
    test_case = LLMTestCase( 
        input=user_input,
        actual_output=actual_output,
    )
#here metric tells deepeval use answer relevancy, pass >0.7, incl reason
    metric = AnswerRelevancyMetric(
        threshold=0.7,
        model="gpt-4o-mini",
        include_reason=True,
    )
# Run evaluation which runs the test
    evaluate(
        test_cases=[test_case],
        metrics=[metric],
    )

    print("\nInput:")
    print(user_input)

    print("\nActual LLM Output:")
    print(actual_output)