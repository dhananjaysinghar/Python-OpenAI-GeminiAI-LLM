import mysql.connector
from typing import Any, Optional
import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import cast
import chainlit as cl



class MySQLDatabase:
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        print(f"self.conn = {self.conn}")
        self.cursor = self.conn.cursor()

    def fetch_closest_question(self, query: str):
        """Fetch the most relevant question and answer from the database."""
        sql_query = "SELECT question, answer FROM faq"
        self.cursor.execute(sql_query)
        rows = self.cursor.fetchall()

        # Simple similarity match (can be replaced with advanced NLP)
        best_match = None
        highest_similarity = 0

        for question, answer in rows:
            similarity = len(set(query.lower().split()) & set(question.lower().split()))
            if similarity > highest_similarity:
                best_match = (question, answer)
                highest_similarity = similarity

        return best_match if best_match else ("No match found", "Sorry, I don't have an answer for that.")

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
db: MySQLDatabase
workflow: Runnable


@cl.on_chat_start
async def on_chat_start():
    """Initialize the database and workflow."""
    global db

    # Initialize database
    db = MySQLDatabase(
        host="localhost",
        user="test",
        password="password",
        database="test_db"
    )

    # Initialize LangChain workflow
    api_key = "AIzaSyB"  # Replace with a valid API key
    gemini_llm = GeminiLLM(api_key)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system", """You are an expert in the Employee database with context - {custom_context}, with a focus on 
            queries related to the Employee table and its associated data. If the user asks a query about the 
            Employee database, process it and provide a detailed response. If the query is not related to the 
            Employee database, politely redirect the user by saying: 'This query does not pertain to the Employee 
            database. Please focus on Employee database-related queries, so I can assist you better.'  give the 
            response for user only not all other context"""
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
    print(f"message:{message.content}")
    runnable = cast(Runnable, cl.user_session.get("runnable"))

    msg = cl.Message(content="")
    closest_question, db_answer = db.fetch_closest_question(message.content)
    async for chunk in runnable.astream(
            {"question": message.content, "custom_context": db_answer},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    await msg.send()

@cl.on_stop
async def on_stop():
    """Close the database connection."""
    global db
    if db:
        db.close()

# chainlit run src/com_gemini_ai_example/service/gemini_ai_service_1.py
