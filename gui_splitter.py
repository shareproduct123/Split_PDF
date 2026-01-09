"""
GUI Interface for PDF Agreement Splitter
Simple tkinter interface for processing labor agreements
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import logging
from split_agreement import AgreementSplitter, batch_process

# Configure logging for GUI
class TextHandler(logging.Handler):
    """Custom logging handler to display logs in GUI"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)


class PDFSplitterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Labor Agreement Splitter")
        self.root.geometry("800x600")
        
        # Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.min_pages = tk.IntVar(value=2)
        self.merge_gap = tk.IntVar(value=5)
        self.batch_mode = tk.BooleanVar(value=False)
        self.processing = False
        
        self.create_widgets()
        self.setup_logging()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title = ttk.Label(main_frame, text="PDF Labor Agreement Splitter", 
                         font=('Helvetica', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=10)
        
        # Input section
        ttk.Label(main_frame, text="Input:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_input).grid(
            row=1, column=2, padx=5, pady=5)
        
        # Batch mode checkbox
        ttk.Checkbutton(main_frame, text="Batch Mode (Process all PDFs in folder)", 
                       variable=self.batch_mode).grid(
            row=2, column=1, sticky=tk.W, pady=5)
        
        # Output section
        ttk.Label(main_frame, text="Output:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(
            row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_output).grid(
            row=3, column=2, padx=5, pady=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(options_frame, text="Minimum pages per section:").grid(
            row=0, column=0, sticky=tk.W, padx=5)
        ttk.Spinbox(options_frame, from_=1, to=10, textvariable=self.min_pages, 
                   width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(options_frame, text="Merge gap (pages):").grid(
            row=0, column=2, sticky=tk.W, padx=5)
        ttk.Spinbox(options_frame, from_=1, to=20, textvariable=self.merge_gap, 
                   width=10).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.process_btn = ttk.Button(button_frame, text="Process", 
                                      command=self.process_files, width=15)
        self.process_btn.grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self.clear_log, 
                  width=15).grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Exit", command=self.root.quit, 
                  width=15).grid(row=0, column=2, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Processing Log", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), 
                      pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled', 
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)
    
    def setup_logging(self):
        """Setup logging to display in GUI"""
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add GUI handler
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(text_handler)
    
    def browse_input(self):
        """Browse for input file or folder"""
        if self.batch_mode.get():
            path = filedialog.askdirectory(title="Select folder containing PDFs")
        else:
            path = filedialog.askopenfilename(
                title="Select PDF file",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        
        if path:
            self.input_path.set(path)
    
    def browse_output(self):
        """Browse for output folder"""
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_path.set(path)
    
    def clear_log(self):
        """Clear the log text"""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')
    
    def process_files(self):
        """Process the PDFs"""
        if self.processing:
            messagebox.showwarning("Processing", "Already processing files!")
            return
        
        input_path = self.input_path.get()
        if not input_path:
            messagebox.showerror("Error", "Please select an input file or folder!")
            return
        
        if not Path(input_path).exists():
            messagebox.showerror("Error", "Input path does not exist!")
            return
        
        # Start processing in a separate thread
        self.processing = True
        self.process_btn.config(state='disabled')
        self.progress.start()
        
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()
    
    def _process_thread(self):
        """Processing thread"""
        try:
            input_path = self.input_path.get()
            output_path = self.output_path.get() if self.output_path.get() else None
            min_pages = self.min_pages.get()
            merge_gap = self.merge_gap.get()
            
            if self.batch_mode.get():
                # Batch processing
                results = batch_process(input_path, output_path, min_pages, merge_gap)
                success = sum(1 for r in results if r.get('success'))
                total_files = sum(r.get('files_created', 0) for r in results)
                
                self.root.after(0, lambda: messagebox.showinfo(
                    "Complete", 
                    f"Batch processing complete!\n\n"
                    f"Processed: {len(results)} PDFs\n"
                    f"Successful: {success}\n"
                    f"Files created: {total_files}"))
            else:
                # Single file processing
                splitter = AgreementSplitter(input_path, output_path, min_pages, merge_gap)
                result = splitter.process()
                
                if result['success']:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success", 
                        f"Processing complete!\n\n"
                        f"Files created: {result['files_created']}\n"
                        f"Output folder: {result['output_dir']}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", 
                        f"Processing failed:\n{result.get('error')}"))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"An error occurred:\n{str(e)}"))
        
        finally:
            self.root.after(0, self._processing_complete)
    
    def _processing_complete(self):
        """Called when processing is complete"""
        self.processing = False
        self.process_btn.config(state='normal')
        self.progress.stop()


def main():
    root = tk.Tk()
    app = PDFSplitterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
