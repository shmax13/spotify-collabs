FROM neo4j:5.14
ENV NEO4J_AUTH=neo4j/knowledgegraphs

# Expose ports for Neo4j
EXPOSE 7474 7687