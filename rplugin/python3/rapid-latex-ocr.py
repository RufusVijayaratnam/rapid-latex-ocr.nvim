import pynvim
from rapid_latex_ocr import LatexOCR
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
        file_path = datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".png"
        if not self.save_clipboard_image_to_file(file_path):
            self.nvim.out_write("Could not save clipboard image, aborted operation")
            return

        if not self.model:
            self.nvim.out_write("Loading Model")
            self.load_model()
            self.nvim.out_write("Model Loaded")
        
        if not os.path.exists(file_path):
            self.nvim.err_write("Failed to save clipboard image to file\n")
            return    
        row, col = self.nvim.current.window.cursor
        current_line = self.nvim.current.buffer[row-1]
        placeholder = "LaTeX code being generated..."
        new_line = current_line[:col] + placeholder + current_line[col:]
        self.nvim.current.buffer[row-1] = new_line    
        output, elapse = self.process_image(file_path)
        if output is None:
            self.nvim.err_write("Failed to process image\n")
            return    
        current_line = self.nvim.current.buffer[row-1]
        start = current_line.find(placeholder)
        if start != -1:
            end = start + len(placeholder)
            new_line = current_line[:start] + output + current_line[end:]
            self.nvim.current.buffer[row-1] = new_line    
        os.remove(file_path)
        self.nvim.out_write("LaTeX code successfully generated and inserted.\n")
