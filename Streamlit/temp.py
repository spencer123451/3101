# Import all required packages
import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_chat import message
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components
import pandas as pd
import time
import os
import csv
import subprocess
import re
import tempfile
from nodecreationcopy import node_creation

# Neo4j connection details
NEO4J_URI = "neo4j+ssc://e7ab451a.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "S9rGCAGzGgKvc1uEg9fo5FpjIfkUTc5ECmcKRJNDPuM"
NEO4J_DATABASE="neo4j"

# Initialise driver using Neo4j connection details
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Create constraints, idempotent operation
statements = """
create constraint chunk_id if not exists for (c:__Chunk__) require c.id is unique;
create constraint document_id if not exists for (d:__Document__) require d.id is unique;
create constraint entity_id if not exists for (c:__Community__) require c.community is unique;
create constraint entity_id if not exists for (e:__Entity__) require e.id is unique;
create constraint entity_title if not exists for (e:__Entity__) require e.name is unique;
create constraint entity_title if not exists for (e:__Covariate__) require e.title is unique;
create constraint related_id if not exists for ()-[rel:RELATED]->() require rel.id is unique;
""".split(";")

for statement in statements:
    if len((statement or "").strip()) > 0:
        print(statement)
        driver.execute_query(statement)

# Test connection to Neo4j
try:
    with driver.session() as session:
        result = session.run("RETURN 1")
        print("Connection successful")
except Exception as e:
    print(f"Failed to connect to Neo4j: {e}")

# Streamlit UI setup
def streamlit_ui():
    # Initialize session state if not present
    if 'file_uploaded' not in st.session_state:
        st.session_state['file_uploaded'] = False

    # Create sidebar with navigation options
    with st.sidebar:
        choice = option_menu('📂 Navigation', ['🏠 Home', '📁 Upload File', '🧑‍💻 GraphRag with Neo4J', '💬 GraphRag ChatBot', 'test'])
    
    # Home page with welcome message and instructions
    if choice == '🏠 Home':
        st.title("👋 Welcome to the GraphRag Chatbot")
        st.write("This is the main page. Use the sidebar to navigate to different sections of the app.")
    
    # Upload file section
    elif choice == '📁 Upload File':
        st.title("🗃️ Upload File")
        st.write("Upload a .txt file")
        upload_file()

    elif choice == '🧑‍💻 GraphRag with Neo4J':
        st.title("📊 GraphRag with Neo4J")
        if st.session_state['file_uploaded']:
            st.write("This is a GraphRAG approach with a Neo4J knowledge graph. Click 'Load Graph,' and view the Neo4J graph.")
            Graphrag_with_Neo4J()
        else:
            st.warning("Please upload a file first to use this section.")

    elif choice == '💬 GraphRag ChatBot':
        st.title("🤖 GraphRag ChatBot")
        if st.session_state['file_uploaded']:
            re_indexing_option()  # Add re-indexing option
            ChatBot()
        else:
            st.warning("Please upload a file first to use this section.")

    elif choice == 'test': # from app3.py, need to figure out where it goes
        st.title("Person Node Relationship Chatbot")
        relationshipChatBot()

# File upload function
def upload_file():
    # temp_dir = tempfile.gettempdir()  # This will get the system's temporary directory
    temp_dir = '../ragtest/input'
    # Check if a file is already uploaded in session state
    if st.session_state.get('file_uploaded'):
        st.success(f"File '{st.session_state['uploaded_file_name']}' is already uploaded.")
        # Option to replace the existing uploaded file
        if st.button("Replace Uploaded File"):
            st.session_state['file_uploaded'] = False  # Reset upload state
            st.session_state['uploaded_file_name'] = None
            st.experimental_rerun()  # Refresh the page to re-enable file uploader
    # Only show file uploader if no file is currently stored in session
    if not st.session_state.get('file_uploaded'):
        uploaded_file = st.file_uploader(label="Upload a document", type=['txt'])
        if uploaded_file:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state['uploaded_file'] = uploaded_file  # Save the file path to session state
            st.session_state['uploaded_file_name'] = uploaded_file.name  # Save the file name to session state
            st.session_state['file_uploaded'] = True  # Set a flag to indicate file has been uploaded
            st.success(f"File {uploaded_file.name} saved to {temp_dir}.")
        else:
            st.session_state['file_uploaded'] = False  # Set a flag to indicate file has not been uploaded

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
        uploaded_file = st.session_state['uploaded_file']
        if st.button("Load Graph"):
            GraphRAG(uploaded_file)
        show_graphrag_graph(driver)

def batched_import(statement, df, batch_size=1000):
    """
    Import a dataframe into Neo4j using a batched approach.
    Parameters: statement is the Cypher query to execute, df is the dataframe to import, and batch_size is the number of rows to import in each batch.
    """
    total = len(df)
    start_s = time.time()
    for start in range(0,total, batch_size):
        batch = df.iloc[start: min(start+batch_size,total)]
        result = driver.execute_query("UNWIND $rows AS value " + statement, 
                                      rows=batch.to_dict('records'),
                                      database_=NEO4J_DATABASE)
        print(result.summary.counters)
    print(f'{total} rows in { time.time() - start_s} s.')    
    return total

# GraphRAG data loading
def GraphRAG(uploaded_file):
    driver = st.session_state.get('driver', None)
    
    if driver is None:
        st.error("Neo4j is not connected.")
        return
    
    # Run GraphRAG indexing process
    # command = f'python -m graphrag.index --root ./ragtest' 
    # subprocess.run(command, shell=True, capture_output=True, text=True)
    # print("indexed")
    
    # Node creation
    node_creation()

    # file_content = uploaded_file.getvalue().decode("utf-8").splitlines()
    # reader = csv.reader(file_content, delimiter='\t')
    # headers = next(reader, None)

    # with driver.session() as session:
    #     # Clear existing data
    #     session.run("MATCH (n) DETACH DELETE n")

    #     # Create nodes and define relationships
    #     previous_node = None
    #     for row in reader:
    #         if not any(field.strip() for field in row) or len(row) < 5:
    #             st.warning(f"Skipping incomplete or empty row: {row}")
    #             continue

    #         lead_text, photo_url, title, url, wikipedia_link = row

    #         # Create node
    #         query_create_node = """
    #         MERGE (p:Person {
    #             title: $title,
    #             lead_text: $lead_text,
    #             photo_url: $photo_url,
    #             url: $url,
    #             wikipedia_link: $wikipedia_link
    #         })
    #         RETURN p
    #         """
    #         session.run(query_create_node, {
    #             "title": title,
    #             "lead_text": lead_text,
    #             "photo_url": photo_url,
    #             "url": url,
    #             "wikipedia_link": wikipedia_link
    #         })

    #         # Example of adding a relationship
    #         if previous_node:
    #             query_create_relationship = """
    #             MATCH (a:Person {title: $previous_title}), (b:Person {title: $current_title})
    #             MERGE (a)-[:RELATED_TO]->(b)
    #             """
    #             session.run(query_create_relationship, {
    #                 "previous_title": previous_node,
    #                 "current_title": title
    #             })

    #         previous_node = title  # Update previous node

    #     # Verify data insertion
    #     node_count = session.run("MATCH (n:Person) RETURN COUNT(n) AS count").single()["count"]
    #     st.write(f"Nodes inserted: {node_count}")

    st.success("Graph data loaded into Neo4j!")

# Display the Neo4j graph with PyVis
def show_graphrag_graph(driver):
    if driver is None:
        st.error("Neo4j is not connected.")
        return
    
    net_graph = Network(height="750px", width="100%", notebook=False)
    net_graph.toggle_physics(True)

    with driver.session() as session:
        added_nodes = set()

        # Query for HAS_FINDING relationships
        # finding_query = """
        # MATCH p=()-[:HAS_FINDING]->() 
        # RETURN p
        # """
        # result = session.run(finding_query)

        # for record in result:
        #     path = record["p"]
        #     for node in path.nodes:
        #         # Extract node name based on type
        #         if "title" in node:  # Community node
        #             node_id = node.get("title", None)
        #             node_color = "orange"
        #         elif "summary" in node:  # Finding node
        #             node_id = node.get("summary", None)
        #             node_color = "lightblue"
        #         else:
        #             node_id = None
        #             node_color = "gray"
        #         if node_id is None or node_id == "":  # Skip if no title exists or if it's empty
        #             continue  # Skip if no valid title exists
        #         node_id = str(node_id)  # Ensure it's a string or integer
        #         if node_id not in added_nodes:
        #             net_graph.add_node(node_id, title=node_id, label=node_id, color=node_color)
        #             added_nodes.add(node_id)
        #     for rel in path.relationships:
        #         start_title = rel.start_node.get("title", None) or rel.start_node.get("summary", None)
        #         end_title = rel.end_node.get("title", None) or rel.end_node.get("summary", None)
        #         if start_title is None or end_title is None or start_title == "" or end_title == "":
        #             continue  # Skip relationships with invalid nodes
        #         start_title = str(start_title)
        #         end_title = str(end_title)
        #         # Check if the nodes exist before adding the edge
        #         if start_title not in added_nodes or end_title not in added_nodes:
        #             print(f"Skipping edge due to missing nodes: {start_title} -> {end_title}")
        #             continue  # Skip edges with missing nodes
        #         net_graph.add_edge(start_title, end_title, title=rel.type)

        # Query for IN_COMMUNITY relationships
        community_query = """
        MATCH p=()-[:IN_COMMUNITY]->() 
        RETURN p
        """
        result = session.run(community_query)

        for record in result:
            path = record["p"]
            for node in path.nodes:
                # Extract node name based on type
                if "title" in node:  # Community node
                    node_id = node.get("title", None)
                    node_color = "orange"
                elif "name" in node:  # Entity node
                    node_id = node.get("name", None)
                    node_color = "lightblue"
                else:
                    node_id = None
                    node_color = "gray"
                if node_id is None or node_id == "":  # Skip if no title exists or if it's empty
                    continue  # Skip if no valid title exists
                node_id = str(node_id)  # Ensure it's a string or integer
                if node_id not in added_nodes:
                    net_graph.add_node(node_id, title=node_id, label=node_id, color=node_color)
                    added_nodes.add(node_id)
            for rel in path.relationships:
                start_title = rel.start_node.get("title", None) or rel.start_node.get("name", None)
                end_title = rel.end_node.get("title", None) or rel.end_node.get("name", None)
                if start_title is None or end_title is None or start_title == "" or end_title == "":
                    continue  # Skip relationships with invalid nodes
                start_title = str(start_title)
                end_title = str(end_title)
                # Check if the nodes exist before adding the edge
                if start_title not in added_nodes or end_title not in added_nodes:
                    print(f"Skipping edge due to missing nodes: {start_title} -> {end_title}")
                    continue  # Skip edges with missing nodes
                net_graph.add_edge(start_title, end_title, title=rel.type)

        # relationship_query = """
        # MATCH (n)-[r]->(m)
        # RETURN n.title AS start_title, m.title AS end_title, type(r) AS relationship
        # """
        # for record in result:
        #     start_title = record["start_title"]
        #     end_title = record["end_title"]
        #     relationship = record["relationship"]

        #     if isinstance(start_title, (str, int)) and isinstance(end_title, (str, int)):
        #         if start_title not in added_nodes:
        #             net_graph.add_node(start_title, title=start_title, label=start_title)
        #             added_nodes.add(start_title)
        #         if end_title not in added_nodes:
        #             net_graph.add_node(end_title, title=end_title, label=end_title)
        #             added_nodes.add(end_title)
        #         net_graph.add_edge(start_title, end_title, title=relationship)
        #     else:
        #         print(f"Skipping invalid node: start_title={start_title}, end_title={end_title}")

        # if not added_nodes:
        #     st.warning("No relationships found. Displaying isolated nodes.")
        #     node_query = "MATCH (n) RETURN n.title AS title LIMIT 50"
        #     node_result = session.run(node_query)

        #     for record in node_result:
        #         title = record["title"]
        #         if isinstance(title, (str, int)):
        #             net_graph.add_node(title, title=title, label=title)
        #         else:
        #             print(f"Skipping invalid node: title={title}")

    net_graph.write_html("graph.html")
    with open("graph.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    components.html(html_content, height=750, width=1000)

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

def query_person_relationships(user_input):
    """
    Query Neo4j for Person nodes with a specific name pattern
    and return related nodes and relationships.
    """
    cypher_query = f"""
    MATCH (p:Person)-[r]->(m)
    WHERE p.name CONTAINS $user_input
    RETURN p, r, m LIMIT 5
    """
    with driver.session() as session:
        result = session.run(cypher_query, user_input=user_input)
        return [(record["p"], record["r"], record["m"]) for record in result]

def relationshipChatBot():

    # Initialize conversation history
    if 'conversation' not in st.session_state:
        st.session_state['conversation'] = []

    # Input box for the user
    user_input = st.text_input("You: ", placeholder="Enter a name to search for relationships")
    if st.button("Send") and user_input.strip():
        # Add user message to conversation history
        st.session_state['conversation'].append(("You", user_input))

        # Query Neo4j for Person nodes and their relationships
        results = query_person_relationships(user_input)

        # Format the response based on query results
        if results:
            response = "Here are some connections I found:\n"
            for person, rel, other_node in results:
                response += f"\n- {person['name']} has a relationship '{rel.type}' with {other_node['name']}"
        else:
            response = "No matches found for your query."

        # Append the bot response to the conversation
        st.session_state['conversation'].append(("Bot", response))

    # Display the conversation history
    for i, (role, msg) in enumerate(st.session_state['conversation']):
        message(msg, is_user=(role == "You"), key=f"{role}_{i}")

# Run the Streamlit app UI
streamlit_ui()