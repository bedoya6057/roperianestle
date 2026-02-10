from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import os
import io

def diagnose_logo():
    logo_path = r"c:\Users\sodexo\Laptop Sodexo Sincronizada\OneDrive\Documentos\Sodexo\Laptop Sodexo\Documentos\Nueva carpeta\roperia-system\frontend\public\logo.png"
    output_pdf = "diagnosis_report.pdf"
    
    print(f"Analyzing: {logo_path}")
    
    if not os.path.exists(logo_path):
        print("ERROR: File not found!")
        return

    try:
        img = Image.open(logo_path)
        print(f"Format: {img.format}")
        print(f"Mode: {img.mode}")
        print(f"Size: {img.size}")
        
        c = canvas.Canvas(output_pdf, pagesize=letter)
        width, height = letter
        y = height - 50
        
        c.drawString(40, y, "Logo Diagnostic Report")
        y -= 20
        c.drawString(40, y, f"Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        y -= 50
        
        # Test 1: Direct Draw
        c.drawString(40, y, "1. Direct Draw:")
        try:
            c.drawImage(logo_path, 40, y - 100, width=150, preserveAspectRatio=True, mask='auto')
            c.drawString(200, y, "Success")
        except Exception as e:
            c.drawString(200, y, f"Failed: {e}")
        
        y -= 150
        
        # Test 2: Convert to RGB (Strip Alpha)
        c.drawString(40, y, "2. Converted to RGB (No Alpha):")
        try:
            rgb_img = img.convert('RGB')
            # Save to temporary buffer
            img_byte_arr = io.BytesIO()
            rgb_img.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            # Draw from reader
            import reportlab.lib.utils
            img_reader = reportlab.lib.utils.ImageReader(img_byte_arr)
            c.drawImage(img_reader, 40, y - 100, width=150, preserveAspectRatio=True)
            c.drawString(200, y, "Success")
        except Exception as e:
            c.drawString(200, y, f"Failed: {e}")

        c.save()
        print(f"Generated {output_pdf}")
        
    except Exception as e:
        print(f"CRITICAL ERROR analyzing image: {e}")

if __name__ == "__main__":
    diagnose_logo()
