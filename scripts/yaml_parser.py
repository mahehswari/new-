# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
"""
This script automatizes generating list of components used in Smart Edge Experience Kits
"""

import argparse
import csv
import io
import os
from pathlib import Path
import sys


class Comments:
    """ Storing parsed comments """
    def __init__(self) -> None:
        self.allowed_fields = [
            "name",
            "role",
            "domain",
            "type",
            "source",
            "ip status",
            "description",
            "status"
        ]
        self.allowed_directories = ["playbooks"]
        #additional files to be loaded from EK directory when restricted_files is set to true
        self.additional_files = [
            "single_node_network_edge.yml",
            "network_edge.yml",
             "default_config.yml"]
        self.list_of_comments = []
        self.ek_directory = Path()
        self.__ek_settings = {}
        self.__role_status_dict = {}

    def combine(self, files=None, input_dir=None, output=None):
        """ Combine fields from comments  """
        self.list_of_comments = []
        files = self.__get_csv_files(files, input_dir)

        for file in files:
            self.__read_csv(file)

        seen = set()
        out = {}
        for comment in self.list_of_comments:
            id_tuple = (comment["role"], comment["name"])
            if (id_tuple) not in seen:
                out[id_tuple] = comment
                seen.add(id_tuple)
            elif comment['ek'] not in out[id_tuple]["ek"]:
                out[id_tuple]["ek"] = out[id_tuple]["ek"] + f", {comment['ek']}"
        self.list_of_comments = out.values()
        fieldnames = self.allowed_fields + ["ek"]
        fieldnames.remove("status")
        if output is None:
            filename="combined_test.csv"
        else:
            filename = output
        self.save_to_file(
            filename= filename,
            fieldnames=fieldnames
            )

    def parse_ek(self, files=None, input_dir=None, restricted_files = False):
        """ Loader for yaml files """
        if input_dir:
            self.ek_directory = Path(input_dir).resolve()
        else:
            cwd = Path(os.getcwd())
            self.ek_directory = cwd
        self.__load_default_settings()
        yaml_files = self.__get_yaml_files(restricted_files)
        if files:
            yaml_files.extend(files)
        for filename in yaml_files:
            self.__load_yml_file(Path(filename))
        self.list_of_comments = [dict(t) for t in {tuple(d.items()) for d in self.list_of_comments}]

    def parse_virgo(self,input_dir=None,):
        """ Loader for yaml files (virgo repository specific)"""
        if input_dir:
            self.ek_directory = Path(input_dir).resolve()
        else:
            cwd = Path(os.getcwd())
            self.ek_directory = cwd
        controller_main_dir = Path(
            "controller/helm/smart-edge-commercial/templates/deployments").resolve()
        yaml_files = self.__get_yaml_files(restricted_files=False, input_dir=controller_main_dir)

        for filename in yaml_files:
            self.__load_yml_file(Path(filename))

    def to_csv(self, fieldnames=None):
        """ Generate csv """
        if not fieldnames:
            fieldnames = self.allowed_fields

        output = io.StringIO()
        dict_writer = csv.DictWriter(
            f=output,
            fieldnames=fieldnames,
            restval="-",
            delimiter=","
        )
        dict_writer.writeheader()
        filename = None
        total_number_of_rows = 0
        for comment in self.list_of_comments:
            for field_to_delete in list(set(comment.keys()) - set(fieldnames)):
                comment.pop(field_to_delete)
            if comment["type"] == "Recipe":
                filename = f"{comment['name'].replace(' ','-') }_parsed.csv"
            else:
                if comment["role"] in self.__role_status_dict:
                    if self.__role_status_dict[comment["role"]] is True:
                        comment["status"] = "Enabled"
                    elif self.__role_status_dict:
                        comment["status"] = "Disabled"
                dict_writer.writerow(comment)
                total_number_of_rows += 1
        print(f"Total numbers of rows: {total_number_of_rows}")
        return output.getvalue(), filename

    def save_to_file(self, filename="parsed_yaml_playbooks.csv", fieldnames=None):
        """ Save ouptut file """
        data, name = self.to_csv(fieldnames=fieldnames)
        if not name:
            name = filename
        with open(name, "w", newline='', encoding='UTF-8') as file:
            file.write(data)

    def __create_base_comment_dict(self, filename, prev_line):
        tmp_dict = dict.fromkeys(self.allowed_fields)
        prev_line = prev_line.split(":")
        if filename.name == "default_config.yml":
            tmp_dict["role"] = prev_line[0]
        elif len(prev_line) > 1:
            tmp_dict["role"] = ":".join(prev_line[1:]).strip()

        return tmp_dict

    @staticmethod
    def __get_csv_files(files, input_dir):
        if files is None:
            files = []
        files = [Path(f).resolve() for f in files]

        if input_dir and os.path.isdir(input_dir):
            directory = Path(input_dir).resolve()
        else:
            directory = Path(os.getcwd())
        if not files:
            files = [directory.joinpath(f) for f in os.listdir(directory)
                    if (os.path.isfile(directory.joinpath(f)) and ".csv" in f)]
        elif files and input_dir:
            files.extend(
                [directory.joinpath(f) for f in os.listdir(directory)
                if (os.path.isfile(directory.joinpath(f)) and ".csv" in f)])

        return files

    def __get_deployment_name(self):
        inventory_path = self.ek_directory.joinpath("inventory.yml")
        with open(inventory_path, encoding='UTF-8') as file:
            for line in file:
                line = line.split("#")[0]
                if "deployment:" in line and not "single_node_deployment:" in line:
                    out = line.strip().split(":")[1].strip()
                    break
            else:
                print("[ERROR] deployment name not found, exiting")
                sys.exit(1)
        return out

    def __get_yaml_files(self, restricted_files, input_dir: Path=None) -> list:
        yaml_files = []
        if input_dir is None:
            allowed_directories_paths = [
                self.ek_directory.joinpath(d) for d in self.allowed_directories
            ]
            base_directory = self.ek_directory
        else:
            base_directory = input_dir
            restricted_files = False
            allowed_directories_paths = []
        extensions = (".yml", ".yaml")

        for dname, _, filenames in os.walk(base_directory):
            dname = Path(dname)
            if dname in allowed_directories_paths:
                for fname in filenames:
                    if fname.lower().endswith(extensions):
                        yaml_files.append(dname.joinpath(fname))
            elif dname == base_directory:
                for name in filenames:
                    if restricted_files and name in self.additional_files:
                        yaml_files.append(dname.joinpath(name))
                    elif restricted_files is False and name.endswith(extensions):
                        yaml_files.append(dname.joinpath(name))
        return yaml_files

    @staticmethod
    def __get_csv_file_content(filename):
        out = []
        if os.path.isfile(filename):
            with open(filename, encoding='UTF-8') as file:
                csv_reader = csv.reader(file, delimiter=",")
                for row in csv_reader:
                    out.append(row)
        else:
            print(f"file: {filename} cannot be found")
        return out

    def __load_default_settings(self):
        deployment_name = self.__get_deployment_name()
        self.__role_status_dict = {}
        self.__ek_settings = {}
        paths = [
            self.ek_directory.joinpath("inventory/default"),
            self.ek_directory.joinpath("deployments",deployment_name)]
        settings_files = []
        for path in paths:
            files = []
            settings_dir_path = path
            for dname, _, filenames in os.walk(settings_dir_path):
                for filename in filenames:
                    files.append(settings_dir_path.joinpath(dname,filename))
            settings_files.extend(files)
        settings_files.sort(key = lambda x: x.name)

        for settings_file in settings_files:
            with open(settings_file, encoding='UTF-8') as file:
                for line in file:
                    line = line.strip().lower()
                    if ("true" in line or "false" in line) and not line.startswith("#"):
                        line = line.split(":")
                        self.__ek_settings[line[0].lower()] = "".join(line[1:]).strip() in ["true"]

    def __load_yml_file(self, filename):
        filename = Path(filename).resolve()
        if not os.path.isfile(filename):
            print(f"File: {filename} cannot be found, skiping")
            return

        prev_line = None
        tmp_dict = {}
        prev_role = None

        with open(filename, encoding='UTF-8') as file:
            for line in file:
                line = line.strip()
                if line.startswith("when:") and tmp_dict:
                    self.__set_role_status(tmp_dict, line)
                elif line.startswith("#") and not line.startswith("##"):
                    split_comment = line.strip("#").strip().split(":")
                    if (
                        len(split_comment) > 1
                        and split_comment[0].lower() in self.allowed_fields
                    ):
                        if not tmp_dict:
                            tmp_dict = self.__create_base_comment_dict(filename, prev_line)
                        tmp_dict[split_comment[0].lower()] = ":".join(split_comment[1:]).strip()
                        if tmp_dict["role"]:
                            prev_role = tmp_dict["role"]
                            self.__role_status_dict[prev_role] = True
                elif tmp_dict and tmp_dict not in self.list_of_comments:
                    if tmp_dict["role"] is None:
                        tmp_dict["role"] = prev_role
                    self.list_of_comments.append(tmp_dict)
                    tmp_dict = {}

                prev_line = line

            if tmp_dict and tmp_dict not in self.list_of_comments:
                if tmp_dict["role"] is None:
                    tmp_dict["role"] = prev_role
                if prev_line.startswith("when:"):
                    self.__set_role_status(tmp_dict, prev_line)

                self.list_of_comments.append(tmp_dict)

    def __read_csv(self, filename):
        data = self.__get_csv_file_content(filename)
        if data and len(data) > 1:
            for row in data[1:]:
                row_dict = dict(zip(self.allowed_fields, row))
                row_dict["ek"] = filename.name.split("/")[-1].split(
                    "_")[0].replace("-", " ").strip(".csv")
                if row_dict["status"].lower() == "enabled":
                    self.list_of_comments.append(row_dict)

    def __set_role_status(self, tmp_dict, line):
        line = line.replace("'","").replace('"',"").replace(" ","")
        conditional = "".join(line.split(":")[1:]).strip().lower().split("|")
        if conditional[0] in self.__ek_settings:
            self.__role_status_dict[tmp_dict["role"]] = self.__ek_settings[conditional[0]]
        else:
            self.__role_status_dict[tmp_dict["role"]] = "true" in conditional[1]

if __name__ == "__main__":
    c = Comments()
    MSG = "Smart Edge Open deployment playbooks yaml parser"
    OUTPUT_HELP_MSG = "set output filename"
    COMBINE_HELP_MSG = "combine csv files"
    INPUT_HELP_MSG = """set input directory
    |    Example: -in /experience/kit/directory"""
    FILES_HELP_MSG = """pass csv files, or directories
    |   Example: -f /experience/kits/file1.csv /experience/kits/file2.csv"""
    RESTRICT_HELP_MSG = f"""restricts parser to only specified files in root directory:
    {c.additional_files} except for allowed directories: {c.allowed_directories}"""

    parser = argparse.ArgumentParser(
        description=MSG,
        formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=60))

    parser.add_argument("-o",  "--Output",  help=OUTPUT_HELP_MSG)
    parser.add_argument("-c",  "--Combine", help=COMBINE_HELP_MSG, action="store_true")
    parser.add_argument("-in", "--Input",   help=INPUT_HELP_MSG)
    parser.add_argument("-f",  "--Files",   help=FILES_HELP_MSG, nargs="+")
    parser.add_argument("-r",  "--Restrict",help=RESTRICT_HELP_MSG, action="store_true")
    #parser.add_argument("-v",  "--Virgo", action="store_true")
    parser.parse_args()

    args = parser.parse_args()

    if args.Combine:
        c.combine(files=args.Files, input_dir=args.Input, output=args.Output)
        sys.exit(0)

    # if args.Virgo:
    #     if args.Output:
    #         OUTPUT_FILENAME_PREFIX = args.Output
    #     else:
    #         OUTPUT_FILENAME_PREFIX = "virgo"

    #     c.parse_virgo()
    #     c.save_to_file(filename=f"{OUTPUT_FILENAME_PREFIX}_controller.csv")
    #     c = Comments()
    #     c.parse_ek(input_dir="experience-kit")
    #     c.save_to_file(filename=f"{OUTPUT_FILENAME_PREFIX}_experience_kit.csv")

    # else:
    c = Comments()
    c.parse_ek(files=args.Files, input_dir=args.Input, restricted_files=args.Restrict)
    if args.Output:
        c.save_to_file(filename=args.Output)
    else:
        c.save_to_file()

    sys.exit(0)
