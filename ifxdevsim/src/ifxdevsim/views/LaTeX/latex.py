# latex.py - Lam Ha

import os
import subprocess
from ...logger import Logger
from copy import deepcopy
from itertools import cycle
import seaborn
import csv

# import yaml

default_config = {
    "data_plot_type": {"default": "scatter2d"},
    "xlabel": "",
    "ylabel": "",
    "width": "10cm",
    "height": "10cm",
    "title": "",
    "title style":  r"{align=center,font=\bfseries}",
    "axis": "axis",
    "legend pos": "outer north east",
}

sample_input = {
    "param1": {
        "view_id": "08022003",
        "config": {
            "xlabel": "day la truc x",
            "ylabel": "day la truc y",
            "title": "sample plot title",
        },
        "data": {
            "line1": "(0,23.1)(10,27.5)(20,32)(30,37.8)(40,44.6)(60,61.8)(80,83.8)(100,114)",
            "line2": "(0,3.1)(10,7.5)(20,12)(30,17.8)(40,24.6)(60,41.8)(80,63.8)(100,94)",
        },
        "sim_data": {"sim1": "(0,5)(10,10)(20,15)(30,20)(40,25)(60,30)(80,35)(100,40)"},
    }
}
sample_input2 = {
    "param2": {
        "view_id": "08022003",
        "config": {
            "xlabel": "day la truc x",
            "ylabel": "day la truc y",
            "title": "sample plot title",
        },
        "data": {
            "line1": "(0,23.1)(10,27.5)(20,32)(30,37.8)(40,44.6)(60,61.8)(80,83.8)(100,114)",
            "line2": "(0,3.1)(10,7.5)(20,12)(30,17.8)(40,24.6)(60,41.8)(80,63.8)(100,94)",
        },
        "sim_data": {"sim1": "(0,5)(10,10)(20,15)(30,20)(40,25)(60,30)(80,35)(100,40)"},
    }
}
# NOTES:
# - add 'grouping plots' to separate overlapping plots ?

import re


def sort_key(corner, config):
    if corner == "measure":
        return 1
    elif corner == config.get("measure_corner"):
        return 0
    else:
        return 2


class Plot:
    def __init__(self, data_input, name):
        # MISSING: load default config from external file.
        self.plot_list = {"scatter2d", "line2d", "smoothline2d"}
        self.name = re.sub(r"[~_]", "-", name)
        self.data = data_input
        self.content = ""
        self.dir = None
        self.load_name(data_input)
        self.finalize_tex()
        if self.config.get("rawdata", False):
            self.write_raw()
        self.generate_pdf()

    def load_name(self, data_input):
        logger = Logger()

        color_palette = seaborn.color_palette("muted")
        colors = ["{" + f"{rgb[0]},{rgb[1]},{rgb[2]}" + "}" for rgb in color_palette]
        color_select = []
        for i, color in enumerate(colors):
            color_select.append(f"color{i}")
            self.content += (
                r"\definecolor" + "{" + f"color{i}" + "}" + "{rgb}" + color + "\n"
            )

        color_cycle = cycle(color_select)
        meas_color = dict()
        sorted_corners = sorted(
            data_input.keys(),
            key=lambda corner: sort_key(corner, data_input[corner].get("config", {})),
        )
        for corner in sorted_corners:
            local_default_config = deepcopy(default_config)
            local_default_config.update(data_input[corner]["config"])
            self.config = self.escape_for_latex(local_default_config)
            self.config['title'] = self.insert_backslashes(self.config['title'],int(self.config.get('title width',25)))
            self.dir = self.dir or self.config["dirname"]
            corner_specific_config = self.get_config_or_default(
                corner, self.config.get("corner_specific", {})
            )
            data = data_input[corner]["data"]
            for p, ds in data.items():
                if self.config['axis'] == "semilogyaxis":
                    ds = list(map(lambda q: (q[0],abs(q[1])),ds))
                if self.config['axis'] == "semilogxaxis":
                    ds = list(map(lambda q: (abs(q[0]),q[1]),ds))
                if self.config['axis'] == "loglogaxis":
                    ds = list(map(lambda q: (abs(q[0]),abs(q[1])),ds))

                if corner == self.config.get("measure_corner"):
                    corner_specific_config["color"] = next(color_cycle)
                    meas_color[p] = corner_specific_config["color"]
                elif corner == "measure":
                    corner_specific_config["color"] = meas_color.get(p, colors[0])
                    if not meas_color.get(p):
                        logger.warning(
                            f"measure_corner view configuration is not defined.  Guessing measurement values align with {list(data_input.keys())[0]}\nSet measure_corner under the texgraph view config to remove this message."
                        )
                else:
                    corner_specific_config["color"] = next(color_cycle)
                if p is None:
                    self.plot(corner, ds, corner, corner_specific_config)
                else:
                    tmp_corner = f"{corner} {p:.3g}"
                    self.plot(corner, ds, tmp_corner, corner_specific_config)

    def get_config_or_default(self, corner, config):
        return config.get(corner, config.get("default", {}))

    def escape_for_latex(self, config: dict):
        new_dict = {}
        to_escape = ["xlabel", "ylabel", "title"]
        for key, value in config.items():
            if isinstance(value, dict):
                new_dict[key] = self.escape_for_latex(value)
            elif isinstance(value, str) and key in to_escape:
                new_value = re.sub(r"([#$%&~_^\\{}])", r"\\\1", value)
                new_dict[key] = "{" + new_value + "}"
            else:
                new_dict[key] = value
        return new_dict

    def insert_backslashes(self, string, width=25):
        words = string.split()
        lines = []
        current_line = words[0]
        for word in words[1:]:
            if len(current_line) + 1 + len(word) <= width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return r" \\ ".join(lines)


    def escape_latex_str(self, s):
        if isinstance(s, str):
            new_value = re.sub(r"([#$%&~_^\\{}])", r"\\\1", s)
            return new_value
        else:
            return s

    def write_raw(self):
        plotdir = os.path.join(self.dir, "plots")
        config = self.config
        row = dict()
        for corname, cordata in self.data.items():
            csvname = self.name + f"_{corname}_raw.csv"
            with open(os.path.join(plotdir, csvname), "w") as csvfile:
                config = cordata["config"]
                header = [config["xlabel"], config.get("plabel", "p"), config["ylabel"]]
                writer = csv.DictWriter(csvfile, header)
                writer.writeheader()
                data = cordata["data"]
                for p, ds in data.items():
                    for x, y in ds:
                        row[config["xlabel"]] = x
                        row[config["ylabel"]] = y
                        row[config.get("plabel", "p")] = p
                        writer.writerow(row)

    def add_corner_specific_styling(self, config):
        out = ""
        for param, val in config.items():
            if val is True:
                out += f"{param}, "
            else:
                out += f"{param}={val}, "
        return out

    def add_styling(self):
        space = 3
        out = ""
        ignore = ["axis", "measure_corner", "plabel", "rawdata", "dirname","title width"]
        for param, val in self.config.items():
            comma = ","
            if isinstance(val, dict):
                continue
            if param in ignore:
                continue
            out += f"{' ' * space * 3}{param}={val}{comma}\n"
        return out

    def finalize_tex(self):
        self.content = (
            r"""
    \begin{tikzpicture}[baseline]
        \begin{%(axis)s}["""
            % self.config
            + "\n"
            + self.add_styling()
            + """]"""
            + self.content
            + r"""
        \end{%(axis)s}
    \end{tikzpicture}"""
            % self.config
        )

    def generate_pdf(self):
        logger = Logger()
        plotdir = os.path.join(self.dir, "plots")
        cwd = os.getcwd()
        os.makedirs(plotdir, exist_ok=True)
        texpath = os.path.join(plotdir, self.name + ".tex")
        with open(texpath, "w") as f:
            f.write(
                r"""\documentclass[16pt]{standalone}
\usepackage{pgfplots} \pgfplotsset{compat=1.16}
\usepackage{tikz}
\begin{document}"""
                + self.content
                + r"""
\end{document}"""
            )
        # logger.info("Plot info written to " + self.name + ".tex.")
        pdfname = os.path.splitext(texpath)[0] + ".pdf"
        self.pdfname = pdfname
        if os.path.exists(pdfname):
            os.unlink(pdfname)
        cmd = [
            "pdflatex",
            "-interaction",
            "batchmode",
            "--output-directory",
            "plots",
            "-shell-escape",
            texpath,
        ]
        # logger.info(f"Running {' '.join(cmd)}")
        devnull = subprocess.DEVNULL
        try:
            subprocess.run(cmd, stdout=devnull, stderr=devnull).check_returncode()
        except subprocess.CalledProcessError as e:
            if os.path.exists(pdfname) and os.stat(pdfname).st_size > 0:
                logger.warning(f"{pdfname} was generated with some latex warnings")
            else:
                raise (e.output)
        os.unlink(os.path.join(plotdir, self.name + ".aux"))
        os.unlink(os.path.join(plotdir, self.name + ".log"))

    def plot(self, corner, data, corner_text, corner_specific_config):
        self.content += (
            r"""
            \addplot+["""
            + self.add_corner_specific_styling(corner_specific_config)
            + r"""
            ] coordinates{%s};"""
            % self.to_latex_sweep(data)
            + "\n"
            + r"\addlegendentry{%s}" % self.escape_latex_str(corner_text)
        )

    def to_latex_sweep(self, data_arr):
        uniq_sorted = sorted(
            [list(q) for q in set(tuple(item) for item in data_arr)],
            key=lambda q: float(q[0]),
        )
        return "".join(map(lambda q: f"({','.join(map(str,q))})", uniq_sorted))


#################################################################################################
