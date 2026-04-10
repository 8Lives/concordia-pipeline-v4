"""
Spec Loader — Markdown Parser for the Three-Tier Specification Hierarchy

Parses:
    system_rules.md       → SystemRules
    DM_domain_rules.md    → DomainSpec
    DM_SEX.md, etc.       → VariableSpec
    value_sets/sex_values.md → ValueSet

Parsing approach: section-header-driven using regex to identify ## headers,
then extracting content within each section. Markdown tables are parsed
row-by-row. Decision principles and business rules are passed through as
raw text for LLM prompt injection.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    AllowedValue,
    CrossVariableRule,
    DomainQCCheck,
    DomainSpec,
    MappingPattern,
    OutputSchemaEntry,
    PlausibilityBenchmark,
    ProvenanceFieldDef,
    SynonymMapping,
    SystemRules,
    ValidationRule,
    ValueSet,
    VariableSpec,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sections(text: str, level: int = 2) -> Dict[str, str]:
    """
    Split markdown text by header level into {header_text: body_text} dict.
    level=2 means split on '## ' headers; level=3 on '### ', etc.
    """
    prefix = "#" * level + " "
    sections: Dict[str, str] = {}
    current_header = None
    current_lines: List[str] = []

    for line in text.split("\n"):
        if line.startswith(prefix):
            # Save previous section
            if current_header is not None:
                sections[current_header] = "\n".join(current_lines).strip()
            current_header = line[len(prefix):].strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_header is not None:
        sections[current_header] = "\n".join(current_lines).strip()

    return sections


def _parse_md_table(text: str) -> List[Dict[str, str]]:
    """
    Parse a markdown table into a list of row dicts.
    Handles the header row, separator row (---|---), and data rows.
    Returns empty list if no valid table found.

    NOTE: If text contains multiple tables, only the FIRST is parsed.
    Use _parse_all_md_tables() to get all tables.
    """
    tables = _parse_all_md_tables(text)
    return tables[0] if tables else []


def _parse_all_md_tables(text: str) -> List[List[Dict[str, str]]]:
    """
    Parse ALL markdown tables from text. Returns list of tables,
    each table being a list of row dicts.
    """
    lines = text.split("\n")
    all_tables: List[List[Dict[str, str]]] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for a potential header row (has |)
        if "|" in line and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Check if next line is a separator
            if re.match(r'^[\s|:\-]+$', next_line) and "|" in next_line:
                # Found a table header + separator
                headers = [h.strip() for h in line.split("|")]
                headers = [h for h in headers if h]

                rows: List[Dict[str, str]] = []
                j = i + 2  # skip header and separator
                while j < len(lines):
                    data_line = lines[j].strip()
                    if not data_line or "|" not in data_line:
                        break
                    cells = [c.strip() for c in data_line.split("|")]
                    cells = [c for c in cells if c != ""]
                    if cells:
                        row = {}
                        for k, h in enumerate(headers):
                            row[h] = cells[k] if k < len(cells) else ""
                        rows.append(row)
                    j += 1

                if rows:
                    all_tables.append(rows)
                i = j
                continue
        i += 1

    return all_tables


def _extract_frontmatter(text: str) -> Dict[str, str]:
    """
    Extract key-value metadata from the spec header block.
    Looks for lines like '**Variable:** SEX' before the first ## header.
    """
    meta: Dict[str, str] = {}
    for line in text.split("\n"):
        if line.startswith("## "):
            break
        match = re.match(r'\*\*(.+?):\*\*\s*(.+)', line)
        if match:
            key = match.group(1).strip()
            val = match.group(2).strip()
            meta[key] = val
    return meta


def _extract_source_priority(text: str) -> List[str]:
    """Extract source priority list from a line like 'SEX, SEXCD, GENDER, GENDERCD'."""
    match = re.search(r'\*\*Source Priority List:\*\*\s*(.+)', text)
    if match:
        return [s.strip() for s in match.group(1).split(",") if s.strip()]
    return []


# ---------------------------------------------------------------------------
# Value Set Loader
# ---------------------------------------------------------------------------

def load_value_set(filepath: Path) -> ValueSet:
    """
    Load a value set file (e.g., sex_values.md).

    Expected structure:
        ## Allowed Target Values — table with Value, Definition, CDISC CT Code
        ## Known Source Synonyms — table with Source Value, Maps To, Confidence, First Seen
    """
    text = filepath.read_text(encoding="utf-8")
    meta = _extract_frontmatter(text)
    sections = _split_sections(text, level=2)

    vs = ValueSet(
        name=filepath.stem,
        version=meta.get("Version", ""),
        cdisc_reference=meta.get("CDISC CT Reference", ""),
    )

    # Parse allowed target values
    for section_name, body in sections.items():
        if "allowed target values" in section_name.lower():
            for row in _parse_md_table(body):
                val = row.get("Value", "").strip().strip('"')
                defn = row.get("Definition", "")
                code = row.get("CDISC CT Code", row.get("Notes", ""))
                if val:
                    vs.allowed_values.append(AllowedValue(
                        value=val, definition=defn, cdisc_code=code
                    ))

        elif "known source synonyms" in section_name.lower():
            for row in _parse_md_table(body):
                source_raw = row.get("Source Value", "")
                target = row.get("Maps To", "")
                confidence = row.get("Confidence", "HIGH")
                first_seen = row.get("First Seen", "")

                # Parse comma-separated source values
                source_values = [s.strip() for s in source_raw.split(",") if s.strip()]
                if source_values and target:
                    vs.synonym_mappings.append(SynonymMapping(
                        source_values=source_values,
                        target_value=target,
                        confidence=confidence,
                        first_seen=first_seen,
                    ))

    logger.debug(f"Loaded value set '{vs.name}': {len(vs.allowed_values)} values, "
                 f"{len(vs.synonym_mappings)} synonym groups")
    return vs


# ---------------------------------------------------------------------------
# Variable Spec Loader
# ---------------------------------------------------------------------------

def load_variable_spec(filepath: Path, value_sets_dir: Optional[Path] = None) -> VariableSpec:
    """
    Load a variable spec file (e.g., DM_SEX.md).

    Extracts:
        - Frontmatter metadata (variable, domain, order, required, version)
        - Section 1: Semantic Identity (definition, SDTM reference)
        - Section 2: Allowed Values + source priority
        - Section 3: Mapping Decision Principles + representative patterns
        - Section 4: Business Rules
        - Section 5: Provenance Flags
        - Section 6: Validation Criteria
        - Section 7: Known Limitations
    """
    text = filepath.read_text(encoding="utf-8")
    meta = _extract_frontmatter(text)
    sections = _split_sections(text, level=2)

    spec = VariableSpec(
        variable=meta.get("Variable", filepath.stem.replace("DM_", "")),
        domain=meta.get("Domain", "").split("(")[0].strip(),  # "Demographics (DM)" → "Demographics"
        version=meta.get("Version", ""),
        _raw_spec_text=text,
    )

    # Parse order
    order_str = meta.get("Order", "0")
    try:
        spec.order = int(order_str)
    except ValueError:
        spec.order = 0

    # Parse required status
    required_raw = meta.get("Required", "Optional")
    if required_raw.lower().startswith("yes"):
        spec.required = "Yes"
    elif required_raw.lower().startswith("conditional"):
        spec.required = "Conditional"
    elif required_raw.lower().startswith("no"):
        spec.required = "No"
    else:
        spec.required = "Optional"

    # Parse sections by number prefix pattern
    for section_name, body in sections.items():
        section_lower = section_name.lower()

        # Section 1: Semantic Identity
        if "semantic identity" in section_lower:
            defn_match = re.search(r'\*\*Definition:\*\*\s*(.+?)(?:\n\n|\n\*\*|\Z)', body, re.DOTALL)
            if defn_match:
                spec.definition = defn_match.group(1).strip()
            sdtm_match = re.search(r'\*\*SDTM Reference:\*\*\s*(.+)', body)
            if sdtm_match:
                spec.sdtm_reference = sdtm_match.group(1).strip()

        # Section 2: Allowed Values
        elif "allowed values" in section_lower:
            # Parse all tables in this section
            all_tables = _parse_all_md_tables(body)

            for table in all_tables:
                if not table:
                    continue
                first_row = table[0]
                headers_set = set(first_row.keys())

                # Property/Value table (for numeric vars like AGE)
                if "Property" in headers_set:
                    for row in table:
                        prop = row.get("Property", "")
                        val = row.get("Value", "")
                        if prop == "Data type":
                            spec.data_type = val
                        elif prop == "Missing value":
                            spec.missing_value = val
                        elif prop == "Plausible range":
                            pass  # stored in validation rules
                    # Don't add these rows as allowed values
                    continue

                # Observed Source Patterns table (has "Sponsor" column) — skip
                if "Sponsor" in headers_set:
                    continue

                # Actual allowed values table: has "Value" + ("Definition" or "Notes")
                if "Value" in headers_set and ("Definition" in headers_set or "Notes" in headers_set):
                    for row in table:
                        val = row.get("Value", "").strip().strip('"')
                        defn = row.get("Definition", "")
                        code = row.get("CDISC CT Code", row.get("Notes", ""))
                        if val:
                            spec.allowed_values.append(AllowedValue(
                                value=val, definition=defn, cdisc_code=code
                            ))

            # Detect data type from context if not set by property table
            if "numeric" in body.lower() and "data type" in body.lower():
                spec.data_type = "Numeric"
            if "date" in body.lower() and "iso 8601" in body.lower():
                spec.data_type = "Date (ISO 8601)"

            # Source priority
            spec.source_priority = _extract_source_priority(body)

            # Missing value override for numeric types
            if spec.data_type == "Numeric" or "numeric" in spec.data_type.lower():
                if "empty" in body.lower() and "missing value" in body.lower():
                    spec.missing_value = ""

        # Section 3: Mapping Decision Principles
        elif "mapping decision principles" in section_lower:
            spec.decision_principles = body

            # Extract representative patterns from table
            subsections = _split_sections(body, level=3)
            for sub_name, sub_body in subsections.items():
                if "representative" in sub_name.lower() or "pattern" in sub_name.lower():
                    for row in _parse_md_table(sub_body):
                        src = row.get("Source Value", "").strip().strip('"')
                        tgt = row.get("Target", "").strip()
                        conf = row.get("Confidence", "HIGH")
                        notes = row.get("Notes", "")
                        if src and tgt:
                            spec.mapping_patterns.append(MappingPattern(
                                source_value=src, target_value=tgt,
                                confidence=conf, notes=notes
                            ))

            # Also check for table directly in section (not in subsection)
            if not spec.mapping_patterns:
                # Look for "Representative patterns:" label followed by a table
                for row in _parse_md_table(body):
                    src = row.get("Source Value", "").strip().strip('"')
                    tgt = row.get("Target", "").strip()
                    conf = row.get("Confidence", "HIGH")
                    notes = row.get("Notes", "")
                    if src and tgt:
                        spec.mapping_patterns.append(MappingPattern(
                            source_value=src, target_value=tgt,
                            confidence=conf, notes=notes
                        ))

        # Section 4: Business Rules
        elif "business rules" in section_lower:
            spec.business_rules = body

        # Section 5: Provenance Flags
        elif "provenance" in section_lower:
            for row in _parse_md_table(body):
                name = row.get("Field", "").strip().strip('`')
                ptype = row.get("Type", "Boolean")
                desc = row.get("Description", "")
                if name:
                    spec.provenance_fields.append(ProvenanceFieldDef(
                        name=name, type=ptype, description=desc
                    ))

        # Section 6: Validation Criteria
        elif "validation" in section_lower:
            # Parse subsections for Conformance, Plausibility, Determinism
            subsections = _split_sections(body, level=3)
            for sub_name, sub_body in subsections.items():
                sub_lower = sub_name.lower()
                if "conformance" in sub_lower:
                    spec.validation_rules.append(ValidationRule(
                        category="Conformance", description=sub_body
                    ))
                elif "plausibility" in sub_lower:
                    spec.validation_rules.append(ValidationRule(
                        category="Plausibility", description=sub_body
                    ))
                    # Parse benchmark table if present
                    for row in _parse_md_table(sub_body):
                        cat = row.get("Category", row.get("Value", ""))
                        typical = row.get("Typical Range", "")
                        trigger = row.get("Investigation Trigger", "")
                        if cat and typical:
                            # Parse range like "40–80%"
                            range_match = re.match(r'(\d+)[–\-](\d+)%?', typical)
                            min_pct = float(range_match.group(1)) if range_match else None
                            max_pct = float(range_match.group(2)) if range_match else None
                            spec.plausibility_benchmarks.append(PlausibilityBenchmark(
                                value=cat, min_pct=min_pct, max_pct=max_pct,
                                investigation_trigger=trigger
                            ))
                elif "determinism" in sub_lower:
                    spec.validation_rules.append(ValidationRule(
                        category="Determinism", description=sub_body
                    ))
                elif "separation" in sub_lower:
                    spec.validation_rules.append(ValidationRule(
                        category="Separation Check", description=sub_body
                    ))

        # Section 7: Known Limitations
        elif "known limitations" in section_lower:
            spec.known_limitations = body

    # Link value set if available
    # Convention: value set file is {variable_lower}_values.md
    if value_sets_dir and value_sets_dir.exists():
        vs_name = spec.variable.lower() + "_values.md"
        vs_path = value_sets_dir / vs_name
        if vs_path.exists():
            spec.value_set = load_value_set(vs_path)
            logger.debug(f"Linked value set '{vs_name}' to variable {spec.variable}")

    logger.debug(f"Loaded variable spec '{spec.variable}': "
                 f"order={spec.order}, required={spec.required}, "
                 f"{len(spec.allowed_values)} allowed values, "
                 f"{len(spec.mapping_patterns)} patterns")
    return spec


# ---------------------------------------------------------------------------
# Domain Rules Loader
# ---------------------------------------------------------------------------

def load_domain_rules(filepath: Path) -> DomainSpec:
    """
    Load domain rules file (e.g., DM_domain_rules.md).

    Extracts:
        - Output schema (Section 2 table)
        - Cross-variable dependencies (Section 4 subsections)
        - Domain QC checks (Section 5 subsections)
        - Stoplight criteria (Section 5.5)
    """
    text = filepath.read_text(encoding="utf-8")
    meta = _extract_frontmatter(text)
    sections = _split_sections(text, level=2)

    # Extract domain code from filename or metadata
    domain_match = re.match(r'(\w+)_domain_rules', filepath.stem)
    domain_code = domain_match.group(1) if domain_match else ""

    ds = DomainSpec(
        domain=domain_code,
        version=meta.get("Version", ""),
        controlling_standard=meta.get("Controlling Standard", ""),
    )

    for section_name, body in sections.items():
        section_lower = section_name.lower()

        # Section 1: Scope and Grain
        if "scope" in section_lower and "grain" in section_lower:
            # Extract grain from first line mentioning "record per"
            grain_match = re.search(r'(One record.+?)\.', body)
            if grain_match:
                ds.grain = grain_match.group(1)

        # Section 2: Output Schema
        elif "output schema" in section_lower:
            for row in _parse_md_table(body):
                order_str = row.get("Order", "0")
                try:
                    order = int(order_str)
                except ValueError:
                    order = 0
                variable = row.get("Variable", "")
                data_type = row.get("Data Type", "")
                required = row.get("Required", "Optional")
                desc = row.get("Description", "")
                if variable:
                    ds.output_schema.append(OutputSchemaEntry(
                        order=order, variable=variable,
                        data_type=data_type, required=required,
                        description=desc
                    ))

        # Section 4: Cross-Variable Dependencies
        elif "cross-variable" in section_lower:
            subsections = _split_sections(body, level=3)
            for sub_name, sub_body in subsections.items():
                # Extract section number
                sec_match = re.match(r'(\d+\.\d+)\s+(.+)', sub_name)
                sec_num = sec_match.group(1) if sec_match else ""
                title = sec_match.group(2) if sec_match else sub_name

                # Infer involved variables from title
                variables = []
                for var in ["AGE", "AGEGP", "AGEU", "RACE", "ETHNIC", "ETHNICITY",
                            "USUBJID", "STUDYID", "SUBJID", "RFSTDTC", "RFENDTC", "SEX",
                            "BRTHDTC", "COUNTRY"]:
                    if var.lower() in sub_name.lower():
                        variables.append(var)

                ds.cross_variable_rules.append(CrossVariableRule(
                    name=title, variables=variables,
                    rule_text=sub_body, section=sec_num
                ))

        # Section 5: Domain-Level QC Checks
        elif "domain-level qc" in section_lower or "qc checks" in section_lower:
            subsections = _split_sections(body, level=3)
            for sub_name, sub_body in subsections.items():
                sec_match = re.match(r'(\d+\.\d+)\s+(.+)', sub_name)
                sec_num = sec_match.group(1) if sec_match else ""
                title = sec_match.group(2) if sec_match else sub_name

                # Derive check_id from title
                check_id = title.upper().replace(" ", "_").replace("-", "_")

                ds.domain_qc_checks.append(DomainQCCheck(
                    name=title, check_id=check_id,
                    description=sub_body, section=sec_num
                ))

                # Capture stoplight criteria
                if "stoplight" in sub_name.lower():
                    ds.stoplight_criteria = sub_body

    logger.debug(f"Loaded domain rules '{ds.domain}': "
                 f"{len(ds.output_schema)} schema entries, "
                 f"{len(ds.cross_variable_rules)} cross-variable rules, "
                 f"{len(ds.domain_qc_checks)} QC checks")
    return ds


# ---------------------------------------------------------------------------
# System Rules Loader
# ---------------------------------------------------------------------------

def load_system_rules(filepath: Path) -> SystemRules:
    """
    Load system_rules.md.

    Each ## section is stored as raw text for the corresponding field.
    """
    text = filepath.read_text(encoding="utf-8")
    meta = _extract_frontmatter(text)
    sections = _split_sections(text, level=2)

    sr = SystemRules(
        version=meta.get("Version", ""),
        _raw_text=text,
    )

    for section_name, body in sections.items():
        sl = section_name.lower()
        if "text normalization" in sl:
            sr.text_normalization = body
        elif "null" in sl or "missing" in sl:
            sr.null_handling = body
        elif "date" in sl:
            sr.date_handling = body
        elif "numeric" in sl:
            sr.numeric_handling = body
        elif "code decod" in sl:
            sr.code_decoding = body
        elif "confidence" in sl:
            sr.confidence_grading = body
        elif "provenance" in sl:
            sr.standard_provenance = body
        elif "transformation report" in sl:
            sr.transformation_report = body

    logger.debug(f"Loaded system rules v{sr.version}")
    return sr


# ---------------------------------------------------------------------------
# Full Domain Loader (orchestrates all of the above)
# ---------------------------------------------------------------------------

def load_domain(domain: str, spec_base_dir: Path) -> Tuple[SystemRules, DomainSpec]:
    """
    Load the complete specification for a domain.

    Args:
        domain: Domain code (e.g., "DM")
        spec_base_dir: Path to knowledge_base/ directory

    Returns:
        Tuple of (SystemRules, DomainSpec with variable_specs populated)

    Raises:
        FileNotFoundError: If required spec files are missing
    """
    domain_dir = spec_base_dir / domain
    value_sets_dir = domain_dir / "value_sets"

    # Load system rules
    system_rules_path = spec_base_dir / "system_rules.md"
    if not system_rules_path.exists():
        raise FileNotFoundError(f"System rules not found: {system_rules_path}")
    system_rules = load_system_rules(system_rules_path)

    # Load domain rules
    domain_rules_path = domain_dir / f"{domain}_domain_rules.md"
    if not domain_rules_path.exists():
        raise FileNotFoundError(f"Domain rules not found: {domain_rules_path}")
    domain_spec = load_domain_rules(domain_rules_path)

    # Load all variable specs in the domain directory
    # Variable specs are files matching {DOMAIN}_*.md but NOT domain_rules, Data_Extraction, Specification_Buildout
    skip_patterns = ["domain_rules", "Data_Extraction", "Specification_Buildout"]

    for md_file in sorted(domain_dir.glob(f"{domain}_*.md")):
        if any(skip in md_file.stem for skip in skip_patterns):
            continue

        try:
            var_spec = load_variable_spec(md_file, value_sets_dir)
            domain_spec.variable_specs[var_spec.variable] = var_spec
        except Exception as e:
            logger.warning(f"Failed to load variable spec {md_file.name}: {e}")

    logger.info(f"Loaded domain '{domain}': {len(domain_spec.variable_specs)} variable specs, "
                f"{len(domain_spec.output_schema)} schema entries")

    return system_rules, domain_spec
