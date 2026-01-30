-- Reference seed data: Entity types for knowledge graph
-- These are the standard entity types available in the system

INSERT INTO graph.entity_types (name, description, icon, color)
VALUES
    ('person', 'A human individual', 'user', '#3B82F6'),
    ('organization', 'A company, institution, or group', 'building', '#10B981'),
    ('location', 'A physical place or address', 'map-pin', '#F59E0B'),
    ('concept', 'An abstract idea or topic', 'lightbulb', '#8B5CF6'),
    ('event', 'Something that happened at a point in time', 'calendar', '#EC4899'),
    ('product', 'A physical or digital product', 'package', '#06B6D4'),
    ('document', 'A reference to a document or file', 'file-text', '#6B7280'),
    ('technology', 'A technology, tool, or framework', 'cpu', '#EF4444'),
    ('process', 'A business or technical process', 'git-branch', '#84CC16')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color;
