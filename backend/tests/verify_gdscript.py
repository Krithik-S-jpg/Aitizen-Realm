"""Script to programmatically verify client GDScript syntax and structure."""

import os
import sys


def verify_scripts() -> int:
    """Verifies tab/space and structural formatting of GDScripts recursively."""
    scripts_dir = (
        "../client/scripts"
        if os.path.basename(os.getcwd()) == "backend"
        else "client/scripts"
    )
    if not os.path.exists(scripts_dir):
        print(f"Error: Scripts directory {scripts_dir} not found.")
        return 1

    print(f"Verifying GDScripts in {scripts_dir}...")
    errors = 0

    for root, _dirs, files in os.walk(scripts_dir):
        for file in files:
            if not file.endswith(".gd"):
                continue

            path = os.path.join(root, file)
            print(f"Inspecting {file}...")

            with open(path, encoding="utf-8") as f:
                lines = f.readlines()

            has_extends = False
            bracket_balance = 0

            for idx, line in enumerate(lines, 1):
                if "extends" in line and not line.strip().startswith("#"):
                    has_extends = True

                # Mixed tabs/spaces validation
                stripped = line.lstrip()
                indent = line[: len(line) - len(stripped)]
                if " " in indent and "\t" in indent:
                    print(f"  [ERROR] {file}:{idx} - Mixed tabs and spaces.")
                    errors += 1

                bracket_balance += line.count("(") - line.count(")")
                bracket_balance += line.count("[") - line.count("]")
                bracket_balance += line.count("{") - line.count("}")

            if not has_extends:
                print(f"  [WARNING] {file} - Missing 'extends'.")

            if bracket_balance != 0:
                print(f"  [ERROR] {file} - Unbalanced brackets ({bracket_balance}).")
                errors += 1

    if errors == 0:
        print("Success: All GDScripts verified successfully with zero issues!")
        return 0
    else:
        print(f"Failure: Found {errors} issue(s) in GDScripts.")
        return 1


if __name__ == "__main__":
    sys.exit(verify_scripts())
