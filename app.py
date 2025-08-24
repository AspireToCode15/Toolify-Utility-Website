from flask import (
    Flask, render_template, request, url_for, send_from_directory, redirect, flash, Response
)
import os
from pdf2docx import Converter
from docx2pdf import convert
import docx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
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
from PIL import Image
from tools_backend.mp4_to_mp3 import convert_mp4_to_mp3
import qrcode
import fitz
from docx import Document
import pypandoc
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from werkzeug.utils import secure_filename
import requests
from pymongo import MongoClient
import nltk

nltk_data_path = os.path.join(os.path.dirname(__file__), "nltk_data")
os.makedirs(nltk_data_path, exist_ok=True)
nltk.data.path.append(nltk_data_path)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', download_dir=nltk_data_path)

app = Flask(__name__)
app.secret_key = 'kuchbhi_123_secret'

client = MongoClient('mongodb://localhost:27017/')
db = client['toolify']
feedback_collection = db['feedback']

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
        name = request.form['name']
        email = request.form['email']
        rating = request.form['rating']
        message = request.form['message']
        feedback_data = {'name': name, 'email': email, 'rating': rating, 'message': message}
        feedback_collection.insert_one(feedback_data)
        flash('Thank you for your feedback!', 'success')
        return redirect('/feedback')
    return render_template('feedback.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/view-feedback')
def view_feedback():
    auth = request.authorization
    if not auth or not (auth.username == "admin" and auth.password == "toolify123"):
        return Response("Could not verify your access.\n\nPlease provide correct username and password.",
                        401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    feedbacks = feedback_collection.find().sort("_id", -1)
    return render_template('view_feedback.html', feedbacks=feedbacks)

@app.route("/youtube_downloader", methods=["GET", "POST"])
def youtube_downloader():
    if request.method == "POST":
        video_url = request.form.get("url")
        if not video_url or not video_url.startswith(("http://", "https://")):
            return render_template("youtube_downloader.html", message="❌ Please enter a valid YouTube URL.")
        try:
            ffmpeg_path = r"C:\\path\\to\\ffmpeg\\bin"
            aria2c_path = r"C:\\path\\to\\aria2"
            os.environ["PATH"] += os.pathsep + ffmpeg_path + os.pathsep + aria2c_path

            aria2c_available = shutil.which("aria2c") is not None
            unique_id = str(uuid.uuid4())
            output_path = os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.%(ext)s")

            command = ["yt-dlp", "--force-ipv4", "-f", "bv*+ba/b", "-o", output_path]
            if aria2c_available:
                command += ["--external-downloader", "aria2c", "--external-downloader-args", "-x 16 -k 1M"]
            command.append(video_url)

            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            if result.returncode != 0:
                return render_template("youtube_downloader.html", message=f"❌ yt-dlp error:\n\n{result.stderr}")

            for ext in ['mp4', 'mkv', 'webm']:
                path = os.path.join(DOWNLOAD_FOLDER, f"{unique_id}.{ext}")
                if os.path.exists(path):
                    file_url = url_for('static', filename=f"downloads/{unique_id}.{ext}")
                    return render_template("youtube_downloader.html", filename=f"{unique_id}.{ext}", file_url=file_url)

            return render_template("youtube_downloader.html", message="❌ Download failed.")
        except subprocess.TimeoutExpired:
            return render_template("youtube_downloader.html", message="❌ Timeout.")
        except Exception as e:
            return render_template("youtube_downloader.html", message=f"❌ Error:\n\n{str(e)}")
    return render_template("youtube_downloader.html")

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
            original = Image.open(image)
            output_filename = f"{uuid.uuid4()}.{fmt.lower()}"
            output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)
            original.save(output_path, format=fmt.upper())
            file_url = url_for('static', filename=f"downloads/{output_filename}")
            return render_template("image_converter.html", filename=output_filename, file_url=file_url)
        except Exception as e:
            return render_template("image_converter.html", error=f"❌ Conversion failed: {str(e)}")
    return render_template("image_converter.html")

@app.route("/text_summarizer", methods=["GET", "POST"])
def text_summarizer():
    summary = None
    if request.method == "POST":
        raw_text = request.form["text"]
        parser = PlaintextParser.from_string(raw_text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, 3)
        summary = " ".join(str(sentence) for sentence in summary_sentences)
    return render_template("text_summarizer.html", summary=summary)

ureg = pint.UnitRegistry()
UNIT_OPTIONS = {
    "Length": ["meter", "kilometer", "centimeter", "millimeter", "mile", "yard", "foot", "inch"],
    "Mass": ["kilogram", "gram", "milligram", "pound", "ounce"],
    "Volume": ["liter", "milliliter", "gallon", "quart", "pint", "cup", "fluid_ounce"]
}

@app.route('/unit_converter', methods=['GET', 'POST'])
def unit_converter():
    context = {
        "unit_options": UNIT_OPTIONS,
        "result": None,
        "error": None,
        "value": 1,
        "from_unit": "meter",
        "to_unit": "kilometer"
    }
    if request.method == 'POST':
        try:
            context['value'] = float(request.form.get('value'))
            context['from_unit'] = request.form.get('from_unit')
            context['to_unit'] = request.form.get('to_unit')
            from_quantity = context['value'] * ureg(context['from_unit'])
            to_quantity = from_quantity.to(ureg(context['to_unit']))
            context['result'] = round(to_quantity.magnitude, 6)
        except pint.errors.DimensionalityError:
            context['error'] = f"Cannot convert from '{context['from_unit']}' to '{context['to_unit']}'. Units are not compatible."
        except Exception as e:
            context['error'] = "An unexpected error occurred during conversion."
    return render_template('unit_converter.html', **context)

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
                c = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter
                text = c.beginText(1 * inch, height - 1 * inch)
                text.setFont("Helvetica", 12)
                max_height = 1 * inch
                line_height = 14
                for para in doc.paragraphs:
                    if text.getY() <= max_height:
                        c.drawText(text)
                        c.showPage()
                        text = c.beginText(1 * inch, height - 1 * inch)
                        text.setFont("Helvetica", 12)
                    text.textLine(para.text)
                c.drawText(text)
                c.showPage()
                c.save()
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
