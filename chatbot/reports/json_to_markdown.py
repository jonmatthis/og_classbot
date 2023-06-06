import json

import markdown


class JsonToMarkdown:
    def __init__(self,
                 json_file_path: str,
                 schema: dict,
                 output_file: str = "report.md"):
        self.json_file_path = json_file_path
        self.output_file = output_file
        self.schema = schema

    def read_json_data(self):
        with open(self.json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    def format_json_to_markdown(self, json_data):
        def process_data(data, schema, parent_key=None):
            markdown = ""
            for key, value in data.items():
                if key not in schema:
                    continue

                markdown_tag = schema[key].get("markdown_tag", "*")
                if isinstance(value, dict) and markdown_tag != "value":
                    markdown += f"{markdown_tag} {key}\n\n"
                    markdown += process_data(value, schema[key]["fields"], key)
                elif isinstance(value, list):
                    markdown += f"{markdown_tag} {key}\n\n"
                    for item in value:
                        if isinstance(item, str):
                            markdown += f"- {item}\n"
                        elif isinstance(item, dict):
                            markdown += process_data(item, schema[key]["fields"], key)
                    markdown += "\n"
                else:
                    # check if the markdown_tag is "value"
                    if markdown_tag == "value" and parent_key:
                        markdown += f"**{parent_key}:** {value}\n\n"
                    else:
                        markdown += f"{markdown_tag} {key}: {value}\n\n"
            return markdown

        markdown = ""
        for item in json_data:
            markdown += process_data(item, self.schema)
        return markdown

    def write_to_html_file(self, markdown_content: str):
        html = markdown.markdown(markdown_content)
        html = f"""
        <!doctype html>
        <html lang="en">
          <head>
            <!-- Required meta tags -->
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">

            <!-- Bootstrap CSS -->
            <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" rel="stylesheet">

            <title>Markdown Report</title>
          </head>
          <body>
            <div class="container mt-4">
                {html}
            </div>

            <!-- Optional JavaScript; choose one of the two! -->
            <!-- Option 1: jQuery and Bootstrap Bundle (includes Popper) -->
            <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.bundle.min.js"></script>
          </body>
        </html>
        """
        with open(self.output_file.replace(".md", ".html"), "w", encoding="utf-8") as file:
            file.write(html)

    def write_to_markdown_file(self, markdown_content: str):
        with open(self.output_file, "w", encoding="utf-8") as file:
            file.write(markdown_content)

    def generate_markdown_report(self):
        json_data = self.read_json_data()
        markdown_content = self.format_json_to_markdown(json_data)
        self.write_to_markdown_file(markdown_content)
        self.write_to_html_file(markdown_content)




if __name__ == "__main__":
    json_file_path = r"D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\mongo_database_backup\chatbot_data\database_backup\humon-chatbot.student_summaries_complete_2023-06-06.json"
    output_file = "report.md"

    schema = {
        "discord_username": {"markdown_tag": "#", "fields": {}},
        "student_summary": {"markdown_tag": "##", "fields": {"summary": {"markdown_tag": "value", "fields": {}}}}
    }

    converter = JsonToMarkdown(json_file_path=json_file_path, schema=schema, output_file=output_file)
    converter.generate_markdown_report()
