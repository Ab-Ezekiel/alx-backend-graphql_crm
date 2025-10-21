# alx_backend_graphql/schema.py
import graphene

class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")

# create the schema object expected by graphene-django config
schema = graphene.Schema(query=Query)
