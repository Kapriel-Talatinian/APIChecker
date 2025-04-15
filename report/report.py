from jinja2 import Environment, FileSystemLoader
import os

# Génère un rapport HTML à partir des résultats
def generate_html_report(data):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report_template.html")

    html_content = template.render(
        summary=data["summary"],
        details=data["details"]
    )

    return html_content
