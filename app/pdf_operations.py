from fpdf import FPDF

def create_pdf_from_images(image_paths, output_path):
    pdf = FPDF()
    for image_path in image_paths:
        pdf.add_page()
        pdf.image(image_path, x=10, y=10, w=180)
    pdf.output(output_path)