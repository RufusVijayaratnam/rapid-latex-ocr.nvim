import pynvim
from rapid_latex_ocr import LatexOCR
from datetime import datetime
import subprocess
@pynvim.plugin
class OCRPlugin(object):
    def __init__(self, nvim):
        self.nvim = nvim
        self.model = None
    @pynvim.function('LoadOCRModel', sync=True)
    def load_model(self, args):
        """Load the OCR model."""
        self.nvim.out_write("Loading OCR model...\n")
        self.model = LatexOCR()
        self.nvim.out_write("Model loaded.\n")
    def process_image(self, img_path):
        """Process an image with the given OCR model."""
        if not self.model:
            self.nvim.err_write("OCR model is not loaded.\n")
            return
        try:
            with open(img_path, "rb") as f:
                data = f.read()
            res, elapse = self.model(data)
            return res, elapse
        except Exception as e:
            self.nvim.err_write(f"Error processing image {img_path}: {e}\n")
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
        os_name = subprocess.getoutput("uname") or "Windows"
        win_cmd = f"powershell.exe -command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::GetImage().Save('{file_path}', [System.Drawing.Imaging.ImageFormat]::Png)\""
        macos_cmd = f"osascript -e 'tell application \"System Events\" to write (the clipboard as JPEG picture) to (POSIX file \"{file_path}\")'"
        linux_cmd = f"xclip -selection clipboard -t image/png -o > \"{file_path}\""
        if os_name == "Darwin":  # macOS
            command = macos_cmd
        elif os_name == "Linux":  # Linux
            if is_wsl():
                command = win_cmd  
            else:
                command = linux_cmd
        else:  # Assuming Windows if not macOS or Linux
            command = win_cmd
        os.system(command)

    @pynvim.function('ImageToLatex', sync=True)
    def run_rapid_latex_ocr(self, args):
        file_path = datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + ".png"
        self.save_clipboard_image_to_file(file_path)
        
        if not self.model:
            self.load_model()
        
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
