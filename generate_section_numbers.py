#!/usr/bin/env python3
import os
import typing
import subprocess
import bisect
import shutil
import re

markdown_in_path = os.path.dirname(__file__) + "/Jarulfs_Guide.md"
markdown_out_path = os.path.dirname(__file__) + "/Jarulfs_Guide_sections.md"
html_out_path = os.path.dirname(__file__) + "/public/index.html"
css_path = os.path.dirname(__file__) + "/style.css"
include_html = [os.path.dirname(__file__) + "/fork_on_gitlab.html"]


def get_section_level(line):
    new_section_size = 0
    for c in line:
        if c is not '#':
            break
        new_section_size += 1

    return new_section_size


def recursive_parse_sections(current_section_path,
                             f,
                             levels_dict,
                             section_names_set: typing.Set[str],
                             before_table_of_contents=True):

    def insert(insert_line, path):
        section_name = insert_line.lstrip("#").strip()

        if section_name in section_names_set:
            raise Exception("Error, duplicate section name: '{}', this makes links break, so we don't allow it".format(
                section_name
            ))

        levels_dict[insert_line] = path
        section_names_set.add(section_name)

    while True:
        line = f.readline()

        if not line:
            break

        if line == "# Table of contents\n":
            before_table_of_contents = False
            continue

        if before_table_of_contents:
            continue

        line = line.strip()

        if line.startswith("#"):
            line = line[1:]

            new_section_size = get_section_level(line)

            if new_section_size > len(current_section_path):
                current_section_path.append(1)
                insert(line, tuple(current_section_path))

                back_up_line = recursive_parse_sections(current_section_path, f, levels_dict, section_names_set, False)
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
    return "{} {} [{}](#{})\n".format(
        ("#" * (len(path)+1)),
        ".".join([str(i) for i in path]),
        line.lstrip("#"),
        generate_sublink_string(line))


def generate_sublink_string(line: str):
    line = line.lstrip("#").strip()
    section_name = line.lower().replace(" ", "-")
    section_name = "".join([c for c in section_name if c.isalpha() or c == "-"])

    return section_name


def get_sublink_string_path_dictionary(levels_dict: typing.Dict[str, tuple]):
    retval = {}
    for key in levels_dict:
        retval[generate_sublink_string(key)] = levels_dict[key]

    return retval


def generate_toc_line(line: str, path):
    line = line.lstrip("#").strip()
    section_name = generate_sublink_string(line)

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
    sublink_string_dict = get_sublink_string_path_dictionary(levels_dict)

    with open(path, "w", encoding="utf-8") as out_file:
        before_table_of_contents = True

        pattern = r"CHAPTER_LINK_([a-z\-]+)"

        while True:
            line = in_file.readline()

            captures = re.findall(pattern, line)

            if captures:
                for section_str in captures:
                    if section_str not in sublink_string_dict:
                        raise Exception("section '{}' is linked to, but does not exist".format(section_str))

                    section_tuple = sublink_string_dict[section_str]

                    line = line.replace("CHAPTER_LINK_" + section_str,
                                        "[chapter {}](#{})".format(".".join([str(i) for i in section_tuple]),
                                                                   section_str))

            if not line:
                break

            if line == "# Table of contents\n":
                out_file.write("<div class='navigation'>\n");
                out_file.write(line)
                generate_table_of_contents(out_file, levels_dict)
                out_file.write("</div>\n");
                before_table_of_contents = False
                continue

            if not before_table_of_contents and line.startswith("#"):
                line = line[1:]
                line = generate_replacement_line(line.strip(), levels_dict[line.strip()])

            out_file.write(line)


# This function was used once, to convert the original chapter links in Jarulf's guide (in the form
# "see chapter 1.3") to named links, like CHAPTER_LINK_general-remarks. It shouldn't be needed anymore,
# but I left it in here for completeness.
def rewrite_replace_original_chapter_links(path: str, in_file: typing.IO, levels_dict: typing.Dict[str, tuple]):
    reversed_levels_dict = {}
    for key in levels_dict:
        reversed_levels_dict[levels_dict[key]] = key

    pattern = r"chapter ([0-9.]+)"

    with open(path, "w", encoding="utf-8") as out_file:
        while True:
            line = in_file.readline()

            write_line = line

            if not write_line:
                break

            captures = re.findall(pattern, write_line)

            if captures:
                write_line = re.sub(pattern,
                                    r"CHAPTER_LINK_\1",
                                    write_line)

                for section_str in captures:
                    section_str = section_str.rstrip(".")
                    section_tuple = tuple([int(x) for x in section_str.split(".")])
                    section_name = generate_sublink_string(reversed_levels_dict[section_tuple])

                    write_line = write_line.replace("CHAPTER_LINK_" + section_str, "CHAPTER_LINK_" + section_name)

            out_file.write(write_line)


def generate_html():
    os.makedirs(os.path.dirname(html_out_path), exist_ok=True)

    command = ["pandoc",
               markdown_out_path,
               "-o", html_out_path,
               "--css", "style.css"]

    for path in include_html:
        command.append("--include-in-header")
        command.append(path)

    subprocess.check_call(command)
    shutil.copyfile(css_path, os.path.dirname(html_out_path) + "/style.css")


def __main__():

    levels_dict = {}
    section_names_set = set()
    with open(markdown_in_path, "r", encoding="utf-8") as in_file:
        recursive_parse_sections([], in_file, levels_dict, section_names_set)

        in_file.seek(0)

        # rewrite_replace_original_chapter_links("fixed.md", in_file, levels_dict)
        rewrite_with_sections(markdown_out_path, in_file, levels_dict)

    generate_html()
    os.remove(markdown_out_path)


if __name__ == "__main__":
    __main__()
