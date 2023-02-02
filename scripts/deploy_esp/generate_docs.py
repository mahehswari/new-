#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

"""
This script generates viewable html documentation from provided markdown files.

Target audience are end customers deploying Experience Kits in offline mode.

Script was written for Python 3.6+ and uses no external dependencies, except for markdown.

This script can be run standalone or as part of generation of offline package proccess.

Available script options. Generate offline documentation:
 - default script invocation, input path has to be specified, output path is ./tmp:     <script> <input_path>
 - script run with input and output paths specified:            <script> <input_path> --output <output_path>
 - force option if output path folder has to be regenerated:    <script> <input_path> --output <output_path> --force
"""

import argparse
import logging
import os
import pathlib
import sys
import traceback

import re
import shutil
import markdown # pylint: disable=import-error

# pylint: disable=import-error
import seo.error


def parse_args():
    """ Parse script arguments """

    p = argparse.ArgumentParser(
        description="""
            Render all the markdown documentation files found in the INPUT directory to HTML. Additionally, render
            these of the sections that match special header format to separate article files. Each article will be
            rendered twice: in the full file and in its individual article file.
        """)

    p.add_argument(
        action="store", dest="in_path", metavar="INPUT", type=pathlib.Path,
        help="path to the INPUT directory containing markdown documentation to be rendered")
    p.add_argument(
        "-o", "--output", action="store", dest="out_path", metavar="PATH", type=pathlib.Path,
        default="./out",
        help="""
            PATH to the output directory into which the command will render the offline documentation
            (default: %(default)s)
        """)
    p.add_argument(
        "-f", "--force", action="store_true", dest="force",
        help="""
            force the script to ignore errors; use this option with caution, as it may
            overwrite a duplicate article id or previously generated documentation;
            it is safer to resolve each of the issues that the script warns about manually
        """)
    p.add_argument(
        "--debug", action="store_true", dest="debug",
        help="provide more verbose diagnostic information")

    args = p.parse_args()
    args.prog = p.prog
    return args


def check_preconditions(args):
    """ Check script's preconditions """

    logging.debug("1/4 Checking preconditions")

    if not args.in_path.exists():
        raise seo.error.AppException(
            seo.error.Codes.MISSING_PREREQUISITE,
            "The documentation input path doesn't exist:\n"
            f"    {args.in_path}")

    if args.force and args.out_path.exists():
        shutil.rmtree(args.out_path)
        logging.warning("%s directory was deleted and new documentation will be created.", args.out_path)

    if args.out_path.exists():
        raise seo.error.AppException(
            seo.error.Codes.ARGUMENT_ERROR,
            f"The output directory ('{args.out_path}') already exists.\n"
            "    Remove it manually or use the --force option to remove it automatically")


def find_files(cfg, path, filetype):
    """ Find files of certain filetype and return their filepaths and filenames """

    excluded_files = cfg["excluded_files"]

    file_paths = []

    for root, _, files in os.walk(path):
        for file_name in files:
            if file_name.endswith(filetype):
                if file_name in excluded_files:
                    continue

                file_path = root.split(str(path))[1][1:]

                file_paths.append((file_path, file_name))

    return file_paths


def store_md_files(cfg, paths):
    """ Store Markdown files in memory """

    in_path = cfg["in_path"]
    out_path = cfg["out_path"]
    file_objs = cfg["file_objs"]

    logging.debug("3/4 Creating split md files.")

    os.makedirs(os.path.join(out_path, "article"), exist_ok=True)
    os.makedirs(os.path.join(out_path, "full"), exist_ok=True)

    for file_path, file_name in paths:
        os.makedirs(os.path.join(out_path, "full", file_path), exist_ok=True)

        with open(os.path.join(in_path, file_path, file_name), 'r') as file:
            file_content = file.readlines()

        file_objs.append({"file_path": os.path.join(".", out_path, "full", file_path), "file_name": file_name,
                          "main_file_name": "", "file_content": file_content, "is_article": False})


def copy_style_css(cfg):
    """ Copy style.css file to output directory """
    out_path = cfg["out_path"]
    style_path = os.path.join(os.path.dirname(__file__), "style.css")

    try:
        shutil.copy(style_path, out_path)
    except IOError as e:
        raise seo.error.AppException(
            seo.error.Codes.RUNTIME_ERROR,
            "Unable to copy file:\n"
            f"    {e}")


def create_html_from_md(cfg):
    """ Create HTML files from stored Markdown files """

    logging.debug("4/4 Creating html files.")

    out_path = cfg["out_path"]

    # This section goes through 'input' and 'split' directories collecting md files
    # and creating html files in mirrored structure inside of 'html' dir.
    for obj in cfg["file_objs"]:
        file_name = obj["file_name"]
        file_path = obj["file_path"]
        file_content = obj["file_content"]
        main_file_name = obj["main_file_name"]
        is_article = obj["is_article"]

        # Title of html and path to the css file.
        css_file = os.path.join("..", "style.css") if is_article \
                   else os.path.join(os.path.relpath(out_path, file_path), "style.css")

        html5_template = f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\
                        \n<title>{file_name[:-3]}</title>\n<link rel=\"stylesheet\" href=\"{css_file}\">\
                        \n</head>\n<body>\n"

        html_content_from_md = markdown.markdown(''.join(file_content), extensions=['fenced_code', 'toc'])
        if is_article:
            with open(os.path.join(out_path, "article", file_name[:-3] + ".html"), 'w') as f:
                mainpage_file_path = os.path.relpath(os.path.relpath(file_path),
                                                     os.path.relpath(os.path.join("article")))
                mainpage_file_path = os.path.join("..", mainpage_file_path, main_file_name[:-3] + ".html")
                footer = f"\nVisit <a href=\"{mainpage_file_path}\">Main page</a> for more information."
                f.write(html5_template + html_content_from_md + footer + "\n</body>\n</html>")
        else:
            with open(os.path.join(file_path, file_name[:-3] + ".html"), 'w') as f:
                f.write(html5_template + html_content_from_md + "\n</body>\n</html>")


def get_single_md_file_sections(file_obj):
    """ Get all sections of a single stored Markdown file """

    lines = []
    sections = []
    tag = ""

    tags = []

    for line in file_obj["file_content"]:
        if re.match(r"^(?=#{1,6})(.*)(?= +<a)", line):
            if tag:
                sections.append((tag[:], lines[:]))
                lines.clear()

            # This regex expression finds text contained in id html tag
            # and checks if it can represent a valid filename
            result = re.search(r'(?<=((id=("|\'){1})))([\w\-.]+)(?=(\3{1}( |\>){1}))', line)
            if not result:
                logging.warning(
                    "Skipping invalid article id found in the following line of the %s file:\n" \
                    "    %s\n" \
                    "    Article HTML file will not be created.", file_obj["file_name"], line.rstrip())
                continue

            tag = result.group(0)
            tags.append(tag)

            line = re.sub(r"(?= <a)(.*)(?=$)", "", line)

        if tag:
            lines.append(line)

    # add last section when all lines read
    if lines:
        sections.append((tag[:], lines[:]))
        lines.clear()

    return sections, tags


def store_single_md_file_sections(cfg, sections, file_obj):
    """ Store all sections of a single Markdown file in memory """

    file_objs = cfg["file_objs"]
    file_name = file_obj["file_name"]
    file_path = file_obj["file_path"]
    tags = []

    for tag, lines in sections:
        tags.append(tag)
        if len(tags) != len(set(tags)):
            if cfg['is_force']:
                tags = list(set(tags))
        else:
            split_file_name = os.path.join(tag + ".md")
            split_file_content = lines

            file_objs.append({"file_path": file_path, "file_name": split_file_name,
                              "main_file_name": file_name, "file_content": split_file_content, "is_article": True})


def filter_single_md_file_sections(sections):
    """ Filter out unnecessary parts of md sections """

    for sec_idx, (tag, lines) in enumerate(sections):
        main_heading_level = len(re.match(r"^#{1,6}", lines[0]).group(0))

        for lines_idx, line in enumerate(lines[1:]):
            m_obj = re.match(r"^#{1,6}", line)
            if m_obj is not None:
                current_heading_level = len(m_obj.group(0))

                if main_heading_level >= current_heading_level:
                    lines = lines[:lines_idx]
                    sections[sec_idx] = (tag, lines)
                    break

    return sections


def split_md_files(cfg):
    """ Split Markdown files into separate sections """

    unique_tags = {}

    for file_obj in cfg["file_objs"]:
        file_name = file_obj["file_name"]

        sections, tags = get_single_md_file_sections(file_obj)
        for article_id in tags:
            if article_id in unique_tags:
                unique_tags[article_id].append(file_name)
            else:
                unique_tags[article_id] = [file_name]

        sections = filter_single_md_file_sections(sections)
        store_single_md_file_sections(cfg, sections, file_obj)
    check_duplicates_between_files(unique_tags, cfg)


def check_duplicates_between_files(unique_tags, cfg):
    """ Check if there are any duplicate article id between files """

    exception_flag = False
    msg = "Duplicated article identifiers were found:"
    # unique_tags key: article_id value: list of files name where the article id occured
    for article_id, files_name in unique_tags.items():
        # counter key: file_name, value: number of article_id occurrence
        # example: "seo_prov_2" article id occured 2 times in provisioning_troubleshooting.md
        # console output: provisioning_troubleshooting.md (2)
        counter = {}
        # files_name is a list of files with specific article id
        for single_file in files_name:
            if single_file in counter:
                counter[single_file] += 1
            else:
                counter[single_file] = 1
        if len(files_name) > 1:
            exception_flag = True
            msg += (
                f"\n    {len(files_name)} articles using the same {article_id}"
                " identifier were found in the following markdown files:")
            for k, v in counter.items():
                msg += f"\n        {k} ({v})"

    if cfg['is_force'] and exception_flag:
        logging.warning(msg)
    elif exception_flag:
        raise seo.error.AppException(
            seo.error.Codes.RUNTIME_ERROR,
            f"{msg}\n\n    Use the -f/--force option to always use the first conflicting "
            "article occurrence and ignore all the others.")


def config_logger(args):
    """ Configure the logging package """

    if args.debug:
        log_level = logging.DEBUG
        log_format = f"%(asctime)s.%(msecs)03d {args.prog}: [%(levelname)s] %(message)s (%(module)s@%(lineno)d)"
    else:
        log_level = logging.INFO
        log_format = f"{args.prog}: [%(levelname)s] %(message)s"

    logging.basicConfig(level=log_level, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')


def run_main():
    """ Top level script entry function """

    args = parse_args()
    config_logger(args)

    try:
        sys.exit(main(args).value)
    except seo.error.AppException as e:  # pylint: disable=invalid-name
        if args.debug:
            traceback.print_exc(file=sys.stderr)
        logging.error(e.code if e.msg is None else e.msg)
        sys.exit(e.code.value)


def main(args):
    """ Internal main function """

    check_preconditions(args)

    ex_files = ["PULL_REQUEST_TEMPLATE.md"]
    cfg = {"in_path": args.in_path, "out_path": args.out_path, "file_objs": [], "excluded_files": ex_files,
           "is_force": args.force}

    logging.debug("2/4 Looking for Markdown files located in the input path: %s", args.in_path)
    md_files = find_files(cfg, cfg["in_path"], ".md")

    store_md_files(cfg, md_files)
    copy_style_css(cfg)
    split_md_files(cfg)
    create_html_from_md(cfg)

    logging.debug("HTML files are located in %s.", os.path.join(cfg["out_path"], "html"))

    return seo.error.Codes.NO_ERROR


if __name__ == "__main__":
    run_main()
