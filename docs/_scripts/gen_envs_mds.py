"""
This script reads documentation from /pettingzoo and puts it into md files inside the docs/ directory
"""

from genericpath import isdir
import os
import re


def add_frontmatter(text, frontmatter_options):
    frontmatter_text = "---"
    for key, value in frontmatter_options.items():
        frontmatter_text += f"\n{key}: {value}"
    frontmatter_text += "\n---\n\n"
    return frontmatter_text + text


def create_docs_md(file_path, text, frontmatter_options):
    text = add_frontmatter(text, frontmatter_options)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)


def get_docs_from_py(file_path):
    print(file_path)
    with open(file_path, "r", encoding="utf-8") as fp:
        text = fp.read()
        regex = re.compile(r'"""\s*(\n|.)*?("""\s*\n)')
        match = regex.match(text)
        if match:
            g = match.group(0)
            # remove docstring quotes
            return text[4 : len(g) - 5]
        else:
            return ""


if __name__ == "__main__":
    ignore_dirs = ["test", "utils"]
    envs_dir = os.path.join("..", "..", "pettingzoo")
    for env_type in os.listdir(envs_dir):
        env_type_path = os.path.join(envs_dir, env_type)
        if not os.path.isdir(env_type_path) or env_type in ignore_dirs:
            continue
        envs_list = os.listdir(env_type_path)

        # rlcard_envs don't follow the same folder structure
        if "rlcard_envs" in envs_list:
            envs_list.pop(envs_list.index("rlcard_envs"))
            for i in os.listdir(os.path.join(env_type_path, "rlcard_envs")):
                if (
                    not os.path.isdir(os.path.join(env_type_path, "rlcard_envs", i))
                    and i != "__init__.py"
                    and i != "rlcard_base.py"
                ):
                    envs_list.append(os.path.join("rlcard_envs", i[:-3]))
            envs_list = sorted(envs_list)

        for i, env_name in enumerate(envs_list):
            env_dir_path = os.path.join(env_type_path, env_name)
            if (
                os.path.isdir(env_dir_path) and "utils" not in env_dir_path
            ) or "rlcard_envs" in env_dir_path:
                if "rlcard_envs" in env_dir_path:
                    env_name = env_name.replace("\\", "/").split("/")[1]
                frontmatter_options = {
                    "env_icon": f'"../../../_static/img/icons/{env_type}/{env_name}.png"'
                }
                if i == 0:
                    frontmatter_options["firstpage"] = ""
                elif i == len(os.listdir(env_type_path)) - 1:
                    frontmatter_options["lastpage"] = ""

                docs_text = get_docs_from_py(
                    os.path.join(
                        env_dir_path,
                        env_name + ".py" 
                    ) if "rlcard_envs" not in env_dir_path else env_dir_path + ".py" 
                )
                docs_env_path = os.path.join(
                    "..", "environments", env_type, env_name + ".md"
                )
                create_docs_md(
                    docs_env_path,
                    docs_text,
                    frontmatter_options,
                )
