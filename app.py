import streamlit as st
from evaluation_copilot.base import MODEL, EvaluationCopilot, RelevanceEvaluationCopilot, CoherenceEvaluationCopilot, FluencyEvaluationCopilot, GroundednessEvaluationCopilot, ImprovementCopilot
from evaluation_copilot.models import EvaluationInput, ImprovementInput
import openai
import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm import OpenAI

client = openai.Client()
client.api_key = ""

user_api_key = st.sidebar.text_input("Enter your OpenAI API Key:", value="", type="password")
if not user_api_key:
    st.error("Please enter your OpenAI API Key in the sidebar.")
else:
    client.api_key = user_api_key
    llm = OpenAI(api_token=user_api_key, model_name=MODEL)

eval_copilot = EvaluationCopilot(client, logging=True)
relevance_eval_copilot = RelevanceEvaluationCopilot(client, logging=True)
coherence_eval_copilot = CoherenceEvaluationCopilot(client, logging=True)
fluency_eval_copilot = FluencyEvaluationCopilot(client, logging=True)
groundedness_eval_copilot = GroundednessEvaluationCopilot(client, logging=True)
improvement_copilot = ImprovementCopilot(client, logging=True)

def get_llm_response(question: str) -> str:
    """
    Function to get the response from an LLM for a given question.
    """
    try:
        response = client.chat.completions.create(
                model=MODEL, messages=[{"role": "system", "content": question}]
            )
        generated_text = response.choices[0].message.content
        return generated_text
    except openai.error.OpenAIError as e:
        st.error(f"An error occurred while fetching the LLM response: {e}")
        return ""
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return ""


# Sidebar buttons for switching between functionalities
app_mode = st.sidebar.radio(
    "Choose the application mode:",
    ("Evaluation Playground", "EvaluationCopilot Usage", "Chat With Evaluations Example")
)

if app_mode == "Evaluation Playground":
    st.title('Evaluation Copilot Demo')

    evaluation_type = st.radio(
        "Select Evaluation Type:",
        ('General', 'Relevance', 'Coherence', 'Fluency', 'Groundedness')
    )

    context = ""
    # The text area is displayed only if the evaluation type requires context
    if evaluation_type in ('Relevance', 'Groundedness'):
        context = st.text_area("Enter context for evaluation:", value="France is a country in Western Europe known for its cities, history, and landmarks.")

    question = st.text_input("Enter your question:", value="What is the capital of France?")

    submit_button = st.button("Submit", disabled=(client.api_key == ""))

    if submit_button:
        llm_answer = get_llm_response(question)
        st.write("## LLM Answer", unsafe_allow_html=True)
        st.info(llm_answer)

        eval_input = EvaluationInput(question=question, answer=llm_answer, context=context if context else None)

        # Evaluate the LLM response based on the selected evaluation type
        if evaluation_type == 'General':
            eval_output = eval_copilot.evaluate(eval_input)
        elif evaluation_type == 'Relevance':
            eval_output = relevance_eval_copilot.evaluate(eval_input)
        elif evaluation_type == 'Coherence':
            eval_output = coherence_eval_copilot.evaluate(eval_input)
        elif evaluation_type == 'Fluency':
            eval_output = fluency_eval_copilot.evaluate(eval_input)
        elif evaluation_type == 'Groundedness':
            eval_output = groundedness_eval_copilot.evaluate(eval_input)

        st.write("## Evaluation", unsafe_allow_html=True)
        st.success(f"Score: {eval_output.score}")
        st.write(f"Justification:\n{eval_output.justification}")

        # Suggest improvements
        improvement_input = ImprovementInput(question=question, answer=llm_answer, score=eval_output.score, justification=eval_output.justification, context=context if context else None)
        improvement_output = improvement_copilot.suggest_improvements(improvement_input)
        st.write("## Improvement Suggestions", unsafe_allow_html=True)
        if improvement_output.question_improvement:
            st.markdown("#### Question Improvement", unsafe_allow_html=True)
            st.markdown(f"> {improvement_output.question_improvement}", unsafe_allow_html=True)

        if improvement_output.answer_improvement:
            st.markdown("#### Answer Improvement", unsafe_allow_html=True)
            st.markdown(f"> {improvement_output.answer_improvement}", unsafe_allow_html=True)

elif app_mode == "EvaluationCopilot Usage":
    st.title("AI Chat with your evaluations")
    uploaded_file = st.file_uploader("Upload a csv for analysis", type=['xlsx', 'csv'])

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]

        if file_type == 'xlsx':
            df = pd.read_excel(uploaded_file, header=None, names=['id', 'questions', 'answers', 'scores', 'justifications'])
        elif file_type == 'csv':
            df = pd.read_csv(uploaded_file)

        sdf = SmartDataframe(df, config={'llm': llm})
        st.write(df.head())

        prompt = st.text_area("Enter Prompt")
        if st.button("Submit"):
            if prompt:
                st.write("PandasAI is generating answer...")
                print("Before")
                resp = sdf.chat(prompt)
                print(resp)
                st.write(resp)
                print("after")
            else:
                st.warning("Please enter a prompt.")

elif app_mode == "Chat With Evaluations Example":
    st.title("Chat With Evaluations Example")

    # Pre-upload the CSV file from the datasets folder
    example_file_path = "datasets/poor.csv"
    try:
        df_example = pd.read_csv(example_file_path)
        sdf_example = SmartDataframe(df_example, config={'llm': llm})
        st.write(df_example.head())

        # Example commands and their outputs
        example_commands = [
            "Summarize the justification for all scores equal to 1",
            "Plot the histogram of evaluations scores",
            "Make a pie chart showing the distribution of scores",
            "Which records have justification showing inaccurate",
            "Give me the records where justification consists of inaccurate answer"
        ]

        st.write("## Example Commands")
        for command in example_commands:
            if st.button(f"Run: {command}"):
                st.write("PandasAI is generating answer...")
                try:
                    resp = sdf_example.chat(command)
                    st.write(resp)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

    except FileNotFoundError:
        st.error(f"File not found: {example_file_path}")