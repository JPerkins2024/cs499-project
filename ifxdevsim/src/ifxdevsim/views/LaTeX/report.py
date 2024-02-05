# report.py - Lam Ha

import os
import subprocess
import yaml

##########################################################################################################


class layout:
    """Generate default layout for latex pdf with all pdf files in cwd"""

    def __init__(self, name, cwd=os.getcwd()):
        self.cwd = cwd
        self.layout = "\n"
        self.name = name
        self.load_default_layout()
        self.generate_layout(
            self.file_search(self.cwd), self.cwd, self.sectioning_depth
        )
        self.write_to_file()

    def load_default_layout(self):
        with open(
            os.path.join(os.path.dirname(__file__), "default_report_view_layout.yaml"),
            "r",
        ) as f:
            self.default_layout = f.readlines()
            for line in self.default_layout:
                if "- Col" in line:
                    self.col = int(line.split(":")[1].split("#")[0])
                if "- Depth" in line:
                    self.sectioning_depth = int(line.split(":")[1].split("#")[0])
            if not hasattr(self, "col"):
                raise KeyError("Missing 'Col' key in default layout file #Styling")
            if not hasattr(self, "sectioning_depth"):
                raise KeyError("Missing 'Depth' key in default layout file #Styling")

    def file_search(self, path):
        for root, dirs, files in os.walk(path):
            filetree = {
                file: root
                for file in files
                if file.endswith(".pdf") and not file.endswith(".report.pdf")
            }
            filetree.update(
                {
                    dir: self.file_search(os.path.join(root, dir))
                    for dir in dirs
                    if self.file_search(os.path.join(root, dir)) != {}
                }
            )
            return filetree

    def generate_layout(self, filetree, cwd, depth):
        """Generate and write new default layout with pdf files in cwd"""

        self.layout += "- Section" + str(depth) + ": Files in " + cwd + "\n"
        self.layout += (
            """- Plot:
    Col: """
            + str(self.col)
            + """
    Caption: """
            + cwd
            + """ 
    Order: """
            + "\n"
        )
        for file in filetree:
            if isinstance(filetree[file], dict):
                self.generate_layout(filetree[file], os.path.join(cwd, file), depth + 1)
            else:
                self.layout += (
                    "      "
                    + os.path.join(filetree[file], file)
                    + ": "
                    + file[:-4]
                    + "\n"
                )

    def write_to_file(self):
        os.makedirs(self.name[:-5], exist_ok=True)
        with open(self.name[:-5] + "/" + self.name.split("/")[-1], "w") as new:
            for line in self.default_layout:
                new.write(line)
                if "# Body" in line:
                    new.write(self.layout)


class report:
    """Generate LaTex and pdf file through pdfLaTex using input layout(.yaml) files"""

    def __init__(self, layout_file):
        self.load_layout(layout_file)
        self.content = ""
        self.generate_content()
        self.generate_pdf(layout_file)

    def load_layout(self, layout_file):
        with open(layout_file, "r") as f:
            self.layout = yaml.safe_load(f)

    def generate_content(self):
        for block in self.layout:
            for key in block:
                if key == "Font":
                    self.content += (
                        r"""\documentclass[%(Font)s,]{article}
\usepackage{"""
                        % block
                        + os.path.join(os.path.dirname(__file__), "tex_preamble")
                        + r"""}
\begin{document}
"""
                    )
                elif key == "Title":
                    if "Name" in block[key]:
                        self.content += r"\title{%(Name)s}" % block[key] + "\n"
                    else:
                        self.content += r"\title{}" + "\n"
                    if "Author" in block[key]:
                        self.content += r"\author{%(Author)s}" % block[key] + "\n"
                    if "Date" in block[key]:
                        self.content += r"\date{%(Date)s}" % block[key] + "\n"
                    self.content += r"\maketitle" + "\n"

                elif key == "Table of Content":
                    self.content += r"\tableofcontents" + "\n"

                elif key == "List of Figures":
                    self.content += r"\listoffigures" + "\n"

                elif key == "Text":
                    for section in block[key]:
                        if section == "Bold":
                            self.content += r"\textbf{%(Bold)s}" % block[key]
                        elif section == "Italics":
                            self.content += r"\textit{%(Italics)s}" % block[key]
                        elif section == "Underline":
                            self.content += r"\{underline%(Underline)s}" % block[key]
                        elif section == "Autofill":
                            self.content += r"\lipsum[%(Autofill)s]" % block[key] + "\n"
                        elif section == "Normal":
                            self.content += block[key][section]

                elif key == "Vspace":
                    self.content += r"\vspace{%(Vspace)s}" % block + "\n"
                elif key == "Hspace":
                    self.content += r"\hspace{%(Hspace)s}" % block + "\n"
                elif key == "Newpage":
                    self.content += r"\newpage" + "\n"

                elif key == "Section0":
                    self.content += r"\part{" + block[key] + "}" + "\n"
                elif key == "Section1":
                    self.content += r"\section{" + block[key] + "}" + "\n"
                elif key == "Section2":
                    self.content += r"\subsection{" + block[key] + "}" + "\n"
                elif key == "Section3":
                    self.content += r"\subsubsection{" + block[key] + "}" + "\n"
                elif key == "Section4":
                    self.content += r"\paragraph{" + block[key] + "}" + "\n"
                elif key == "Section5":
                    self.content += r"\subparagraph{" + block[key] + "}" + "\n"
                # elif key == 'UnnumberedSection':
                #     self.content += r'\section*{%(UnnumberedSection)s}'%block + '\n'

                elif key == "Graphics":
                    if "File" in block[key]:
                        for root, dirs, files in os.walk(os.getcwd()):
                            for file in files:
                                if file == block[key]["File"]:
                                    self.content += r"\begin{figure}[H]" + "\n"
                                    if "Align" in block[key]:
                                        if block[key]["Align"] == "Center":
                                            self.content += r"  \centering" + "\n"
                                        if block[key]["Align"] == "Right":
                                            self.content += r"  \raggedleft" + "\n"
                                        if block[key]["Align"] == "Left":
                                            self.content += r"  \raggedright" + "\n"
                                    if "Offset" in block[key]:
                                        self.content += (
                                            r"  \hspace{%(Offset)s}" % block[key] + "\n"
                                        )
                                    if "Scale" in block[key] and isinstance(
                                        block[key]["Scale"], (float, int)
                                    ):
                                        self.content += (
                                            r"  \includegraphics[scale="
                                            + str(block[key]["Scale"])
                                            + r"]{"
                                            + os.path.join(root, file)
                                            + "}"
                                            + "\n"
                                        )
                                    else:
                                        self.content += (
                                            r"  \includegraphics{"
                                            + os.path.join(root, file)
                                            + "}"
                                            + "\n"
                                        )
                                    if "Caption" in block[key]:
                                        self.content += (
                                            r"  \caption{"
                                            + block[key]["Caption"]
                                            + "}"
                                            + "\n"
                                        )
                                    self.content += r"\end{figure}" + "\n"
                                    break
                            else:
                                continue
                            break
                        else:
                            print(os.path.join(root, file))
                            raise SyntaxError(
                                "Path in Graphics 'File' cannot be found in cwd"
                            )
                    else:
                        raise KeyError(
                            "Missing 'File' key when writing Graphics to LaTex"
                        )

                elif key == "Plot":
                    if "Col" in block[key]:
                        if isinstance(block[key]["Col"], (float, int)):
                            for i in range(
                                0, len(block[key]["Order"]), block[key]["Col"]
                            ):
                                if i == 0:
                                    self.content += r"""\begin{figure}[H]
    \centering
"""
                                else:
                                    self.content += r"""\begin{figure}[H]
    \ContinuedFloat
    \centering
"""
                                for plot in dict(
                                    list(block[key]["Order"].items())[
                                        i : i + block[key]["Col"]
                                    ]
                                ):
                                    self.content += (
                                        r"""    \begin{subfigure}[t]{"""
                                        + str(1 / (block[key]["Col"] + 0.2))
                                        + r"""\textwidth}
        \centering"""
                                    )
                                    if block[key]["Col"] <= 2:
                                        self.content += (
                                            r"""
        \includegraphics{"""
                                            + plot
                                            + r"}"
                                        )
                                    if block[key]["Col"] > 2:
                                        self.content += (
                                            r"""
        \includegraphics[width=\textwidth]{"""
                                            + plot
                                            + r"}"
                                        )
                                    self.content += (
                                        r"""
        \caption{"""
                                        + str(block[key]["Order"][plot] or "")
                                        + r"""}
    \end{subfigure}
"""
                                    )
                                if (
                                    i >= (len(block[key]["Order"]) - block[key]["Col"])
                                    and "Caption" in block[key]
                                ):
                                    self.content += (
                                        r"  \caption{"
                                        + str(block[key]["Caption"] or "")
                                        + "}"
                                        + "\n"
                                    )
                                self.content += r"\end{figure}" + "\n"
                        else:
                            raise ValueError(
                                "'Col' value: expected integer, got "
                                + type(block[key]["Col"])
                            )

                    else:
                        raise KeyError("Missing 'Col' Key when writing Plot to LaTex")
        self.content += r"\end{document}"

    def generate_pdf(self, name):
        os.makedirs("/".join(name.split("/")[:-1]), exist_ok=True)
        with open(name[:-5] + ".report.tex", "w") as f:
            f.write(self.content)
        cmd = [
            "pdflatex",
            "-output-directory=" + "/".join(name.split("/")[:-1]),
            "-interaction",
            "batchmode",
            name[:-5] + ".report.tex",
        ]
        # pdflatex will be called twice to ensure consistent bookmarking (mainly for toc & lof)
        subprocess.run(cmd).check_returncode()
        subprocess.run(cmd)
        print("Report file generated successfully in " + "/".join(name.split("/")[:-1]))


##########################################################################################################


def main():
    filename = input("Enter file name: ")
    cwd = os.getcwd()
    filename = os.path.join(cwd, filename)
    print("Searching under " + cwd + " for given path...")
    if os.path.exists(filename):
        if filename.endswith(".yaml"):
            report(filename)
        else:
            if os.path.isdir(filename) and filename.split("/")[
                -1
            ] + ".yaml" in os.listdir(filename):
                report(os.path.join(filename, filename.split("/")[-1] + ".yaml"))
            else:
                main(filename + ".yaml")
    else:
        if not filename.endswith(".yaml"):
            filename = filename + ".yaml"
        while True:
            cmd = input(
                "\nA compatible yaml layout ("
                + filename.split("/")[-1]
                + ") cannot be found from "
                + "/".join(filename.split("/")[:-1])
                + ", generate new latex report with this path (Y), try a different path or exit(N): "
            )
            if cmd in ["y", "Y", "yes", "Yes"]:
                layout(filename, "/".join(filename.split("/")[:-1]))
                print(
                    "Layout file successfully written to "
                    + filename[:-5]
                    + "/"
                    + filename.split("/")[-1]
                )

                # Insert line below for auto compilation to LaTex of new yaml layout
                report(filename[:-5] + "/" + filename.split("/")[-1])
                break
            elif cmd in ["n", "N", "No", "no"]:
                break
            else:
                main(cmd)
                break


##########################################################################################################


if __name__ == "__main__":
    main()
