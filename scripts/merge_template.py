from pathlib import Path
import re
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Minha tradução"


def merge_files(
    input_directory: Path,
    output_path: Path,
    base_name: str,
    suffix: str,
) -> None:
    part_pattern = re.compile(
        rf"^{re.escape(base_name)}_part_(\d+){re.escape(suffix)}$"
    )

    parts = []
    for path in input_directory.iterdir():
        match = part_pattern.match(path.name)
        if match:
            index = int(match.group(1))
            parts.append((index, path))

    if not parts:
        print(f"No parts found in {input_directory} matching "
              f"{base_name}_part_NN{suffix}")
        sys.exit(1)

    parts.sort(key=lambda item: item[0])

    expected_index = parts[0][0]
    for index, path in parts:
        if index != expected_index:
            print(f"Warning: gap in part sequence before {path.name} "
                  f"(expected part_{expected_index:02d})")
        expected_index = index + 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="latin-1", newline="") as out_file:
        total_lines = 0
        for index, path in parts:
            with path.open("r", encoding="latin-1", newline="") as in_file:
                lines = in_file.readlines()
            out_file.writelines(lines)
            total_lines += len(lines)
            print(f"Merged: {path.name} ({len(lines)} lines)")

    print(f"Created: {output_path} ({total_lines} lines total)")


if __name__ == "__main__":
    base_name = "TEMPLATE"
    suffix = ".DAT"

    input_directory = DATA_DIR / f"{base_name}_parts"
    output_path = DATA_DIR / f"{base_name}{suffix}"

    merge_files(
        input_directory=input_directory,
        output_path=output_path,
        base_name=base_name,
        suffix=suffix,
    )