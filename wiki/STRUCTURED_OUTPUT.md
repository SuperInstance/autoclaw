# Generating Structured Output

Creating validated, formatted output in required formats.

---

## 🎯 Output Format Types

**JSON**: Machine-readable, schema-validatable
**CSV**: Spreadsheet-compatible, simple
**XML**: Hierarchical, standards-compliant
**Markdown**: Human-readable, documentation
**YAML**: Configuration-friendly, readable

---

## ✅ Output Validation

```
Generate raw output
    ↓
Parse to schema
    ↓
Validate structure
    ↓
Check required fields
    ↓
Type checking
    ↓
Format conversion
```

---

## 📋 Schema Definition

```yaml
fields:
  - name: title
    type: string
    required: true
  - name: confidence
    type: float
    range: [0, 1]
    required: true
  - name: tags
    type: array
    items: string
```

---

## 🔄 Format Conversion

- JSON → CSV
- CSV → JSON
- YAML → JSON
- Markdown → HTML
- All → human summary

---

## 🔗 See Also

- [DATA_AUTOMATION.md](DATA_AUTOMATION.md)
- [DATA_PIPELINE_DESIGN.md](DATA_PIPELINE_DESIGN.md)
- [API_REFERENCE.md](API_REFERENCE.md)

**See also**: [HOME.md](HOME.md)
