from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from typing import Any, Optional
import chainlit as cl
import google.generativeai as genai
from langchain_community.utilities import SQLDatabase
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferMemory


class GeminiLLM(Runnable):
    def __init__(self, llm_key: str):
        genai.configure(api_key=llm_key)
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
api_key = "<api_key>"
gemini_llm = GeminiLLM(api_key)


def get_schema(_):
    return db.get_table_info()


def run_query(query):
    return db.run(query)


memory: ConversationBufferMemory


def get_history(_):
    return memory.load_memory_variables({})["history"]


@cl.on_chat_start
async def on_chat_start():
    global memory
    memory = ConversationBufferMemory()
    print(memory.load_memory_variables({})["history"])
    template = """Based on the table schema below and the conversation history, write a syntactically correct SQL 
    query in plain text that would answer the user's question. Do not include any Markdown formatting, code blocks, 
    or backticks in your response, if possible create a query to get all possible related details about question 
    and get all latest info.
        
        History: {history}
        
        Schema: {schema}
        
        Question: {question}
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
    memory.chat_memory.add_user_message(message.content)
    history = get_history
    template = """This is the conversation so far: {history}

        The answer to the user's question is as follows. Please respond in a suitable format for a report or formal 
        presentation, using markdown formatting. Based on the user's question, do not provide any other information 
        beyond the response. Analyze the {history} and craft your answer meaningfully based on the previous 
        conversation.
        
        Question: {question}
        SQL Query: {query}
        SQL Response: {response}
    """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (
            RunnablePassthrough.assign(query=sql_chain)
            .assign(schema=get_schema, response=lambda variables: run_query(variables["query"]),
                    history=history)
            | prompt
            | gemini_llm
            | StrOutputParser()
    )

    response = full_chain.invoke({"question": message.content, "history": history})
    memory.chat_memory.add_ai_message(response)
    await cl.Message(content=response).send()

# chainlit run src/com_gemini_ai_example/service/gemini_ai_service.py
