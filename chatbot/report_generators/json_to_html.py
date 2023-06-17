import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from chatbot.student_info.load_student_info import load_student_info


class JsonToHTML:
    def __init__(self,
                 json_file_path: str,
                 schema: dict,
                 output_file: str = "report.html"):
        self.json_file_path = json_file_path
        self.output_file = output_file
        self.schema = schema
        self.table_of_contents = []
        self.student_info = load_student_info()


    def read_json_data(self):
        with open(self.json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    @staticmethod
    def format_summary(summary):
        summary = summary.replace("```", "")
        summary = re.sub(r'# (.*?):', r'<h3>\1</h3>', summary)
        summary = summary.replace('\n', '<br>')
        return summary

    def format_json_to_html(self, json_data):
        def process_data(data, schema, parent_key=None):
            html = ""
            for key, value in data.items():
                if key not in schema:
                    continue

                html_tag = schema[key].get("html_tag", "p")
                if html_tag == "h1":
                    html += f"<{html_tag} id='{data['_student_name']}'></{html_tag}>"
                    self.table_of_contents.append(data['_student_name'])

                if isinstance(value, dict) and html_tag != "value":
                    html += process_data(value, schema[key]["fields"], key)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            html += f"<li>{item}</li>"
                        elif isinstance(item, dict):
                            html += process_data(item, schema[key]["fields"], key)
                else:
                    if html_tag == "value" and parent_key:
                        if parent_key == 'video_chatter_summary':
                            value = self.format_summary(value)
                            html += f"{value}<br>"
                            continue
                        html += f"<b> {value}<br>"
                    else:
                        html += f"<{html_tag}>{key}: {value}</{html_tag}>"
            return html

        html = ""
        for item in json_data:
            html += process_data(item, self.schema)
        return html

    def write_to_html_file(self, html_content: str):
        toc_html = "<div class='toc'><h2>Table of Contents</h2>\n<ul>\n"
        for student_name in self.table_of_contents:
            toc_html += f"<li><a href='#{student_name}'>{student_name}</a></li>\n"
        toc_html += "</ul>\n</div>"

        html = f"""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" rel="stylesheet">
            <title>Report</title>
          </head>
          <body>
            <div class="container mt-4">
                {toc_html}
                <div class="content">
                  {html_content}
                </div>
            </div>
            <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
          </body>
        </html>
        """
        with open(self.output_file, "w", encoding="utf-8") as file:
            file.write(html)

    def generate_report(self):
        json_data = self.read_json_data()
        html_content = self.format_json_to_html(json_data)
        self.write_to_html_file(html_content)


if __name__ == "__main__":
    load_dotenv()
    base_path = Path(os.getenv("PATH_TO_COURSE_DROPBOX_FOLDER"))
    json_file_path = base_path / "course_data" / "chatbot_data"/ "video_chatter_summaries.json"
    output_file_path = base_path /"course_data" / "video_chatter_summaries_report.html"

    schema = {
        "_student_name": {"html_tag": "h1", "fields": {}},
        "video_chatter_summary": {"html_tag": "h2", "fields": {"summary": {"html_tag": "value", "fields": {}}}},
        "thread_conversation": {"html_tag": "h2", "fields": {"summary": {"html_tag": "value", "fields": {}}}}
    }

    converter = JsonToHTML(json_file_path=str(json_file_path),
                           schema=schema,
                           output_file=str(output_file_path))
    converter.generate_report()

    print("Done!")

