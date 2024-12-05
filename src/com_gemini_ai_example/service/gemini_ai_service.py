from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import Any, Optional
import chainlit as cl
import google.generativeai as genai
from langchain_community.utilities import SQLDatabase
from langchain_core.runnables import RunnablePassthrough


class GeminiLLM(Runnable):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel("gemini-1.5-flash")

    def invoke(self, prompt: any, config: Optional[RunnableConfig] = None, **kwargs: Any):
        # Generate content with the model
        try:
            response = self.llm.generate_content(f"{prompt}")
            print(f"response.text: {response.text}")
            return response.text
        except Exception as e:
            return f"An error occurred while generating content: {e}"


db_uri = "mysql+mysqlconnector://test:password@localhost:3306/test_db"
db = SQLDatabase.from_uri(db_uri)
api_key = "<gemini_ai_key>"
gemini_llm = GeminiLLM(api_key)


def get_schema(_):
    return db.get_table_info()


def run_query(query):
    return db.run(query)


@cl.on_chat_start
async def on_chat_start():
    template = """Based on the table schema below, write a syntactically correct SQL query in plain text that would 
    answer the user's question. Do not include any Markdown formatting, code blocks, or backticks in your response 
    {schema}
            
    Question = {question}
    SQL Query: 
    """
    prompt = ChatPromptTemplate.from_template(template)

    sql_chain = (
            RunnablePassthrough.assign(schema=get_schema)
            | prompt | gemini_llm.bind(stop="\nSQL Result")
            | StrOutputParser()
    )

    cl.user_session.set("sql_chain", sql_chain)
    await cl.Message(content="Welcome! Ask me a question, and I'll find an answer for you.").send()


@cl.on_message
async def on_message(message: cl.Message):
    print(f"message: {message.content}")
    sql_chain = cl.user_session.get("sql_chain")

    template = """The answer to the user's question is response. Please respond suitable for a 
    report or formal presentation and markdown formatted. based on user question, do not give any other info other than response

            Question = {question}
            SQL Query: {query}
            SQL Response: {response}
            """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (RunnablePassthrough.assign(query=sql_chain)
                  .assign(schema=get_schema, response=lambda variables: run_query(variables["query"]))
                  | prompt
                  | gemini_llm
                  | StrOutputParser()
                  )

    response = full_chain.invoke({"question": message.content})
    await cl.Message(content=response).send()

# chainlit run src/com_gemini_ai_example/service/gemini_ai_service_2.py
