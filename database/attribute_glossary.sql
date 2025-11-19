-- Attribute Glossary Table
CREATE TABLE IF NOT EXISTS attribute_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attribute TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    attribute_type TEXT,
    data_type TEXT,
    parent_attribute TEXT,
    unit TEXT,
    example_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Top-level hierarchy attributes
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, example_value) VALUES
('product_code', 'Unique article number for this specific product variant', 'hierarchy', 'string', NULL, '1047-08-08'),
('family_code', 'Code identifying the product family/line', 'hierarchy', 'string', NULL, '1047'),
('family_name', 'Name of the product family/line group', 'hierarchy', 'string', NULL, 'HYDROSCAND T7012 TVILLING'),
('family_subtitle', 'Optional variant name within family', 'hierarchy', 'string', NULL, 'NON CONDUCTIVE'),
('category_name', 'Product category/classification', 'hierarchy', 'string', NULL, 'HÖGTRYCKSSLANG'),
('chapter', 'Document chapter reference', 'hierarchy', 'string', NULL, 'KAPITEL 1:1 HÖGTRYCKSSLANG'),
('page_number', 'PDF page number where product appears', 'hierarchy', 'number', NULL, '29'),
('configuration_type', 'Configuration variant type', 'hierarchy', 'string', NULL, 'STANDARD'),
('configuration_name', 'Display name for configuration variant', 'hierarchy', 'string', NULL, 'PÅ BOBIN'),
('specifications', 'JSON object containing all technical attributes for this product size', 'hierarchy', 'json', NULL, '{"ID mm": "13.0", "Arb.tr. MPa": "14.0"}'),
('family_construction_details', 'JSON object containing material and construction attributes of product family', 'hierarchy', 'json', NULL, '{"Innertub": "Polyester elastomer", "Temperatur": "-40°C to +100°C"}'),
('family_applications', 'JSON object containing typical application areas', 'hierarchy', 'json', NULL, '{}');

-- Nested family construction attributes
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('Innertub', 'Inner tube material composition and properties', 'material', 'string', NULL, 'family_construction_details', 'Polyester elastomer'),
('Yttertub', 'Outer tube/cover material and properties', 'material', 'string', NULL, 'family_construction_details', 'Olje- och nötningsbeständigt polyuretan'),
('Armering', 'Reinforcement type and material', 'material', 'string', NULL, 'family_construction_details', 'Ett flätat polyesterinlägg'),
('Säkerhetsfaktor', 'Safety factor - ratio of burst pressure to working pressure', 'performance', 'string', NULL, 'family_construction_details', '1:4'),
('Temperatur', 'Operating temperature range for the product family', 'temperature', 'text_range', '°C', 'family_construction_details', '-40°C – +100°C'),
('Utförande', 'Execution/finish - outer appearance and marking', 'material', 'string', NULL, 'family_construction_details', 'Svart hölje, prickklad'),
('Hylsa', 'Recommended sleeve/coupling series for assembly', 'assembly', 'string', NULL, 'family_construction_details', '4200-14-xx'),
('Produktgrupp', 'Product group classification number', 'classification', 'string', NULL, 'family_construction_details', '110');

-- Specification attributes (dimensions)
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('ID mm', 'Inner diameter in millimeters', 'dimension', 'number', 'mm', 'specifications', '13.0'),
('ID tum', 'Inner diameter in inches (1/16 tum)', 'dimension', 'number', 'tum', 'specifications', '1/2'),
('YD mm', 'Outer diameter in millimeters', 'dimension', 'number', 'mm', 'specifications', '23.0'),
('Böjradie mm', 'Minimum bending radius', 'dimension', 'number', 'mm', 'specifications', '200'),
('Vikt kg/m', 'Weight per meter', 'weight', 'number', 'kg/m', 'specifications', '0.85');

-- Specification attributes (pressure and performance)
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('Arb.tr. MPa', 'Working pressure - maximum safe operating pressure', 'pressure', 'number', 'MPa', 'specifications', '14.0'),
('Sprängtr. MPa', 'Burst pressure - maximum pressure before rupture', 'pressure', 'number', 'MPa', 'specifications', '56.0');

-- Specification attributes (material and assembly)
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('Anslutning', 'Connection type and standard', 'assembly', 'string', NULL, 'specifications', 'JIC 37 degrees'),
('Ni-plating', 'Nickel plating specification if applicable', 'material', 'string', NULL, 'specifications', 'Yes'),
('Art.nr Hylsa', 'Article number of recommended sleeve/coupling', 'assembly', 'string', NULL, 'specifications', '4200-14-xx');

-- Specification attributes (packaging and miscellaneous)
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('Förp', 'Packaging unit', 'packaging', 'string', NULL, 'specifications', 'BOX'),
('Ant/förp', 'Quantity per package - pieces per packaging unit', 'packaging', 'number', 'pieces', 'specifications', '10'),
('Min.längd', 'Minimum length - shortest available length', 'dimension', 'number', 'mm', 'specifications', '500'),
('Max längd', 'Maximum length - longest available length', 'dimension', 'number', 'mm', 'specifications', '2000'),
('Typ', 'Type - product type designation', 'classification', 'string', NULL, 'specifications', 'Straight');

-- Standard and technical information
INSERT INTO attribute_glossary (attribute, description, attribute_type, data_type, unit, parent_attribute, example_value) VALUES
('TEKNISK INFORMATION ENLIGT SAE J518 CODE 62', 'Technical information per SAE J518 Code 62 standard', 'standards', 'string', NULL, 'specifications', 'SAE Code 62 Compact');

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_glossary_attribute ON attribute_glossary(attribute);
CREATE INDEX IF NOT EXISTS idx_glossary_attribute_type ON attribute_glossary(attribute_type);
CREATE INDEX IF NOT EXISTS idx_glossary_parent ON attribute_glossary(parent_attribute);
