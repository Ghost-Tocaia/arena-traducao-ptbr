import ast
import re
import textwrap
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "Minha tradução"
PARTS_DIRECTORY = DATA_DIR / "TEMPLATE_parts"

LINE_WIDTH = 30
INPUT_ENCODING = "latin-1"
TRANSLATION_ENCODING = "utf-8"
OUTPUT_ENCODING = "latin-1"


def load_translations(file_path: Path) -> dict[int, str]:
    content = file_path.read_text(encoding=TRANSLATION_ENCODING)

    tree = ast.parse(content)

    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "translations"
        ):
            return ast.literal_eval(node.value)

    raise ValueError(
        f"The 'translations' dictionary was not found in {file_path}."
    )


def normalize_text(text: str) -> str:
    text = text.strip()

    if text.endswith("&"):
        text = text[:-1]

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def wrap_text(text: str, width: int) -> list[str]:
    text = normalize_text(text)

    lines = textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=True,
        drop_whitespace=True,
    )

    if not lines:
        return ["&"]

    lines[-1] += "&"

    return lines


def rebuild_file(
    original_path: Path,
    translations: dict[int, str],
    output_path: Path,
) -> tuple[int, int]:
    original_lines = original_path.read_text(
        encoding=INPUT_ENCODING
    ).splitlines()

    output_lines: list[str] = []

    translation_index = 0
    missing_count = 0
    position = 0

    while position < len(original_lines):
        line = original_lines[position]

        if line.startswith("#") or line.startswith(";") or not line.strip():
            output_lines.append(line)
            position += 1
            continue

        original_text_lines: list[str] = []

        while position < len(original_lines):
            current_line = original_lines[position]

            if (
                current_line.startswith("#")
                or current_line.startswith(";")
                or not current_line.strip()
            ):
                break

            original_text_lines.append(current_line)
            position += 1

        if translation_index not in translations:
            output_lines.extend(original_text_lines)
            missing_count += 1
            translation_index += 1
            continue

        translated_text = translations[translation_index]

        output_lines.extend(
            wrap_text(
                translated_text,
                LINE_WIDTH,
            )
        )

        translation_index += 1

    output_path.write_text(
        "\r\n".join(output_lines) + "\r\n",
        encoding=OUTPUT_ENCODING,
    )

    return translation_index, missing_count


def main() -> None:
    translation_files = sorted(PARTS_DIRECTORY.glob("TEMPLATE_part_*.py"))

    if not translation_files:
        print("No translation files were found.")
        return

    for translation_file in translation_files:
        output_file = translation_file.with_suffix(".DAT")

        if not output_file.exists():
            print(
                f"Skipping {translation_file.name}: "
                f"original {output_file.name} was not found."
            )
            continue

        print(f"Processing {translation_file.name}...")

        translations = load_translations(translation_file)

        translation_count, missing_count = rebuild_file(
            original_path=output_file,
            translations=translations,
            output_path=output_file,
        )

        if missing_count:
            print(
                f"Completed {output_file.name} WITH WARNINGS: "
                f"{translation_count - missing_count}/{translation_count} "
                f"translations applied, {missing_count} left in the original language."
            )
        else:
            print(
                f"Completed {output_file.name}: "
                f"{translation_count} translations applied."
            )


if __name__ == "__main__":
    main()
