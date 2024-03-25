# tableview.py - Lam Ha

# Notes:
# Tableview can now only work if specific columns are listed in .dso views config
# Tableview relies on the tex_preamble.sty file being in the correct dir (Please change file path acorrdingly)
# Tableview .tex output often requires 2 compilations for a stable pdf
##########################################################################################################

from pylatexenc.latexencode import unicode_to_latex
from .baseview import BaseView
import subprocess, os

##########################################################################################################


class TableView(BaseView):
    def __init__(self, id, *args):
        super().__init__(id)
        self.header = ""
        self.content = ""

    # def add_opts(self, opts):
    #     self.opts = opts

    def to_dso(self):
        output_file = self.opts.get("filename", None) or f"{self.id}.tex"
        tex_preamble_file = os.path.join(
            os.path.dirname(__file__), "LaTeX", "tex_preamble"
        )  # tex_preamble>sty is referenced here

        # self.more_header()
        self.add_rows()
        with open(output_file, "w") as f:
            f.write(
                r"""\documentclass[12pt]{article}
\usepackage{"""
                + tex_preamble_file
                + r"""} 
\begin{document}
    \pgfplotstabletypeset[
        every head row/.append style={
        before row={
            \toprule
            """+ self.header +r"""},
        after row={\midrule
        \endhead}
        },
        ]{
""" + unicode_to_latex(self.content) + r"""    }
\end{document}"""
            )

        # Comment/Uncomment below code to include pdflatex auto-compilation
        # cmd = [
        #     "pdflatex",
        #     "-interaction",
        #     "batchmode",
        #     "-shell-escape",
        #     output_file,
        # ]
        # subprocess.run(cmd).check_returncode()
        # subprocess.run(cmd)
        # os.unlink(".".join(output_file.split(".")[:-1]) + ".aux")
        # os.unlink(".".join(output_file.split(".")[:-1]) + ".log")

    def add_rows(self):
        columns = self.opts.get("columns")
        if not isinstance(columns, dict):
            raise ("Missing 'columns' atribute in tableview. Id: " + self.id)
        header_list = self.flatten_columns(columns)
        for header in header_list:
            self.content += header[-1] + ","
        self.content = unicode_to_latex(self.content[:-1]) + '\n'
        for key, param in self.params.items():
            self.params[key] = {k: param[k] for k in columns if k in param}
            for header in header_list:
                self.content += (
                    str(self.check_key_exist_recursive(self.params[key], header)) + ","
                )
            self.content = self.content[:-1] + "\n"

    def flatten_columns(self, columns, parent_key=None):
        if parent_key is None:
            parent_key = []
        items = []
        for k, v in columns.items():
            new_keys = parent_key + [k]
            if isinstance(v, dict):
                items.extend(self.flatten_columns(v, new_keys))
            else:
                items.append(new_keys)
        return items

    def check_key_exist_recursive(self, d, indices):
        if not indices:
            return d
        index = indices[0]
        if index in d:
            return self.check_key_exist_recursive(d[index], indices[1:])
        else:
            return ""

    # def more_header(self): 
    #     columns = self.opts.get("columns")
    #     header_list = self.flatten_columns(columns)
    #     for depth in range (-2 ,0 - len (max (header_list, key=len)) -1 , -1):
    #         count = 1
    #         header  = ''
    #         line = ''
    #         linecount = 0
    #         for item in range(0,len(header_list)- 1 , 1): 
    #             if depth < 0 - len(header_list[item]) or item >= len(header_list) - 1 or depth < 0 - len(header_list[item + 1]) or header_list[item][depth] != header_list[item + 1][depth] :
    #                 header += r'\multicolumn{'+ str(count) + r'}{c}{'+ unicode_to_latex(header_list[item][depth]) +r'} & \phantom{ab} & '
    #                 line += r'\cmidrule{'+str(linecount + 1) +'-' + str(linecount + count - 1) + '} '
    #                 linecount = linecount + count
    #                 count = 1
    #             else: 
    #                 count = count + 1
    #         self.header = header[:-15] +'\n' + line + '\n' +  self.header  
    def print_example_config(self):
        content = """
# Replace filename with output dso.csv name
# The columns option specifies desired columns in output csvs.
# Columns are specified in the same hierarchy as the dso.yml output.
views:
  FILENAME:
    type: table
    columns:
      device: true
      metrics: true
      control:
        simulator: false
        mode: true
      stimuli:
        vr: false
        """
        print(content)
                            
