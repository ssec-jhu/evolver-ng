import socket

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from evolver import __project__, __version__

html_app = FastAPI()


@html_app.get("/network", operation_id="network_state_html", response_class=HTMLResponse)
async def network_html():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    html_content = f"""
    <html>
        <head>
            <title>Evolver</title>
        </head>
        <body>
            <h1>device network details</h1>
            <p>Running '{__project__}' ver: '{__version__}'</p>
            <p>Hostname: {hostname}</p>
            <p>IP Address: {ip_address}</p>
        </body>
    </html>
    """
    return html_content
