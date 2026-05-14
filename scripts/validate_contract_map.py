#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import glob

ROOT = Path(__file__).resolve().parents[1]

def validate_path(path_str):
    """Checks if a path or glob exists."""
    if "*" in path_str:
        matches = glob.glob(str(ROOT / path_str))
        return len(matches) > 0
    else:
        return (ROOT / path_str).exists()

def extract_paths_from_cell(cell):
    """Extracts text inside backticks from a table cell."""
    return re.findall(r"`([^`]+)`", cell)

def extract_validation_paths(cell):
    """Extracts script or test paths from validation command cell."""
    paths = []
    
    # First, extract anything in backticks
    raw_backticks = extract_paths_from_cell(cell)
    for item in raw_backticks:
        # If it contains spaces, it's likely a command, try to extract paths from it
        if " " in item:
            # Look for common path patterns
            found = re.findall(r"(?:scripts/[\w\-\.\*]+|tests/[\w\-\.\*/]+|forgeflow_runtime/[\w\-\.\*]+)", item)
            paths.extend(found)
        else:
            paths.append(item)
    
    # Also look for paths outside backticks just in case
    potential_paths = re.findall(r"(?:scripts/[\w\-\.\*]+|tests/[\w\-\.\*/]+|forgeflow_runtime/[\w\-\.\*]+)", cell)
    paths.extend(potential_paths)
    
    return list(set(paths))

def main():
    contract_map_path = ROOT / "docs" / "contract-map.md"
    if len(sys.argv) > 1:
        contract_map_path = Path(sys.argv[1]).resolve()

    if not contract_map_path.exists():
        print(f"ERROR: Contract map not found at {contract_map_path}", file=sys.stderr)
        sys.exit(1)

    content = contract_map_path.read_text(encoding="utf-8")
    
    # Find the table. Look for lines starting with |
    lines = content.splitlines()
    table_lines = [line for line in lines if line.strip().startswith("|")]
    
    if len(table_lines) < 3: # Header, separator, and at least one row
        print("ERROR: No contract table found in markdown", file=sys.stderr)
        sys.exit(1)

    errors = []
    
    # Skip header and separator
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.split("|") if cell.strip() or (line.startswith("|") and line.endswith("|"))]
        # Depending on how split works with leading/trailing |
        # | a | b | c | -> ['', ' a ', ' b ', ' c ', '']
        cells = [c.strip() for c in line.split("|")][1:-1]
        
        if len(cells) < 5:
            continue
            
        surface = cells[0]
        source_of_truth = cells[1]
        validation_command = cells[3]
        
        # Paths to check
        paths_to_check = []
        paths_to_check.extend(extract_paths_from_cell(surface))
        paths_to_check.extend(extract_paths_from_cell(source_of_truth))
        paths_to_check.extend(extract_validation_paths(validation_command))
        
        for path in paths_to_check:
            # Clean up path (sometimes they have trailing . or , if they were part of a sentence)
            path = path.rstrip(".,")
            
            # Special case for forgeflow_runtime/* and scripts/*.py
            if path == "forgeflow_runtime/*":
                if not (ROOT / "forgeflow_runtime").is_dir():
                    errors.append(f"Missing directory: forgeflow_runtime")
                continue
            if path == "scripts/*.py":
                if not (ROOT / "scripts").is_dir():
                    errors.append(f"Missing directory: scripts")
                continue

            if not validate_path(path):
                errors.append(f"Missing path referenced in contract map: {path}")

    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    print("CONTRACT MAP VALIDATION: PASS")

if __name__ == "__main__":
    main()
