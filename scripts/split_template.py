from pathlib import Path
import re
import sys

DATA_DIR = Path(__file__).resolve().parent.parent / "Minha tradução"


def split_file(
    input_path: Path,
    output_directory: Path,
    target_lines: int = 1000,
) -> None:
    header_pattern = re.compile(r"^#(?:[0-9a-fA-F]+)")
    
    with input_path.open("r", encoding="latin-1", newline="") as file:
        lines = file.readlines()

    output_directory.mkdir(parents=True, exist_ok=True)

    parts = []
    current_part = []
    current_line_count = 0

    for line in lines:
        is_header = bool(header_pattern.match(line))

        if (
            current_line_count >= target_lines
            and is_header
            and current_part
        ):
            parts.append(current_part)
            current_part = []
            current_line_count = 0

        current_part.append(line)
        current_line_count += 1

    if current_part:
        parts.append(current_part)

    for index, part in enumerate(parts, start=1):
        output_path = output_directory / (
            f"{input_path.stem}_part_{index:02d}{input_path.suffix}"
        )

        with output_path.open(
            "w",
            encoding="latin-1",
            newline=""
        ) as file:
            file.writelines(part)

        print(
            f"Created: {output_path} "
            f"({len(part)} lines)"
        )


if __name__ == "__main__":
    input_path = DATA_DIR / "TEMPLATE.DAT"

    target_lines = 1000

    if len(sys.argv) >= 3:
        target_lines = int(sys.argv[2])

    output_directory = (
        input_path.parent / f"TEMPLATE_parts"
    )

    split_file(
        input_path=input_path,
        output_directory=output_directory,
        target_lines=target_lines,
    )