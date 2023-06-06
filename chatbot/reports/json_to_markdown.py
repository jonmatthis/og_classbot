import json


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
        def process_data(data, schema, level=1):
            markdown = ""
            for key, value in data.items():
                if key not in schema:
                    continue

                if isinstance(value, dict):
                    markdown += f"{'#' * level} {key}\n\n"
                    markdown += process_data(value, schema[key], level + 1)
                elif isinstance(value, list):
                    markdown += f"{'#' * level} {key}\n\n"
                    for item in value:
                        if isinstance(item, str):
                            markdown += f"- {item}\n"
                        elif isinstance(item, dict):
                            markdown += process_data(item, schema[key], level + 1)
                    markdown += "\n"
                else:
                    markdown += f"**{key}:** {value}\n\n"
            return markdown

        markdown = ""
        for item in json_data:
            markdown += process_data(item, self.schema)
        return markdown

    def write_to_markdown_file(self, markdown_content: str):
        with open(self.output_file, "w", encoding="utf-8") as file:
            file.write(markdown_content)

    def generate_markdown_report(self):
        json_data = self.read_json_data()
        markdown_content = self.format_json_to_markdown(json_data)
        self.write_to_markdown_file(markdown_content)


if __name__ == "__main__":
    json_file_path = r"D:\Dropbox\Northeastern\Courses\neural_control_of_real_world_human_movement\mongo_database_backup\chatbot_data\database_backup\humon-chatbot.student_summaries_complete_2023-06-06.json"
    output_file = "report.md"

    schema = {
        "discord_username": {},
        "threads": {"summary": {"summary": {}}, },
        "student_summary": {"summary": {}}
    }

    converter = JsonToMarkdown(json_file_path=json_file_path, schema=schema, output_file=output_file)
    converter.generate_markdown_report()
