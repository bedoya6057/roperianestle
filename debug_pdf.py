from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def test_pdf_logo():
    output_filename = "debug_logo.pdf"
    c = canvas.Canvas(output_filename, pagesize=letter)
    width, height = letter
    
    # 1. Define paths to test
    paths_to_test = [
        os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "logo.png"),
        r"c:\Users\sodexo\Laptop Sodexo Sincronizada\OneDrive\Documentos\Sodexo\Laptop Sodexo\Documentos\Nueva carpeta\roperia-system\frontend\public\logo.png"
    ]

    y_pos = height - 100
    
    c.drawString(50, height - 50, "Debug PDF Logo Test")

    for i, logo_path in enumerate(paths_to_test):
        abs_path = os.path.abspath(logo_path)
        exists = os.path.exists(abs_path)
        
        c.drawString(50, y_pos, f"Path {i}: {abs_path}")
        c.drawString(50, y_pos - 15, f"Exists: {exists}")
        
        if exists:
            try:
                # Draw small version
                c.drawImage(abs_path, 50, y_pos - 120, width=100, preserveAspectRatio=True, mask='auto')
                c.drawString(160, y_pos - 60, "v: Draw Success")
            except Exception as e:
                c.drawString(160, y_pos - 60, f"x: Draw Error: {e}")
        
        y_pos -= 150

    c.save()
    print(f"Generated {output_filename}")

if __name__ == "__main__":
    test_pdf_logo()
