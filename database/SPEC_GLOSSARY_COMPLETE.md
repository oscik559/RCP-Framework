# Complete Specification Glossary
## Hydroscand Product Database

**Last Updated:** November 19, 2025  
**Total Keys:** 34 specification attributes + metadata columns

---

## Product Column Keys (Metadata)

These are the primary attributes of each product record:

| Attribute | Description |
|-----------|-------------|
| `product_code` | Full unique product article number (e.g., "1047-08-08", "1103-03-04") |
| `family_id` | Reference to product family |
| `family_name` | Product family name (e.g., "HYDROSCAND T7012 TVILLING", "KAPPAFLEX 2K PO") |
| `category_name` | Product category (e.g., "HÖGTRYCKSSLANG", "PRESSKOPPLINGAR") |
| `variant_suffix` | Variant code appended to base product code (e.g., "-04", "-06", "-04-30") |
| `configuration_type` | Configuration variant type (STANDARD, REEL, SPECIAL_LENGTH, etc.) |
| `configuration_name` | Display name for configuration (e.g., "PÅ BOBIN", "SPECIAL ORDER") |
| `page_number` | PDF page where product appears |
| `chapter` | Document chapter reference (e.g., "KAPITEL 1:1 HÖGTRYCKSSLANG") |
| `bounding_box` | Visual coordinates on page [x0, y0, x1, y1] |
| `notes` | Additional product notes |

---

## Specification Keys (Found in Product Data)

### **Dimensions & Sizing**

| Key | Description |
|-----|-------------|
| `ID mm` | Inner Diameter in millimeters (e.g., "13,0", "6,5", "8,0") |
| `ID tum` | Inner Diameter in inches (e.g., "1/2\"", "1/4\"", "5/16\"") |
| `YD mm` | Outer Diameter in millimeters (e.g., "20.3", "11,8", "13,6") |
| `A` | Dimension A in mm (component measurement) |
| `B` | Dimension B in mm (component measurement) |
| `C` | Dimension C in mm (component measurement) |
| `Längd` | Length in millimeters (e.g., "21,5 mm", "29,5 mm") |
| `Höjd` | Height in millimeters (component dimension) |
| `Dimension` | Nominal product size (e.g., "1/4\"", "5/16\"") |
| `Rör` | Tube/hose diameter in mm (e.g., "6 mm", "8 mm") |
| `Flänsstorlek` | Flange size (e.g., "1/2\"") |
| `Huvud` | Head/connector size (e.g., "1/4\"", "3/8\"") |
| `Studs Ø` | Stud/bolt diameter in mm (e.g., "6 mm") |

### **Pressure & Performance**

| Key | Description |
|-----|-------------|
| `Arb.tr. MPa` | **Working Pressure** in megapascals - maximum safe operating pressure (e.g., "14,0", "29,0", "25,0") |
| `Sprängtr. MPa` | **Burst/Test Pressure** in megapascals - pressure at which hose ruptures (e.g., "100,0") |
| `Böjradie mm` | **Minimum Bend Radius** in millimeters - smallest safe bending curve (e.g., "40", "55", "75") |

### **Weight & Physical Properties**

| Key | Description |
|-----|-------------|
| `Vikt kg/m` | **Weight per meter** in kilograms - hose/component mass per linear meter (e.g., "0,18", "0,22", "0,43") |

### **Connection & Threading**

| Key | Description |
|-----|-------------|
| `Gänga` | **Thread type** - connection thread specification (e.g., "G 1/8\"" = ISO 228 gas thread) |
| `Bult-Gänga` | **Bolt thread** - metric thread specification (e.g., "M 10 x 1,0") |
| `Artikelnr` | **Article Number** - product identifier/code |
| `Artikel nummer` | **Article Number** (alternative form) |
| `Artikelnummer` | **Article Number** (alternative form) |
| `Artikelnr.` | **Article Number** (with period) |

### **Assembly & Coupling**

| Key | Description |
|-----|-------------|
| `Hylsa` | **Sleeve/Coupling series** - compatible coupling designation (e.g., "4200-14-03", "4200-07-04") |
| `Används med` | **Used with** - compatible product or assembly designation |
| `Slang ID` | **Hose ID reference** - which hose diameter this fits |

### **Component-Specific Specifications**

| Key | Description |
|-----|-------------|
| `Hölje` | **Housing/Cover color** - outer cover color (e.g., "Blå" = Blue, "Svart" = Black) |
| `WEO` | **Width/Exterior dimension** in mm - component external measurement |
| `Nyckelvidd` | **Wrench size** in mm - hex key/wrench size needed for installation/tightening |
| `Ant/förp` | **Quantity per package** - pieces per packaging unit (e.g., "10") |
| `Min.längd` | **Minimum length** - shortest available length (e.g., "130", "170") |
| `Max längd` | **Maximum length** - longest available length (e.g., "190", "230") |
| `Typ` | **Type** - product type designation (e.g., "IR") |

### **Standards & Technical Info**

| Key | Description |
|-----|-------------|
| `TEKNISK INFORMATION ENLIGT SAE J518 CODE 62` | **Technical information per SAE standard** - compliance notation |

---

## Family Construction Keys (Nested in family_construction_details)

These attributes describe the overall product family characteristics:

| Key | Description |
|-----|-------------|
| `Innertub` | **Inner tube material** - fluid-contact material (e.g., "Polyester elastomer", "Slät P.T.F.E. (Teflon®)") |
| `Yttertub` | **Outer tube material** - external cover (e.g., "Olje- och nötningsbeständigt polyuretan", "Dubbla rostfria stålwireflätor") |
| `Armering` | **Reinforcement** - structural reinforcement type (e.g., "Ett flätat polyesterinlägg", "Två kompaktflätade stålwireinlägg") |
| `Temperatur` | **Temperature range** - operating temperature limits (e.g., "-40°C – +100°C, luft och vatten max +70°") |
| `Säkerhetsfaktor` | **Safety factor** - burst pressure to working pressure ratio (e.g., "1:4", "1:5") |
| `Utförande` | **Execution/Finish** - surface finish description (e.g., "Svart hölje, prickklad" = Black cover with pattern) |
| `Hylsa` | **Coupling/Sleeve series** - compatible coupling designation |
| `Produktgrupp` | **Product group** - internal classification number (e.g., "110", "100") |

---

## Summary

- **Total Specification Keys:** 34
- **Metadata Columns:** 11
- **Key Categories:**
  - Dimensions: 13 keys (diameters, lengths, heights)
  - Pressure & Performance: 3 keys
  - Weight & Properties: 1 key
  - Connection & Threading: 4 keys
  - Assembly & Coupling: 3 keys
  - Component-Specific: 7 keys
  - Standards: 1 key
  - Family-level: 8 keys

---

## Notes

1. **Swedish Terminology:** All keys and many values use Swedish technical terms. Preserved as-is.
2. **Decimal Format:** Swedish format uses comma (,) as decimal separator (e.g., "13,0" = 13.0)
3. **Variants:** Some keys appear in multiple forms (e.g., `Artikelnr`, `Artikel nummer`, `Artikelnummer`)
4. **Unit Variations:** Same specs may appear in different units (e.g., `ID mm` + `ID tum`)
5. **Scaling:** New products may introduce new keys - add to this glossary incrementally

---

## Usage in analyze_with_llm Prompt

When LLM analyzes product data, it should reference this glossary:

```
User Question: "What is the working pressure for 1047-08-08?"
Data Contains: {"Arb.tr. MPa": "14,0"}
Glossary Maps: "Arb.tr. MPa" → "Working Pressure in megapascals"
LLM Answer: "The working pressure for product 1047-08-08 is 14.0 MPa."
```

