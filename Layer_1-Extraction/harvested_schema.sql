-- database: :memory:
-- ============================================================================
-- ENHANCED PRODUCT DATABASE SCHEMA
-- Supports hierarchical product organization with categories, families,
-- configurations, and flexible specifications
-- ============================================================================

-- ============================================================================
-- LEVEL 0: Page Regions (Header/Footer exclusion zones)
-- ============================================================================
CREATE TABLE IF NOT EXISTS page_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_number INTEGER NOT NULL,
    pdf_name TEXT NOT NULL,
    page_width REAL NOT NULL,
    page_height REAL NOT NULL,
    header_x0 REAL NOT NULL,
    header_y0 REAL NOT NULL,
    header_x1 REAL NOT NULL,
    header_y1 REAL NOT NULL,
    footer_x0 REAL NOT NULL,
    footer_y0 REAL NOT NULL,
    footer_x1 REAL NOT NULL,
    footer_y1 REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(pdf_name, page_number)
);

-- ============================================================================
-- INDEXES for Page Regions
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_page_regions_pdf ON page_regions(pdf_name);
CREATE INDEX IF NOT EXISTS idx_page_regions_page ON page_regions(page_number);

-- ============================================================================
-- LEVEL 1: Categories (Top-level product groupings)
-- ============================================================================
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "HÖGTRYCKSSLANG", "OLJESLANG", etc.
    chapter TEXT,                          -- "KAPITEL 1:1", "KAPITEL 1:2", etc.
    description TEXT,                      -- Category description
    page_number INTEGER,                   -- First page where category appears
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, chapter)
);

-- ============================================================================
-- INDEXES for Categories
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
CREATE INDEX IF NOT EXISTS idx_categories_chapter ON categories(chapter);

-- ============================================================================
-- LEVEL 2: Product Families (Groups of related products)
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    
    -- Basic identification
    family_code TEXT NOT NULL,             -- "1059-01", "1105-43", "1105-10", etc.
    name TEXT NOT NULL,                    -- "HYDROSCAND T8081", "KAPPAFLEX 2K PO"
    subtitle TEXT,                         -- "NON CONDUCTIVE", "HEAVY WALL", etc.
    description TEXT,                      -- Additional product line description
    
    -- Construction details (JSON for flexibility)
    construction_details TEXT,             -- JSON object with material specs, properties, etc.
    /*
    Example JSON structure:
    {
        "inner_tube": "Slät P.T.F.E. (Teflon®)",
        "outer_cover": "Dubbla rostfria stålwireflätor",
        "reinforcement": "Två kompaktflätade stålwireinlägg",
        "safety_factor": "1:4",
        "temperature": {
            "min": -60,
            "max": 260,
            "unit": "°C"
        },
        "standards": ["EN 857 2SC", "DNV", "MED", "MSHA"],
        "marking": "Vävvecklat, blå märkning",
        "hylsa": "4200-11-xx, 4200-23-xx",
        "produktgrupp": "100"
    }
    */
    
    -- Usage and applications (separate column for easy querying)
    applications TEXT,                     -- Free-form usage description
    
    -- Location information
    page_number INTEGER,                   -- Page where family is introduced
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(family_code, name)
);

-- ============================================================================
-- INDEXES for Product Families
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_families_category ON product_families(category_id);
CREATE INDEX IF NOT EXISTS idx_families_code ON product_families(family_code);

-- ============================================================================
-- LEVEL 3: Products (Individual SKUs/Article numbers with specifications)
-- ============================================================================
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,
    
    -- Product identification
    product_code TEXT NOT NULL UNIQUE,     -- Full code: "1059-01-04", "1105-10-04-30"
    variant_suffix TEXT,                   -- "-04", "-06", "-04-30", etc.
    
    -- Configuration type (instead of separate table)
    configuration_type TEXT DEFAULT 'STANDARD',  -- "STANDARD", "REEL", "SPECIAL_LENGTH", etc.
    configuration_name TEXT,               -- "PÅ BOBIN", "SPECIAL ORDER", etc.
    
    -- Specifications (JSON for ultimate flexibility)
    specifications TEXT,                   -- JSON object with all technical specs
    /*
    Example JSON for STANDARD type:
    {
        "type": "STANDARD",
        "id_mm": 6.5,
        "id_tum": "1/4\"",
        "yd_mm": 13.4,
        "working_pressure_mpa": 45.0,
        "bend_radius_mm": 45,
        "weight_kg_per_m": 0.30
    }
    
    Example JSON for REEL type:
    {
        "type": "REEL",
        "dimension": "1/4\"",
        "min_length_m": 170,
        "max_length_m": 230
    }
    */
    
    -- Visual information
    bounding_box TEXT,                     -- JSON: [x0, y0, x1, y1] for location on page
    page_number INTEGER,                   -- Page where product appears
    
    -- Metadata
    notes TEXT,                           -- Additional notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (family_id) REFERENCES product_families(id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES for Products
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_products_family ON products(family_id);
CREATE INDEX IF NOT EXISTS idx_products_code ON products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_config_type ON products(configuration_type);

-- ============================================================================
-- FULL-TEXT SEARCH (FTS5) for Product Families
-- Purpose: Fast, Google-like text search with relevance ranking
-- How: Build specialized search index with tokenization
-- When: For searching descriptions, applications, specifications text
-- ============================================================================
CREATE VIRTUAL TABLE IF NOT EXISTS product_families_fts USING fts5(
    family_code,
    name,
    applications,
    content=product_families,
    content_rowid=id
);

-- ============================================================================
-- TRIGGERS to Keep FTS Index in Sync
-- ============================================================================

-- Trigger: Insert into FTS when new family is added
CREATE TRIGGER IF NOT EXISTS families_ai AFTER INSERT ON product_families BEGIN
    INSERT INTO product_families_fts(rowid, family_code, name, applications)
    VALUES (new.id, new.family_code, new.name, new.applications);
END;

-- Trigger: Update FTS when family is modified
CREATE TRIGGER IF NOT EXISTS families_au AFTER UPDATE ON product_families BEGIN
    UPDATE product_families_fts 
    SET family_code = new.family_code,
        name = new.name,
        applications = new.applications
    WHERE rowid = new.id;
END;

-- Trigger: Delete from FTS when family is removed
CREATE TRIGGER IF NOT EXISTS families_ad AFTER DELETE ON product_families BEGIN
    DELETE FROM product_families_fts WHERE rowid = old.id;
END;
