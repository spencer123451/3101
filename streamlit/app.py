import os
import streamlit as st
from py2neo import Graph
from pyvis.network import Network
import streamlit.components.v1 as components
import subprocess

# Neo4j connection details
NEO4J_URI = "neo4j+s://8f24b8ea.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "bbWjvWFoZFFjAxvM54zttfoNFxIe6M11q5cl04Bt9p8"
NEO4J_DATABASE = "neo4j"

# Initialize Neo4j connection in session state
if 'driver' not in st.session_state:
    try:
        st.session_state.driver = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        st.session_state.connection_status = "Connected"
    except Exception as e:
        st.session_state.connection_status = f"Error connecting to Neo4j: {str(e)}"

def test_neo4j_connection():
    """Test connection to the Neo4j database."""
    try:
        result = st.session_state.driver.run("RETURN 'Connection successful!' AS message")
        return result.single()["message"]
    except Exception as e:
        return f"Error connecting to Neo4j: {str(e)}"

def query_neo4j(cypher_query):
    """Query the Neo4j database and return records."""
    try:
        result = st.session_state.driver.run(cypher_query)
        data = result.data()
        if not data:
            st.warning("No results returned from the query.")
        return data
    except Exception as e:
        st.error(f"Error querying Neo4j: {str(e)}")
        return []

def visualize_query_result(records):
    """Visualize the query result as a graph using PyVis."""
    if not records:
        st.warning("No records to display in the graph.")
        return

    net_graph = Network(height="750px", width="100%", notebook=False)
    net_graph.toggle_physics(True)

    added_nodes = set()

    for record in records:
        path = record.get('p', None)
        if path:
            for node in path.nodes:
                node_id = str(node.get("title", node.get("name", None)))
                node_color = "orange" if "title" in node else "lightblue"

                if node_id and isinstance(node_id, (str, int, float)):
                    if node_id not in added_nodes:
                        net_graph.add_node(str(node_id), title=str(node_id), label=str(node_id), color=node_color)
                        added_nodes.add(node_id)

            for rel in path.relationships:
                start_title = str(rel.start_node.get("title", rel.start_node.get("name", None)))
                end_title = str(rel.end_node.get("title", rel.end_node.get("name", None)))

                if (start_title and isinstance(start_title, str) and
                    end_title and isinstance(end_title, str)):
                    net_graph.add_edge(str(start_title), str(end_title), title=str(rel.type))

    net_graph.write_html("graph.html")
    with open("graph.html", "r", encoding="utf-8") as file:
        html_content = file.read()

    components.html(html_content, height=750, width=1000)

def Graphrag_with_Neo4J():
    """Display a predefined graph from Neo4j with visualization."""
    cypher_query = "MATCH p=()-[:IN_COMMUNITY]->() RETURN p LIMIT 50;"
    result = query_neo4j(cypher_query)

    if result:
        visualize_query_result(result)
        st.write("Query Results:")
        st.write(result)
    else:
        st.warning("No results found or error in query execution.")

def run_graphrag_indexing(uploaded_files):
    """Save uploaded files to the ragtest/input folder."""
    input_folder = "ragtest/input"
    os.makedirs(input_folder, exist_ok=True)

    try:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(input_folder, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.write(f"File saved to {file_path}")

        st.write("Files saved successfully. Ready for indexing.")
        return "Files indexed successfully!"
    except Exception as e:
        st.error(f"Error in saving files: {str(e)}")
        return ""

def run_graphrag_indexing_command():
    """Run the indexing command using subprocess."""
    try:
        command = ["python", "-m", "graphrag.index", "--root", "./ragtest"]
        subprocess.run(command, capture_output=True, text=True, check=True)
        st.success("Indexing complete. Graph uploaded to Neo4j")
    except subprocess.CalledProcessError as e:
        st.error(f"Error during indexing: {e.stderr}")

def chatbot_interface():
    """Simple chatbot interface for user queries."""
    st.header("Neo4j Chatbot")
    user_input = st.text_input("Ask a question or enter a query:", "")

    if user_input:
        with open("chatbot_logs.txt", "a") as log_file:
            log_file.write(f"User: {user_input}\n")

        if user_input.lower().startswith("cypher:"):
            query = user_input[7:].strip()
            result = query_neo4j(query)
            st.write("Query Results:")
            st.write(result)
        else:
            response = run_graphrag_query(user_input)
            st.write("Graphrag Query Result:")
            st.write(response)

            with open("chatbot_logs.txt", "a") as log_file:
                log_file.write(f"Chatbot: {response}\n")

def run_graphrag_query(user_input):
    """Run a Graphrag query with subprocess and return the result."""
    try:
        command = [
            "python", "-m", "graphrag.query",
            "--root", "./ragtest",
            "--method", "global",
            user_input
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.replace("🚀", "")

    except subprocess.CalledProcessError as e:
        return f"Error occurred: {e.stderr}"

# Main app logic
st.sidebar.title("Navigation")
menu_options = ["Home", "Run Indexing", "Show Graph", "Chatbot", "Run Cypher Query", "Dashboard"]
choice = st.sidebar.selectbox("Choose an option", menu_options)

if st.session_state.connection_status.startswith("Error"):
    st.error(st.session_state.connection_status)
else:
    st.success(f"Neo4j connection successful: {st.session_state.connection_status}")

if choice == "Home":
    st.title("Welcome to the Neo4j Streamlit App")
    st.write("Use the sidebar to navigate.")

elif choice == "Run Indexing":
    uploaded_files = st.file_uploader("Upload files for indexing", type=["txt", "csv", "json"], accept_multiple_files=True)
    if uploaded_files:
        result = run_graphrag_indexing(uploaded_files)
        st.write(result)
        if st.button("Run Indexing"):
            run_graphrag_indexing_command()
    else:
        st.write("Please upload files to index.")

elif choice == "Show Graph":
    Graphrag_with_Neo4J()

elif choice == "Chatbot":
    chatbot_interface()

elif choice == "Run Cypher Query":
    st.header("Run Custom Cypher Query")
    cypher_query = st.text_area("Enter Cypher Query", "MATCH p=()-[:IN_COMMUNITY]->() RETURN p LIMIT 50;")
    
    if st.button("Execute Query"):
        if cypher_query.strip():
            result = query_neo4j(cypher_query)
            if result:
                st.write("Query Results:")
                visualize_query_result(result)
                st.write(result)
            else:
                st.warning("No results found.")
        else:
            st.warning("Please enter a Cypher query.")

elif choice == "Dashboard":
    st.title("NeoDash Dashboard")
    st.write("Click the link below to open the NeoDash dashboard in a new tab:")
    st.markdown(
        '<a href="https://neodash.graphapp.io" target="_blank">Open NeoDash</a>',
        unsafe_allow_html=True
    )
    st.write("NeoDash is an interactive dashboard for visualizing and exploring Neo4j graph data.")
