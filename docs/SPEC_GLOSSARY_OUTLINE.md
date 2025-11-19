# Spec Glossary - Complete Outline

## Metadata Keys (Top-level product record attributes)

### Product Identification
- `product_code` - Full product article number (e.g., "1047-08-08")
- `Artikelnummer` - Alternative product identifier (often same as product_code)
- `Artikelnr` - Short form of article number

### Family Information
- `family_code` - Product family code (e.g., "1047")
- `family_name` - Full family product name (e.g., "HYDROSCAND T7012 TVILLING")
- `family_subtitle` - Product line variant (e.g., "NON CONDUCTIVE", "HEAVY WALL")

### Category Information
- `category_name` - Product category (e.g., "HÖGTRYCKSSLANG", "PRESSKOPPLINGAR")
- `chapter` - Document chapter reference (e.g., "KAPITEL 1:1 HÖGTRYCKSSLANG")

### Configuration & Variant
- `configuration_type` - Configuration type (e.g., "STANDARD", "REEL", "SPECIAL_LENGTH")
- `configuration_name` - Configuration display name (e.g., "PÅ BOBIN")
- `variant_suffix` - Variant code (e.g., "-04", "-06", "-04-30")

### Location Information
- `page_number` - PDF page where product appears
- `bounding_box` - Visual location coordinates on page [x0, y0, x1, y1]

---

## Specification Keys (Product Technical Attributes)

### Dimensions - Diameter & Size
- `ID mm` - **Inner Diameter in millimeters** (e.g., "13,0")
- `ID tum` - **Inner Diameter in inches** (e.g., "1/2\"")
- `YD mm` - **Outer Diameter in millimeters** (e.g., "20.3")
- `OD mm` - **Outer Diameter in millimeters** (alternative form)

### Pressure & Performance
- `Arb.tr. MPa` - **Working Pressure in megapascals** (e.g., "14,0")
- `Testöverslag` - Test pressure / burst pressure
- `Max tryck` - Maximum pressure

### Physical Properties
- `Böjradie mm` - **Minimum Bend Radius in millimeters** (e.g., "75")
- `Vikt kg/m` - **Weight per meter in kilograms** (e.g., "0.43")
- `Längd` - Length specifications
- `Tjocklek` - Wall thickness

### Material & Construction
- `Innertub` - **Inner tube material** (e.g., "Polyester elastomer")
- `Yttertub` - **Outer tube material** (e.g., "Olje- och nötningsbeständigt polyuretan")
- `Armering` - **Reinforcement type** (e.g., "Ett flätat polyesterinlägg")
- `Förstärkning` - Alternative reinforcement description

### Temperature & Environment
- `Temperatur` - **Temperature range** (e.g., "-40°C – +100°C, luft och vatten max +70°")
- `Operativ temp` - Operating temperature range
- `Lagring temp` - Storage temperature range

### Quality & Standards
- `Säkerhetsfaktor` - **Safety factor** (e.g., "1:4")
- `Utförande` - **Execution/Finish** (e.g., "Svart hölje, prickklad")
- `Märkning` - Marking/Labeling specification
- `Certifiering` - Certifications (e.g., DNV, MED, ISO)

### Assembly & Installation
- `Hylsa` - **Sleeve/Coupling series** (e.g., "4200-14-xx")
- `Koppling` - Coupling information
- `Monteringssätt` - Installation method

### Classification
- `Produktgrupp` - **Product Group number** (e.g., "110")
- `Typ` - Product type

### Connection & Thread
- `Gänga` - Thread type (G, JIC, ORFS, NPTF, BSP)
- `Anslutning` - Connection type
- `Tvärsnittsarea` - Cross-sectional area

### Application & Usage
- `Tillämpning` - Application area
- `Användning` - Usage description
- `Miljö` - Environment/application type (hydraulic, pneumatic, water, etc.)

---

## Family Construction Details (Nested JSON)

These appear in `family_construction_details` and should also have glossary entries:

- `Innertub` - Inner tube material
- `Yttertub` - Outer tube material  
- `Armering` - Reinforcement type
- `Säkerhetsfaktor` - Safety factor
- `Temperatur` - Temperature range
- `Utförande` - Execution/finish
- `Hylsa` - Coupling/sleeve series
- `Produktgrupp` - Product group

---

## Summary Statistics

- **Total Keys Currently in Database:** 7 (from current extraction)
- **Total Possible Keys (Outlined Above):** ~40+
- **Key Categories:**
  - Metadata: 10 keys (product & family identification)
  - Specifications: 25+ keys (technical specs)
  - Construction: 8 keys (materials & assembly)

---

## Notes

1. **Swedish Terms:** Many keys use Swedish abbreviations/full words. Preserve these in canonical form.
2. **Unit Variations:** Same specs may appear in different units (mm vs. tum, MPa vs. bar)
3. **Nested Data:** Some specs appear both at product level and in family construction details
4. **Incomplete:** New products may introduce new keys not yet discovered
5. **Localization:** Some keys may have English equivalents depending on document source

