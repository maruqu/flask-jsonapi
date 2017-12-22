

def join_query_on_many_relationships_if_needed(query, relationship_fields):
    for relationship_field in relationship_fields:
        query = join_query_on_relationship_if_needed(query, relationship_field)
    return query


def join_query_on_relationship_if_needed(query, relationship_field):
    if not _check_if_query_is_joined_on_relationship(query, relationship_field):
        query = query.join(relationship_field)
    return query


def _check_if_query_is_joined_on_relationship(query, relationship_field):
    joined_models = [entity.class_ for entity in query._join_entities]
    return relationship_field.mapper.class_ in joined_models
