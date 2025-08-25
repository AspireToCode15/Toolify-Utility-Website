from flask import (
    Flask, render_template, request, url_for, send_from_directory, redirect, flash, Response, jsonify
)
import os
from pdf2docx import Converter
import docx
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import pint
import subprocess
import uuid
import shutil
import zipfile
import random
import string
import base64
from io import BytesIO
from pypdf import PdfWriter, PdfReader
from PIL import Image as PILImage
from tools_backend.mp4_to_mp3 import convert_mp4_to_mp3
import qrcode
import fitz
from werkzeug.utils import secure_filename
import requests
import markdown

app = Flask(__name__)
app.secret_key = 'kuchbhi_123_secret'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'downloads')
CONVERTED_FOLDER = os.path.join(BASE_DIR, 'static', 'converted')
AUDIO_FOLDER = os.path.join(BASE_DIR, 'static', 'tts_audio')
for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER, CONVERTED_FOLDER, AUDIO_FOLDER]:
    os.makedirs(folder, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        flash('This feature is temporarily disabled. Please check back later!', 'info')
        return redirect('/feedback')
    return render_template('feedback.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/view-feedback')
def view_feedback():
    return "This feature is temporarily disabled.", 404

@app.route("/markdown_editor", methods=["GET"])
def markdown_editor():
    return render_template("markdown_editor.html")

@app.route("/convert_markdown", methods=["POST"])
def convert_markdown():
    data = request.json
    md_text = data.get('markdown_text', '')
    html = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
    return jsonify({'html': html})

@app.route("/dictionary", methods=["GET", "POST"])
def dictionary():
    definition = None
    error = None
    word = None
    if request.method == "POST":
        word = request.form.get("word")
        if not word:
            error = "Please enter a word to search."
        else:
            try:
                api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                response = requests.get(api_url)
                if response.status_code == 200:
                    definition = response.json()[0]
                else:
                    error = f"Could not find a definition for '{word}'. Please check the spelling."
            except Exception as e:
                error = "An error occurred while connecting to the dictionary service."
    return render_template("dictionary.html", definition=definition, error=error, word=word)

@app.route("/mp4_to_mp3", methods=["GET", "POST"])
def mp4_to_mp3():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return render_template("mp4_to_mp3.html", error="❌ Please upload a valid MP4 file.")
        filename, error = convert_mp4_to_mp3(DOWNLOAD_FOLDER, file)
        if error:
            return render_template("mp4_to_mp3.html", error=error)
        file_url = url_for('static', filename=f"downloads/{filename}")
        return render_template("mp4_to_mp3.html", filename=filename, file_url=file_url)
    return render_template("mp4_to_mp3.html")

@app.route("/file_compressor", methods=["GET", "POST"])
def file_compressor():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return render_template("file_compressor.html", message="Please upload a file.")
        zip_id = str(uuid.uuid4())
        zip_filename = f"{zip_id}.zip"
        zip_path = os.path.join(DOWNLOAD_FOLDER, zip_filename)
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(file_path, arcname=file.filename)
        os.remove(file_path)
        return render_template("file_compressor.html", filename=zip_filename,
                                file_url=url_for("static", filename=f"downloads/{zip_filename}"))
    return render_template("file_compressor.html")

@app.route("/pdf_merger", methods=["GET", "POST"])
def pdf_merger():
    if request.method == "POST":
        files = request.files.getlist("pdfs")
        if not files or files[0].filename == "":
            return render_template("pdf_merger.html", error="Please upload at least two PDF files.")
        try:
            writer = PdfWriter()
            for file in files:
                reader = PdfReader(file)
                for page in reader.pages:
                    writer.add_page(page)
            merged_filename = f"{uuid.uuid4()}.pdf"
            merged_path = os.path.join(DOWNLOAD_FOLDER, merged_filename)
            with open(merged_path, "wb") as f_out:
                writer.write(f_out)
            return render_template("pdf_merger.html", filename=merged_filename,
                                    file_url=url_for("static", filename=f"downloads/{merged_filename}"))
        except Exception as e:
            return render_template("pdf_merger.html", error=f"❌ Merge failed: {str(e)}")
    return render_template("pdf_merger.html")

@app.route("/password_generator", methods=["GET", "POST"])
def password_generator():
    if request.method == "POST":
        length = int(request.form.get("length", 12))
        use_uppercase = 'uppercase' in request.form
        use_numbers = 'numbers' in request.form
        use_symbols = 'symbols' in request.form
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase if use_uppercase else ""
        digits = string.digits if use_numbers else ""
        symbols = string.punctuation if use_symbols else ""
        all_chars = lowercase + uppercase + digits + symbols
        if not all_chars:
            return render_template("password_generator.html", error="❌ Please select at least one character type.")
        password_chars = [random.choice(lowercase)]
        if uppercase: password_chars.append(random.choice(uppercase))
        if use_numbers: password_chars.append(random.choice(digits))
        if use_symbols: password_chars.append(random.choice(symbols))
        while len(password_chars) < length:
            password_chars.append(random.choice(all_chars))
        random.shuffle(password_chars)
        password = ''.join(password_chars[:length])
        return render_template("password_generator.html", password=password)
    return render_template("password_generator.html")

@app.route('/qr_generator', methods=['GET', 'POST'])
def qr_generator():
    qr_image = None
    error = None
    data = None
    if request.method == 'POST':
        data = request.form.get('data')
        if not data or not data.strip():
            error = "Please enter some data to generate a QR code."
        else:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                qr_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            except Exception as e:
                error = "An error occurred while generating the QR code."
    return render_template('qr_generator.html', qr_image=qr_image, error=error, data=data)

@app.route("/image_converter", methods=["GET", "POST"])
def image_converter():
    if request.method == "POST":
        image = request.files.get("image")
        fmt = request.form.get("format")
        if not image or not fmt:
            return render_template("image_converter.html", error="❌ Please upload an image and select a format.")
        try:
            original = PILImage.open(image)
            output_filename = f"{uuid.uuid4()}.{fmt.lower()}"
            output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
            original.save(output_path, format=fmt.upper())
            file_url = url_for('static', filename=f"downloads/{output_filename}")
            return render_template("image_converter.html", filename=output_filename, file_url=file_url)
        except Exception as e:
            return render_template("image_converter.html", error=f"❌ Conversion failed: {str(e)}")
    return render_template("image_converter.html")

@app.route('/word_to_pdf', methods=['GET', 'POST'])
def word_to_pdf():
    if request.method == 'POST':
        if 'word_file' not in request.files:
            return render_template('word_to_pdf.html', message="Form Error: No file part sent.")
        file = request.files['word_file']
        if file.filename == '':
            return render_template('word_to_pdf.html', message="No file selected.")
        if file and file.filename.lower().endswith(('.docx')):
            try:
                original_filename = secure_filename(file.filename)
                input_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
                file.save(input_path)
                doc = docx.Document(input_path)
                pdf_filename = f"{os.path.splitext(original_filename)[0]}.pdf"
                pdf_path = os.path.join(app.config['CONVERTED_FOLDER'], pdf_filename)
                styles = getSampleStyleSheet()
                elements = []
                for para in doc.paragraphs:
                    elements.append(Paragraph(para.text, styles['Normal']))
                    elements.append(Spacer(1, 12))
                pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
                pdf.build(elements)
                os.remove(input_path)
                return render_template('word_to_pdf.html', pdf_file=pdf_filename)
            except Exception as e:
                return render_template('word_to_pdf.html', message="Conversion failed. The file might be corrupt or in an unsupported format.")
        else:
            return render_template('word_to_pdf.html', message="Invalid file type. Please upload a .docx file.")
    return render_template('word_to_pdf.html')

@app.route('/pdf_to_word', methods=['GET', 'POST'])
def pdf_to_word():
    if request.method == 'POST':
        pdf_file = request.files.get('pdf_file')
        if not pdf_file or not pdf_file.filename.lower().endswith('.pdf'):
            return render_template('pdf_to_word.html', message="Please select a valid PDF file.")
        filename = secure_filename(pdf_file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(input_path)
        output_filename = filename.rsplit('.', 1)[0] + '.docx'
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], output_filename)
        try:
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            return render_template('pdf_to_word.html', word_file=output_filename)
        except Exception as e:
            error_message = f"Conversion Failed: {str(e)}"
            return render_template('pdf_to_word.html', message=error_message)
    return render_template('pdf_to_word.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(
            app.config['CONVERTED_FOLDER'], 
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        return "File not found!", 404
