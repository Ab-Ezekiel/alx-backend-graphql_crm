import graphene
from crm.schema import CRMQuery

class Query(CRMQuery, graphene.ObjectType):
    hello = graphene.String(default_value="Hello world")

schema = graphene.Schema(query=Query)
