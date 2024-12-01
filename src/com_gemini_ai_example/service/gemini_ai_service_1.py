import mysql.connector
from typing import Any, Optional
import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import cast
import chainlit as cl
import json


class MySQLDatabase:
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        print(f"self.conn = {self.conn}")
        self.cursor = self.conn.cursor()

    def get_table_structure(self, table_name):
        cursor = self.conn.cursor(dictionary=True)
        query = f"DESCRIBE {table_name}"
        cursor.execute(query)
        result = cursor.fetchall()
        json_result = json.dumps(result, indent=4)
        return json_result

    def get_multiple_table_structures(self):
        table_names = ["EMP", "DEPT", "SALGRADE"]
        table_structures = {}
        for table in table_names:
            structure = self.get_table_structure(table)
            table_structures[table] = structure
        return json.dumps(table_structures, indent=4)

    def query_with_response(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def is_valid_sql(self, query_txt: str) -> bool:
        query = query_txt.strip()
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE", "USE", "DESCRIBE", "SHOW"]
        query_upper = query.upper()
        if any(query_upper.startswith(keyword) for keyword in sql_keywords) and query.endswith(';'):
            return True
        return False

    def close(self):
        self.cursor.close()
        self.conn.close()


# Gemini LLM (Simplified for LangChain Compatibility)
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


# Initialize global objects
db_service: MySQLDatabase
workflow: Runnable
gemini_llm: GeminiLLM


@cl.on_chat_start
async def on_chat_start():
    """Initialize the database and workflow."""
    global db_service
    global gemini_llm

    # Initialize database
    db_service = MySQLDatabase(
        host="localhost",
        user="test",
        password="password",
        database="test_db"
    )

    # Initialize LangChain workflow
    api_key = "<API_KEY>"  # Replace with a valid API key
    gemini_llm = GeminiLLM(api_key)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system", """You are an expert in the Employee database with context - {custom_context} and also follow 
            the command- {command} strictly, with a focus on queries related to the Employee table and its associated data. If 
            the user asks a query about the Employee database, process it and provide a detailed response. If the 
            query is not related to the Employee database, politely redirect the user by saying: 'This query does not 
            pertain to the Employee database. Please focus on Employee database-related queries, so I can assist you 
            better.'  give the response for user only not all other context"""
        ), (
            "human", "{question}"
        )
    ])

    runnable = prompt | gemini_llm | StrOutputParser()
    cl.user_session.set("runnable", runnable)

    msg = "Welcome! Ask me a question, and I'll find an answer for you."
    elements = [cl.Text(name="Welcome", content=msg, display="inline")]
    # Send a welcome message
    await cl.Message(content="", elements=elements).send()


@cl.on_message
async def on_message(message: cl.Message):
    print(f"message: {message.content}")

    # Retrieve the runnable instance from the session
    runnable = cast(Runnable, cl.user_session.get("runnable"))

    # Step 1: Fetch database structure as context
    db_answer = db_service.get_multiple_table_structures()

    # Step 2: Initialize a response object
    msg = cl.Message(content="")

    # Step 3: First pass through the runnable to generate an intermediate response
    intermediate_response = ""
    async for chunk in runnable.astream(
            {
                "question": message.content,
                "custom_context": db_answer,
                "command": "Generate only the SQL query as a plain text without any additional explanation or "
                           "modifications, so it can be executed directly in the database."
            },
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        intermediate_response += chunk

    print(f"Intermediate Response from Runnable: {intermediate_response}")
    cleaned_response = intermediate_response.replace("```sql", "").replace("```", "").strip()
    print(f"cleaned_response: {cleaned_response}")

    if db_service.is_valid_sql(cleaned_response):
        additional_db_data = db_service.query_with_response(cleaned_response)
        res = gemini_llm.invoke(f"""The answer to the user's question is {additional_db_data}. Please respond in human to 
        understandable format based on user query {message.content}""")
    else:
        res = cleaned_response

    msg = cl.Message(content=res)
    await msg.send()


@cl.on_stop
async def on_stop():
    """Close the database connection."""
    global db_service
    if db_service:
        db_service.close()

# chainlit run src/com_gemini_ai_example/service/gemini_ai_service_1.py
