import json
import re
from pathlib import Path


class JsonToHTML:
    def __init__(self,
                 json_file_path: str,
                 csv_file_path: str,
                 schema: dict,
                 output_file: str = "report.html"):
        self.json_file_path = json_file_path
        self.csv_file_path = csv_file_path
        self.output_file = output_file
        self.schema = schema
        self.table_of_contents = []
        self.names = self.read_csv_data()
    def read_csv_data(self):
        import csv
        with open(self.csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            names = {row['discord_username']: row['full_name'] for row in reader}
        return names
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
                    html += f"<{html_tag} id='{data['discord_username']}'>{key}</{html_tag}>"
                    self.table_of_contents.append(data['discord_username'])

                if isinstance(value, dict) and html_tag != "value":
                    html += process_data(value, schema[key]["fields"], key)
                elif isinstance(value, list):
                    # html += f"<{html_tag}>{key}</{html_tag}>"
                    for item in value:
                        if isinstance(item, str):
                            html += f"<li>{item}</li>"
                        elif isinstance(item, dict):
                            html += process_data(item, schema[key]["fields"], key)
                else:
                    if html_tag == "value" and parent_key:
                        if parent_key == 'student_summary':
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
        toc_html = "<h2>Table of Contents</h2>\n<ol>\n"
        for student_name in self.table_of_contents:
            toc_html += f"<li><a href='#{student_name}'>{student_name}</a></li>\n"
        toc_html += "</ol>\n"

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
                {html_content}
            </div>
            <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.bundle.min.js"></script>
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
    json_file_path = r"D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\course_data\mongo_database_backup\chatbot_data\database_backup\humon-chatbot.student_summaries_complete_2023-06-06.json"
    csv_file_path = r"D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\course_data\student_info\student_info_combined.csv"
    output_file_path = str(Path(json_file_path).parent.parent.parent.parent / "student_report.html")

    schema = {
        "discord_username": {"html_tag": "h1", "fields": {}},
        "student_summary": {"html_tag": "h2", "fields": {"summary": {"html_tag": "value", "fields": {}}}}
    }

    converter = JsonToHTML(json_file_path=json_file_path,
                           csv_file_path=csv_file_path,
                           schema=schema,
                           output_file=output_file_path)
    converter.generate_report()
