import os
import base64
from urllib.parse import quote as urlquote
from flask import Flask, render_template
from flask_mail import Mail, Message
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import jinja2

# Configuration
UPLOAD_DIRECTORY = "temp"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# Initialize Flask server
server = Flask(__name__)
# Configure mail settings using environment variables
server.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
server.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 465))
server.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
server.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
server.config["MAIL_USE_TLS"] = False
server.config["MAIL_USE_SSL"] = True
mail = Mail(server)

# Initialize Dash app
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Email Modal
email_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Draft Email")),
        dbc.ModalBody(
            [
                dbc.Input(id="to-address", placeholder="Recipient Email", type="email"),
                dcc.Upload(
                    id="upload-data",
                    children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                    multiple=True
                ),
                html.Ul(id="file-list"),
                dbc.Textarea(id="text-area", placeholder="Add text here..."),
                dbc.Button("Send", id="send-button", color="success"),
                html.Div(id="output"),
            ]
        ),
        dbc.ModalFooter(dbc.Button("Close", id="close", color="secondary"))
    ],
    id="email-modal",
    is_open=False,
)

# Main Layout
app.layout = dbc.Container(
    [
        dbc.Button("Email Button", id="email-button"),
        email_modal,
    ]
)

# Functions
def save_file(name, content):
    """Decode and store a file uploaded with Plotly Dash."""
    data = content.encode("utf8").split(b";base64,")[1]
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))

def uploaded_files():
    """List the files in the upload directory."""
    return [f for f in os.listdir(UPLOAD_DIRECTORY) if os.path.isfile(os.path.join(UPLOAD_DIRECTORY, f))]

def file_download_link(filename):
    """Create a Plotly Dash 'A' element that downloads a file from the app."""
    return html.A(filename, href=f"/download/{urlquote(filename)}")

# Callbacks
@app.callback(
    Output("file-list", "children"),
    [Input("upload-data", "filename"), Input("upload-data", "contents")]
)
def update_output(uploaded_filenames, uploaded_file_contents):
    if uploaded_filenames is not None and uploaded_file_contents is not None:
        for name, data in zip(uploaded_filenames, uploaded_file_contents):
            save_file(name, data)

    files = uploaded_files()
    if not files:
        return [html.Li("No files yet!")]
    return [html.Li(file_download_link(filename)) for filename in files]

@app.callback(
    Output("email-modal", "is_open"),
    [Input("email-button", "n_clicks"), Input("close", "n_clicks")],
    [State("email-modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@app.callback(
    Output("output", "children"),
    [
        Input("send-button", "n_clicks"),
        State("to-address", "value"),
        State("upload-data", "contents"),
        State("text-area", "value"),
    ]
)
def pre_outreach_qc_email(n_clicks, to_address, file_contents, text):
    if n_clicks:
        msg = Message(
            "Please find the attached document.",
            sender=server.config["MAIL_USERNAME"],
            recipients=[to_address]
        )

        # Email content
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('./'))
        template = env.get_template("template/mail.html")
        msg.html = template.render(text=text)

        # Attach files
        for filename in uploaded_files():
            with open(os.path.join(UPLOAD_DIRECTORY, filename), "rb") as fp:
                msg.attach(filename, "application/octet-stream", fp.read())

        mail.send(msg)

        # Clean up uploaded files
        for filename in uploaded_files():
            os.remove(os.path.join(UPLOAD_DIRECTORY, filename))

        return "Your message has been sent."

    return ""

if __name__ == "__main__":
    server.run(debug=True)
