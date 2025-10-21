# alx_backend_graphql_crm/schema.py
import graphene

class Query(graphene.ObjectType):
    # a single field 'hello' of type String that returns a default value
    hello = graphene.String(default_value="Hello, GraphQL!")

# create the schema object expected by graphene-django config
schema = graphene.Schema(query=Query)

