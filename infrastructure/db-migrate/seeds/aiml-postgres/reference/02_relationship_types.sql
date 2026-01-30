-- Reference seed data: Relationship types for knowledge graph
-- These are the standard relationship types available in the system

INSERT INTO graph.relationship_types (name, description, inverse_name, source_entity_types, target_entity_types)
VALUES
    ('works_for', 'Employment relationship', 'employs', ARRAY['person'], ARRAY['organization']),
    ('located_in', 'Physical location relationship', 'contains', NULL, ARRAY['location']),
    ('part_of', 'Membership or component relationship', 'has_part', NULL, NULL),
    ('related_to', 'General relationship', 'related_to', NULL, NULL),
    ('created_by', 'Authorship or creation', 'created', NULL, ARRAY['person', 'organization']),
    ('depends_on', 'Dependency relationship', 'required_by', NULL, NULL),
    ('interacts_with', 'Interaction or communication', 'interacts_with', NULL, NULL),
    ('succeeded_by', 'Temporal succession', 'preceded_by', NULL, NULL),
    ('similar_to', 'Similarity relationship', 'similar_to', NULL, NULL),
    ('references', 'Citation or reference', 'referenced_by', NULL, NULL)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    inverse_name = EXCLUDED.inverse_name,
    source_entity_types = EXCLUDED.source_entity_types,
    target_entity_types = EXCLUDED.target_entity_types;
