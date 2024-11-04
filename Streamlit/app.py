import streamlit as st
from streamlit_option_menu import option_menu
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import csv
import subprocess
import re
import tempfile

# Neo4j connection details
NEO4J_URI = "neo4j+s://d5ed894c.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "tcuj-hf-dTuj7b2A-GpCDlroMoCSG_sqiVyzv97BHgw"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Test connection to Neo4j
try:
    with driver.session() as session:
        result = session.run("RETURN 1")
        print("Connection successful")
except Exception as e:
    print(f"Failed to connect to Neo4j: {e}")

# Streamlit UI setup
def streamlit_ui():
    with st.sidebar:
        choice = option_menu('📂 Navigation', ['🏠 Home', '🧑‍💻 GraphRag with Neo4J', '💬 GraphRag ChatBot'])
    
    if choice == '🏠 Home':
        st.title("👋 Welcome to the GraphRag Chatbot")
        st.write("This is the main page. Use the sidebar to navigate to different sections of the app.")
    
    elif choice == '🧑‍💻 GraphRag with Neo4J':
        st.title("📊 GraphRag with Neo4J")
        st.write("This is a GraphRAG approach with a Neo4J knowledge graph. Upload a document, click 'Load Graph,' and view the Neo4J graph.")
        Graphrag_with_Neo4J()

    elif choice == '💬 GraphRag ChatBot':
        st.title("🤖 GraphRag ChatBot")
        if upload_file():
            re_indexing_option()  # Add re-indexing option
        ChatBot()

# Neo4j GraphRAG section
def Graphrag_with_Neo4J():
    load_dotenv()
    driver = None

    # Connect to Neo4j
    if 'neo4j_connected' not in st.session_state:
        st.subheader("Connect to Neo4j Database")
        neo4j_url = st.text_input("Neo4j URL:", value="neo4j+s://<your-neo4j-url>")
        neo4j_username = st.text_input("Neo4j Username:", value="neo4j")
        neo4j_password = st.text_input("Neo4j Password:", type='password')
        connect_button = st.button("Connect")

        if connect_button and neo4j_password:
            try:
                driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_username, neo4j_password))
                st.session_state['driver'] = driver
                st.session_state['neo4j_connected'] = True
                st.success("Connected to Neo4j database.")
            except Exception as e:
                st.error(f"Failed to connect to Neo4j: {e}")
    else:
        driver = st.session_state['driver']
    
    # Upload file and load graph
    if driver:
        uploaded_file = st.file_uploader(label="Upload a document", type=['txt'])
        if not uploaded_file:
            st.warning("Please upload a document")
        else:
            if st.button("Load Graph"):
                GraphRAG(uploaded_file)
            show_graphrag_graph(driver)

# Reindexing option
def re_indexing_option():
    if st.button("Re-index GraphRAG Data"):
        st.write("Re-indexing in progress...")
        try:
            # Initialize and run indexing commands
            subprocess.run("python -m graphrag.index --init --root ./ragtest", shell=True, check=True)
            subprocess.run("python -m graphrag.index --root ./ragtest", shell=True, check=True)
            st.success("Re-indexing completed successfully!")
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to re-index: {e}")

# GraphRAG data loading
def GraphRAG(uploaded_file):
    driver = st.session_state.get('driver', None)
    
    if driver is None:
        st.error("Neo4j is not connected.")
        return
    
    file_content = uploaded_file.getvalue().decode("utf-8").splitlines()
    reader = csv.reader(file_content, delimiter='\t')
    headers = next(reader, None)

    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")

        # Create nodes and define relationships
        previous_node = None
        for row in reader:
            if not any(field.strip() for field in row) or len(row) < 5:
                st.warning(f"Skipping incomplete or empty row: {row}")
                continue

            lead_text, photo_url, title, url, wikipedia_link = row

            # Create node
            query_create_node = """
            MERGE (p:Person {
                title: $title,
                lead_text: $lead_text,
                photo_url: $photo_url,
                url: $url,
                wikipedia_link: $wikipedia_link
            })
            RETURN p
            """
            session.run(query_create_node, {
                "title": title,
                "lead_text": lead_text,
                "photo_url": photo_url,
                "url": url,
                "wikipedia_link": wikipedia_link
            })

            # Example of adding a relationship
            if previous_node:
                query_create_relationship = """
                MATCH (a:Person {title: $previous_title}), (b:Person {title: $current_title})
                MERGE (a)-[:RELATED_TO]->(b)
                """
                session.run(query_create_relationship, {
                    "previous_title": previous_node,
                    "current_title": title
                })

            previous_node = title  # Update previous node

        # Verify data insertion
        node_count = session.run("MATCH (n:Person) RETURN COUNT(n) AS count").single()["count"]
        st.write(f"Nodes inserted: {node_count}")

    st.success("Graph data loaded into Neo4j!")

# Display the Neo4j graph with PyVis
def show_graphrag_graph(driver):
    if driver is None:
        st.error("Neo4j is not connected.")
        return
    
    net_graph = Network(height="750px", width="100%", notebook=False)
    net_graph.toggle_physics(True)

    with driver.session() as session:
        relationship_query = """
        MATCH (n)-[r]->(m)
        RETURN n.title AS start_title, m.title AS end_title, type(r) AS relationship
        """
        result = session.run(relationship_query)

        added_nodes = set()

        for record in result:
            start_title = record["start_title"]
            end_title = record["end_title"]
            relationship = record["relationship"]

            if start_title not in added_nodes:
                net_graph.add_node(start_title, title=start_title, label=start_title)
                added_nodes.add(start_title)
            if end_title not in added_nodes:
                net_graph.add_node(end_title, title=end_title, label=end_title)
                added_nodes.add(end_title)
            net_graph.add_edge(start_title, end_title, title=relationship)

        if not added_nodes:
            st.warning("No relationships found. Displaying isolated nodes.")
            node_query = "MATCH (n) RETURN n.title AS title LIMIT 50"
            node_result = session.run(node_query)

            for record in node_result:
                title = record["title"]
                net_graph.add_node(title, title=title, label=title)

    net_graph.write_html("graph.html")
    with open("graph.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    components.html(html_content, height=750, width=1000)

# File upload function
def upload_file():
    temp_dir = tempfile.gettempdir()  # This will get the system's temporary directory
    uploaded_file = st.file_uploader(label="Upload a document", type=['txt'])
    if uploaded_file:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"File {uploaded_file.name} saved to {temp_dir}.")
        return True
    return False

# ChatBot function
def ChatBot():
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("Type your message here..."):
        st.chat_message("user").write(f"{user_input}")
        st.session_state['messages'].append({"role": "user", "content": user_input})
        # Placeholder response as transformers-related functionality is removed
        assistant_response = "I'm here to assist you with the GraphRag chatbot functionality."

        with st.chat_message("assistant"):
            st.write(assistant_response)
            st.session_state['messages'].append({"role": "assistant", "content": assistant_response})

# Run the Streamlit app UI
streamlit_ui()
