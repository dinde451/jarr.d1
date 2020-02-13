#!/usr/bin/env python3
import os
import typing
import subprocess
import bisect
import shutil

markdown_in_path = os.path.dirname(__file__) + "/Jarulfs_Guide.md"
markdown_out_path = os.path.dirname(__file__) + "/Jarulfs_Guide_sections.md"
html_out_path = os.path.dirname(__file__) + "/public/index.html"
css_path = os.path.dirname(__file__) + "/style.css"


def get_section_level(line):
    new_section_size = 0
    for c in line:
        if c is not '#':
            break
        new_section_size += 1

    return new_section_size


def recursive_parse_sections(current_section_path, f, levels_dict, before_table_of_contents=True):

    def insert(insert_line, path):
        if insert_line in levels_dict:
            raise Exception("Error, duplicate section name: '{}', this makes links break, so we don't allow it".format(
                insert_line.lstrip("#").strip()
            ))

        levels_dict[insert_line] = path

    while True:
        line = f.readline()

        if not line:
            break

        if line == "TABLE_OF_CONTENTS_HERE\n":
            before_table_of_contents = False

        if before_table_of_contents:
            continue

        line = line.strip()

        if line.startswith("#"):
            line = line[1:]

            new_section_size = get_section_level(line)

            if new_section_size > len(current_section_path):
                current_section_path.append(1)
                insert(line, tuple(current_section_path))

                back_up_line = recursive_parse_sections(current_section_path, f, levels_dict, False)
                del current_section_path[-1]

                if back_up_line:
                    if get_section_level(back_up_line) < len(current_section_path):
                        return back_up_line
                    else:
                        current_section_path[-1] += 1
                        insert(back_up_line, tuple(current_section_path))

            elif new_section_size < len(current_section_path):
                return line
            else:
                current_section_path[-1] += 1
                insert(line, tuple(current_section_path))

    return None


def generate_replacement_line(line: str, path):
    return ("#" * (len(path)+1)) + " " + ".".join([str(i) for i in path]) + " " + line.lstrip("#") + "\n"


def generate_toc_line(line: str, path):
    line = line.lstrip("#").strip()
    section_name = line.lower().replace(" ", "-")
    section_name = "".join([c for c in section_name if c.isalpha() or c == "-"])

    return '<h{}>{} <a href="#{}">{}</a></h2>'.format(
        len(path) + 1,
        ".".join([str(i) for i in path]),
        section_name,
        line
    )


def generate_table_of_contents(out_file: typing.IO, levels_dict: typing.Dict[str, tuple]):
    sorted_sections_list = []
    for item in levels_dict.items():
        bisect.insort(sorted_sections_list, (item[1], item[0]))

    for item in sorted_sections_list:
        out_file.write(generate_toc_line(item[1], item[0]))


def rewrite_with_sections(path: str, in_file: typing.IO, levels_dict: typing.Dict[str, tuple]):
    with open(path, "w", encoding="utf-8") as out_file:
        before_table_of_contents = True

        while True:
            line = in_file.readline()

            if not line:
                break

            if line == "TABLE_OF_CONTENTS_HERE\n":
                generate_table_of_contents(out_file, levels_dict)
                before_table_of_contents = False
                continue

            if not before_table_of_contents and line.startswith("#"):
                line = line[1:]
                line = generate_replacement_line(line.strip(), levels_dict[line.strip()])

            out_file.write(line)


def generate_html():
    os.makedirs(os.path.dirname(html_out_path), exist_ok=True)
    subprocess.check_call(["pandoc",
                           markdown_out_path,
                           "-o", html_out_path,
                           "--css", "style.css"])
    shutil.copyfile(css_path, os.path.dirname(html_out_path) + "/style.css")


def __main__():

    levels_dict = {}
    with open(markdown_in_path, "r", encoding="utf-8") as in_file:
        recursive_parse_sections([], in_file, levels_dict)

        in_file.seek(0)
        rewrite_with_sections(markdown_out_path, in_file, levels_dict)

    generate_html()
    os.remove(markdown_out_path)


if __name__ == "__main__":
    __main__()
