import streamlit as st
from snowflake.core import Root # requires snowflake>=0.8.0
from snowflake.cortex import Complete
from snowflake.snowpark.context import get_active_session
import pandas as pd
import datetime
import uuid
import time
import re


MODELS = [
    "mistral-large",
    "snowflake-arctic",
    "mistral-7b",
    "llama3-8b",
]

def imdb_url(imdb_id):
    """
    Return a list of imdb links from the provided context
    """
    base_url = "https://www.imdb.com/title/"
    imdb_url = base_url + imdb_id
    return imdb_url
    

def init_messages():
    """
    Initialize the session state for chat messages. If the session state indicates that the
    conversation should be cleared or if the "messages" key is not in the session state,
    initialize it as an empty list.
    """
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []
    if "feedback_list" not in st.session_state:
        st.session_state.feedback_list = []


def init_service_metadata():
    """
    Initialize the session state for cortex search service metadata. Query the available
    cortex search services from the Snowflake session and store their names and search
    columns in the session state.
    """
    if "service_metadata" not in st.session_state:
        services = session.sql("SHOW CORTEX SEARCH SERVICES;").collect()
        service_metadata = []
        if services:
            # TODO: remove loop once changes land to add the column metadata in SHOW
            for s in services:
                svc_name = s["name"]
                svc_search_col = session.sql(
                    f"DESC CORTEX SEARCH SERVICE {svc_name};"
                ).collect()[0]["search_column"]
                service_metadata.append(
                    {"name": svc_name, "search_column": svc_search_col}
                )

        st.session_state.service_metadata = service_metadata


def init_config_options():
    """
    Initialize the configuration options in the Streamlit sidebar. Allow the user to select
    a cortex search service, clear the conversation, toggle debug mode, and toggle the use of
    chat history. Also provide advanced options to select a model, the number of context chunks,
    and the number of chat messages to use in the chat history.
    """
    st.sidebar.selectbox(
        "Select cortex search service:",
        [s["name"] for s in st.session_state.service_metadata],
        key="selected_cortex_search_service",
    )

    st.sidebar.button("Clear conversation", key="clear_conversation")
    st.sidebar.toggle("Debug", key="debug", value=False)
    st.sidebar.toggle("Use chat history", key="use_chat_history", value=True)

    with st.sidebar.expander("Advanced options"):
        st.selectbox("Select model:", MODELS, key="model_name")
        st.number_input(
            "Select number of context chunks",
            value=3,
            key="num_retrieved_chunks",
            min_value=1,
            max_value=10,
        )
        st.number_input(
            "Select number of messages to use in chat history",
            value=5,
            key="num_chat_messages",
            min_value=1,
            max_value=10,
        )

    st.sidebar.expander("Session State").write(st.session_state)


def query_cortex_search_service(query, columns = [], filter={}):
    """
    Query the selected cortex search service with the given query and retrieve context documents.
    Display the retrieved context documents in the sidebar if debug mode is enabled. Return the
    context documents as a string.

    Args:
        query (str): The query to search the cortex search service with.

    Returns:
        str: The concatenated string of context documents.
    """
    db, schema = session.get_current_database(), session.get_current_schema()

    cortex_search_service = (
        root.databases[db]
        .schemas[schema]
        .cortex_search_services[st.session_state.selected_cortex_search_service]
    )

    context_documents = cortex_search_service.search(
        query, columns=columns, filter=filter, limit=st.session_state.num_retrieved_chunks
    )
    results = context_documents.results

    context_str = ""
    for i, r in enumerate(results):
        context_str += f"Context document {i+1}: {r['TITLE']} {r['OVERVIEW']}\n\n"

    if st.session_state.debug:
        st.sidebar.text_area("Context documents", context_str, height=500)

    return context_str, results


def get_chat_history():
    """
    Retrieve the chat history from the session state limited to the number of messages specified
    by the user in the sidebar options.

    Returns:
        list: The list of chat messages from the session state.
    """
    start_index = max(
        0, len(st.session_state.messages) - st.session_state.num_chat_messages
    )
    return st.session_state.messages[start_index : len(st.session_state.messages) - 1]


def complete(model, prompt):
    """
    Generate a completion for the given prompt using the specified model.

    Args:
        model (str): The name of the model to use for completion.
        prompt (str): The prompt to generate a completion for.

    Returns:
        str: The generated completion.
    """
    return Complete(model, prompt).replace("$", "\$")


def make_chat_history_summary(chat_history, question):
    """
    Generate a summary of the chat history combined with the current question to extend the query
    context. Use the language model to generate this summary.

    Args:
        chat_history (str): The chat history to include in the summary.
        question (str): The current user question to extend with the chat history.

    Returns:
        str: The generated summary of the chat history and question.
    """
    prompt = f"""
        [INST]
        Based on the chat history below and the question, generate a query that extend the question
        with the chat history provided. The query should be in natural language. 
        Answer with only the query.

        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {question}
        </question>
        [/INST]
    """

    summary = complete(st.session_state.model_name, prompt)

    if st.session_state.debug:
        st.sidebar.text_area(
            "Chat history summary", summary.replace("$", "\$"), height=150
        )

    return summary


def create_prompt(user_question):
    """
    Create a prompt for the language model by combining the user question with context retrieved
    from the cortex search service and chat history (if enabled). Format the prompt according to
    the expected input format of the model.

    Args:
        user_question (str): The user's question to generate a prompt for.

    Returns:
        str: The generated prompt for the language model.
    """
    if st.session_state.use_chat_history:
        chat_history = get_chat_history()
        if chat_history != []:
            question_summary = make_chat_history_summary(chat_history, user_question)
            prompt_context, results = query_cortex_search_service(
                question_summary,
                columns=["TITLE", "IMDB_ID","OVERVIEW"],
                filter={"@and": [{"@eq": {"ORIGINAL_LANGUAGE": "en"}}]},)
        else:
            prompt_context, results = query_cortex_search_service(
                user_question,
                columns=["TITLE", "IMDB_ID", "OVERVIEW"],
                filter={"@and": [{"@eq": {"ORIGINAL_LANGUAGE": "en"}}]},)
    else:
        prompt_context, results = query_cortex_search_service(
            user_question,
            columns=["TITLE", "IMDB_ID", "OVERVIEW"],
            filter={"@and": [{"@eq": {"ORIGINAL_LANGUAGE": "en"}}]},
        )
        chat_history = ""

    prompt = f"""
            [INST]
    You are an AI movie recommendation assistant with RAG capabilities. When a user asks for movie suggestions or information about films, you will be provided with relevant movie data between <context> and </context> tags.
    Your task is to:
    Always use the movie titles from the provided context. Never output placeholders like "Untitled (Context document X)".
    Provide relevant movie suggestions based on the user's preferences and query.
    Include a brief, engaging explanation for why each movie is recommended.
    Your responses should:
    Be coherent, concise, and directly address the user's request.
    Draw only from the provided context to tailor recommendations.
    If the user asks a question about movies that cannot be answered with the given context or chat history, simply state: "I'm sorry, but I don't have enough information to answer that question or make a recommendation based on that criteria."
    Avoid phrases like "according to the provided context" or mentioning the RAG system. Instead, present the information as if you have comprehensive knowledge about films.".
                    
            <chat_history>
            {chat_history}
            </chat_history>
            <context>          
            {prompt_context}
            </context>
            <question>  
            {user_question}
            </question>
            [/INST]
            Answer:
           """
    return prompt, results


def clean_string(input_string):
    # Replace curly quotes with standard quotes
    clean_str = input_string.replace('“', '').replace('"', '')
    clean_str = clean_str.replace('‘', "").replace('\'', '')
    
    # Remove any other non-standard characters
    clean_str = re.sub(r'[^\x00-\x7F]+', '', clean_str)
    
    return clean_str
    
def log_answer(q_id, question, answer, feedback, response_time, time):
    conn = session.connection
    cursor = conn.cursor()
    # Clean each value before inserting
    question = clean_string(question)
    answer = clean_string(answer)
    
    insert_sql = f"""INSERT INTO LOGGING (QUESTION_ID, QUESTION, ANSWER, FEEDBACK, RESPONSE_TIME, TIMESTAMP)
                    VALUES ('{q_id}', '{question}', '{answer}', '{feedback}', '{response_time}', '{time}')"""
    cursor.execute(insert_sql)

    
def feedback_neg():
    st.toast(f"Feedback submitted",  icon='👎')
    conn = session.connection
    cursor = conn.cursor()
    update_query =  f"""update logging set feedback = 0 where question_id = '{st.session_state['q_id']}'"""
    cursor.execute(update_query)


def main():
    st.title(f":movie_camera: Movie Recommender with Snowflake Cortex")

    init_service_metadata()
    init_config_options()
    init_messages()

    icons = {"assistant": "❄️", "user": "👤"}
    
    disable_chat = (
        "service_metadata" not in st.session_state
        or len(st.session_state.service_metadata) == 0
    )
    
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=icons[message["role"]]):
            st.markdown(message["content"])

    if question := st.chat_input("Ask a question...", disabled=disable_chat):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": question})
        
            # Display user message in chat message container
            with st.chat_message("user", avatar=icons["user"]):
                st.markdown(question.replace("$", "\$"))
                
        
            # Display assistant response in chat message container
            with st.chat_message("assistant", avatar=icons["assistant"]):
                message_placeholder = st.empty()
                question = question.replace("'", "")
                prompt, results = create_prompt(question)
                start_time = time.time()
             
                with st.spinner("Thinking..."):
                    generated_response = complete(
                        st.session_state.model_name, prompt
                    )
                    # build references table for citation
                    markdown_table = "###### References \n\n| Movie Title | Link |\n|-------|-----|\n"
                    for ref in results:
                        markdown_table += f"| {ref['TITLE']} | [Link]({imdb_url(ref['IMDB_ID'])}) |\n"
                    message_placeholder.markdown(generated_response + "\n\n" + markdown_table+ "\n\n")
                    # feedback
                    end_time = time.time()
                    st.session_state['q_id'] = uuid.uuid4()
                    log_answer(st.session_state['q_id'], question, generated_response, 1, end_time- start_time, datetime.datetime.now())
                   

                with st.container(border=False):
                    col1, col2 = st.columns([1,1])
                    with col1:
                        st.button(label = "👎", on_click=feedback_neg)
            
                    
        # Add assistant message to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": generated_response,
                "question": question
            })
        
            



if __name__ == "__main__":
    session = get_active_session()
    root = Root(session)
    main()