# import chainlit
# import mysql.connector
# from langchain_core.runnables import Runnable
# from langchain.schema.runnable import RunnableConfig
# from langchain.prompts import PromptTemplate
# from langchain.schema import StrOutputParser
# import chainlit as cl
# from typing import Any, Optional
# import google.generativeai as genai
# from langchain_core.prompts import ChatPromptTemplate
# from typing import cast
#
#
# # genai.configure(api_key="AIzaSyBN7W70FQWLd3tm446YWw5uA5ufZNOpJIc")
#
#
# class MySQLDatabase:
#     def __init__(self, host, user, password, database):
#         self.conn = mysql.connector.connect(
#             host=host, user=user, password=password, database=database
#         )
#         print(f"self.conn = {self.conn}")
#         self.cursor = self.conn.cursor()
#
#     def fetch_closest_question(self, query: str):
#         """Fetch the most relevant question and answer from the database."""
#         sql_query = "SELECT question, answer FROM faq"
#         self.cursor.execute(sql_query)
#         rows = self.cursor.fetchall()
#
#         # Simple similarity match (can be replaced with advanced NLP)
#         best_match = None
#         highest_similarity = 0
#
#         for question, answer in rows:
#             similarity = len(set(query.lower().split()) & set(question.lower().split()))
#             if similarity > highest_similarity:
#                 best_match = (question, answer)
#                 highest_similarity = similarity
#
#         return best_match if best_match else ("No match found", "Sorry, I don't have an answer for that.")
#
#     def close(self):
#         self.cursor.close()
#         self.conn.close()
#
#
# # Gemini LLM (Simplified for LangChain Compatibility)
# class GeminiLLM(Runnable):
#     def __init__(self, api_key: str):
#         genai.configure(api_key=api_key)
#         self.llm = genai.GenerativeModel("gemini-1.5-flash")
#
#     def invoke(self, prompt: any, config: Optional[RunnableConfig] = None, **kwargs: Any):
#         # Generate content with the model
#         try:
#             response = self.llm.generate_content(f"{prompt}")
#             print(response.text)
#         except Exception as e:
#             print(f"An error occurred while generating content: {e}")
#
#
# # Example usage of the GeminiLLM
# def create_workflow(api_key: str):
#     # Create an instance of GeminiLLM with the API key
#     gemini_llm = GeminiLLM(api_key)
#
#     # Define the prompt template
#     prompt_template = PromptTemplate(
#         input_variables=["user_query", "db_answer"],
#         template="User asked: {user_query}\nDatabase answer: {db_answer}\nRefine this answer for clarity and "
#                  "completeness."
#     )
#
#     # Create a Runnable sequence by chaining the prompt template with the LLM
#     return prompt_template | gemini_llm
#
#
# # Initialize global objects
# db: MySQLDatabase
# workflow: Runnable
#
#
# @cl.on_chat_start
# async def on_chat_start():
#     """Initialize the database and workflow."""
#     global db
#
#     # Initialize database
#     db = MySQLDatabase(
#         host="localhost",
#         user="test",
#         password="password",
#         database="test_db"
#     )
#
#     # Initialize LangChain workflow
#     api_key = "AIzaSyBN7W70FQWLd3tm446YWw5uA5ufZNOpJIc"  # Replace with a valid API key
#
#     # prompt = PromptTemplate(
#     #     input_variables=["user_query", "db_answer"],
#     #     template="User asked: {user_query}\nDatabase answer: {db_answer}\nRefine this answer for clarity and "
#     #              "completeness."
#     # )
#     prompt = ChatPromptTemplate.from_messages([
#         (
#             "system", """You are Employee DB expert and your context is {custom_context}, If someone ask query and
#             that is not about Employee table, kindly ask them to focus on Employee database queries"""
#         ), (
#             "human", "{question}"
#         )
#     ])
#
#     runnable = prompt | create_workflow(api_key) | StrOutputParser()
#     cl.user_session.set("runnable", runnable)
#
#     msg = "Welcome! Ask me a question, and I'll find an answer for you."
#     elements = [cl.Text(name="Welcome", content=msg, display="inline")]
#     # Send a welcome message
#     await cl.Message(content="", elements=elements).send()
#
#
# @cl.on_message
# async def handle_message(message: chainlit.message.Message):
#     """Handle user input, query the DB, and refine response using LangChain."""
#     global db, workflow
#
#     print(f"message:{message.content}")
#     runnable = cast(Runnable, cl.user_session.get("runnable"))
#     # Fetch the closest question and answer from the database
#
#     msg = cl.Message(content="")
#
#     closest_question, db_answer = db.fetch_closest_question(message.content)
#
#     # Send the responses to the user
#     # refined_response = await workflow.invoke({"user_query": message, "db_answer": db_answer})
#
#     async for chunk in runnable.astream({"question": message.content, "custom_context": db_answer}
#             , config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
#                                         ):
#         await msg.stream_token(chunk)
#
#     await msg.send()
#
#
# @cl.on_stop
# async def on_stop():
#     """Close the database connection."""
#     global db
#     if db:
#         db.close()
