import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo

from io import StringIO
from typing import Optional

from pdfminer.converter import TextConverter
from pdfminer.image import ImageWriter
from pdfminer.layout import LAParams, LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.utils import AnyIO


class CustomText(tk.Text):
    '''A text widget with a new method, highlight_pattern()

    example:

    text = CustomText()
    text.tag_configure("red", foreground="#ff0000")
    text.highlight_pattern("this should be red", "red")

    The highlight_pattern method is a simplified python
    version of the tcl code at http://wiki.tcl.tk/3246
    '''

    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

    def highlight_pattern(self, pattern, tag, start="1.0", end="end",
                          regexp=False):
        '''Apply the given tag to all text that matches the given pattern

        If 'regexp' is set to True, pattern will be treated as a regular
        expression according to Tcl's regular expression syntax.
        '''

        start = self.index(start)
        end = self.index(end)
        self.mark_set("matchStart", start)
        self.mark_set("matchEnd", start)
        self.mark_set("searchLimit", end)

        count = tk.IntVar()
        while True:
            index = self.search(pattern, "matchEnd", "searchLimit",
                                count=count, regexp=regexp)
            if index == "":
                break
            if count.get() == 0:
                break  # degenerate pattern which matches zero-length strings
            self.mark_set("matchStart", index)
            self.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
            self.tag_add(tag, "matchStart", "matchEnd")


class TextConverterByLine(TextConverter):
    def __init__(
            self,
            rsrcmgr: PDFResourceManager,
            outfp: AnyIO,
            keywords: list,
            codec: str = "utf-8",
            pageno: int = 1,
            laparams: Optional[LAParams] = None,
            showpageno: bool = False,
            imagewriter: Optional[ImageWriter] = None,
    ) -> None:
        super().__init__(rsrcmgr, outfp, codec=codec, pageno=pageno, laparams=laparams, showpageno=showpageno,
                         imagewriter=imagewriter)
        self.keywords = keywords
        self.accumulated_line = ""
        self.keyword_to_page = {}
        self.keyword_to_lines = {}
        self.lines_to_keywords = {}
        self.curr_page_no = -1

    def write_text(self, text: str) -> None:
        self.accumulated_line += text
        if text == "\n":
            for keyword in self.keywords:
                if self.accumulated_line.find(keyword) != -1:
                    super().write_text(self.accumulated_line)
                    if keyword in self.keyword_to_page:
                        self.keyword_to_page[keyword].append(self.curr_page_no)
                    else:
                        self.keyword_to_page[keyword] = [self.curr_page_no]
                    if keyword in self.keyword_to_lines:
                        self.keyword_to_lines[keyword].append(self.accumulated_line)
                    else:
                        self.keyword_to_lines[keyword] = [self.accumulated_line]
            self.accumulated_line = ""

    def receive_layout(self, ltpage: LTPage):
        self.curr_page_no = ltpage.pageid
        super().receive_layout(ltpage)


def pdf_miner(file_path, keywords):
    output_string = StringIO()
    with open(file_path, 'rb') as in_file:
        parser = PDFParser(in_file)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = TextConverterByLine(rsrcmgr, output_string, keywords=keywords, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(doc):
            interpreter.process_page(page)
    print(output_string.getvalue())
    for kv in device.keyword_to_page.items():
        print("Keyword %s in pages: %s" % (kv[0], ",".join(map(str, kv[1]))))
    return device.keyword_to_lines, device.keyword_to_page


fs = None


def select_file():
    filetypes = (
        ('text files', '*.pdf'),
        ('All files', '*.*')
    )
    filename = fd.askopenfilename(
        title='Open a file',
        initialdir='/',
        filetypes=filetypes)
    fs.set(filename)


def mine_pdf_update_widget(text_box, file_path, keywords):
    kl, kp = pdf_miner(file_path, keywords)

    s = ""
    for k, lines in kl.items():
        s += k + ":\n"
        for l in lines:
            s += "\t"+l+"\n"
    s += "\n\n"
    for k, pages in kp.items():
        s += k + ": " + ",".join(map(lambda p: str(p), pages)) + "\n"
    text_box.insert(tk.END, s)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # create the root window
    root = tk.Tk()
    fs = tk.StringVar()
    fs.set("No file chosen yet")
    root.title('Tkinter Open File Dialog')
    frm = tk.Frame(root)
    frm.grid()
    tk.Label(frm, textvariable=fs).grid(column=0, row=0, padx=(10, 10), pady=(10, 10))
    # open button
    tk.Button(
        frm,
        text='Open a File',
        command=select_file
    ).grid(column=1, row=0, padx=(10, 10))
    tk.Label(frm, text="Keyword:").grid(row=1, padx=(10, 10), pady=(10, 10))
    kwEntry = tk.Entry(frm)
    kwEntry.grid(row=1, column=1, padx=(10, 10))
    textBox = tk.Text(frm)
    textBox.grid(row=2, padx=(10, 10))
    tk.Button(
        frm,
        text="Search",
        command=lambda: mine_pdf_update_widget(textBox, fs.get(), [kwEntry.get()])
    ).grid(row=1, column=2, padx=(10, 10), pady=(10, 10))
    root.mainloop()
