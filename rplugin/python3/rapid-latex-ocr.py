import pynvim
from rapid_latex_ocr import LaTeXOCR
from datetime import datetime
import subprocess
import os
import platform
from PIL import ImageGrab
@pynvim.plugin
class OCRPlugin(object):
    def __init__(self, nvim):
        self.nvim = nvim
        self.model = None
        self.delimiters = {}

    def load_model(self):
        """Load the OCR model."""
        self.nvim.out_write("Loading OCR model...\n")
        self.model = LatexOCR()
        self.nvim.out_write("Model loaded.\n")

    def process_image(self, img_path):
        """Process an image with the given OCR model."""
        if not self.model:
            self.nvim.err_write("OCR model is not loaded.\n")
            return None, None
        try:
            with open(img_path, "rb") as f:
                data = f.read()
            res, elapse = self.model(data)
            return res, elapse
        except Exception as e:
            self.nvim.err_write(f"Error processing image {img_path}: {e}\n")
            return None, None
    def is_wsl(self):
        try:
            with open("/proc/version", "r") as proc_version_file:
                proc_version_contents = proc_version_file.read().lower()
                # Check if the contents include "microsoft", indicating WSL
                return "microsoft" in proc_version_contents
        except FileNotFoundError:
            # If the file doesn't exist, we're likely not on Linux or WSL at all
            return False
    @pynvim.function('SetupDelimiters', sync=False)
    def SetupDelimiters(self, args):
        self.delimiters = args[0]

    def save_clipboard_image_to_file(self, file_path):
        # Determine the operating system
        os_name = platform.system()
        wsl = self.is_wsl()
        if wsl:              # Convert the Linux file path to a Windows-compatible path for PowerShell
            try:
                windows_file_path = subprocess.check_output(["wslpath", "-w", file_path]).decode().strip()
                command = ["powershell.exe", "-command", f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::GetImage().Save('{windows_file_path}')"]
                subprocess.run(command, check=True, capture_output=True)
                self.nvim.out_write(f"Image saved to {file_path}\n")
                return True
            except subprocess.CalledProcessError as e:
                self.nvim.err_write(f"Failed to save image from clipboard: {e}\n")
                return False
        elif os_name == 'Windows':
            # Windows-specific code
            try:
                img = ImageGrab.grabclipboard()
                if img is None:
                    self.nvim.err_write("No image in clipboard!\n")
                    return False
                img.save(file_path)
                self.nvim.out_write(f"Image saved to {file_path}\n")
                return True
            except Exception as e:
                self.nvim.err_write(f"Error saving image: {e}\n")
                return False
        elif os_name == 'Darwin':
            # macOS-specific code
            try:
                subprocess.run(['pngpaste', file_path], check=True)
                self.nvim.out_write(f"Image saved to {file_path}\n")
                return True
            except subprocess.CalledProcessError:
                self.nvim.err_write("No image in clipboard or pngpaste not installed.\n")
                return False
        elif os_name == 'Linux':
            # Linux-specific code, using xclip
            try:
                with open(file_path, 'wb') as f:
                    subprocess.run(['xclip', '-selection', 'clipboard', '-t', 'image/png', '-o'], stdout=f, check=True)
                self.nvim.out_write(f"Image saved to {file_path}\n")
                return True
            except subprocess.CalledProcessError:
                self.nvim.err_write("No image in clipboard or xclip not installed.\n")
                return False
        else:
            self.nvim.err_write(f"Unsupported OS: {os_name}\n")
            return False


    @pynvim.function('ImageToLatex', sync=False)
    def run_rapid_latex_ocr(self, args):
        if args[0] in self.delimiters:
            delim_left = self.delimiters[args[0]]['left']
            delim_right = self.delimiters[args[0]]['right']
        else:
            self.nvim.err_write(f"Error: No such delimiter '{args[0]}' registered. Available delimiters: {self.delimiters}\n")
            return
        row, col = self.nvim.current.window.cursor
        current_line = self.nvim.current.buffer[row-1]
        placeholder = delim_left + "LaTeX code being generated..." + delim_right
        new_line = current_line[:col] + placeholder + current_line[col:]
        self.nvim.current.buffer[row-1] = new_line
        # Move cursor to end of placeholder
        new_col = col + len(placeholder)
        self.nvim.current.window.cursor = (row, new_col)
        file_path = datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".png"
        if not self.save_clipboard_image_to_file(file_path):
            self.nvim.out_write("Could not save clipboard image, aborted operation")
            self.nvim.current.buffer[row-1] = current_line
            return
        if not self.model:
            self.nvim.out_write("Loading Model")
            self.load_model()
            self.nvim.out_write("Model Loaded")
            if not self.model:
                self.nvim.current.buffer[row-1] = current_line
                return
        output, elapse = self.process_image(file_path)
        output = delim_left + output + delim_right
        if not os.path.exists(file_path) or output is None:
            self.nvim.err_write("Failed to save clipboard image to file or process image\n")
            self.nvim.current.buffer[row-1] = current_line
            return
        current_line = self.nvim.current.buffer[row - 1]
        start = current_line.find(placeholder)
        if start != -1:
            crow, ccol = self.nvim.current.window.cursor
            end = start + len(placeholder)
            diff = ccol - end
            new_line = current_line[:start] + output + current_line[end:]
            self.nvim.current.buffer[row-1] = new_line
            # Move cursor to end of generated output
            if crow == row:
                new_col = ccol + len(output) - len(placeholder) + diff
            else:
                new_col = ccol
            self.nvim.current.window.cursor = (crow, new_col)
        os.remove(file_path)
        self.nvim.out_write("LaTeX code successfully generated and inserted.\n")
