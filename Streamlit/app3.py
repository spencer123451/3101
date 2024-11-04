import streamlit as st
from neo4j import GraphDatabase
from streamlit_chat import message  # Optional, for chat layout
import os

# Retrieve Neo4j credentials securely (replace with your method for managing secrets)
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d5ed894c.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Validate if credentials are present
if not NEO4J_PASSWORD:
    st.error("Neo4j password is not set. Please ensure your credentials are securely provided.")
else:
    # Neo4j connection setup
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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

    st.title("Person Node Relationship Chatbot")

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
    for role, msg in st.session_state['conversation']:
        message(msg, is_user=(role == "You"))
