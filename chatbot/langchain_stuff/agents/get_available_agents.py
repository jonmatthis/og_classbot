from pathlib import Path

import toml




def load_all_agent_configuration_files() -> dict:
    available_agents = {}
    config_folder_path = Path(__file__).parent / "configuration_tomls"
    for toml_path in config_folder_path.glob("**/*.toml"):
        available_agents[toml_path.stem] = toml.load(toml_path)
    return available_agents

def get_agent_configuration(agent_name: str = None) -> dict:
    available_agents = load_all_agent_configuration_files()
    if agent_name is None:
        return list(available_agents.values())[0]
    else:
        return available_agents[agent_name]

def get_available_agents():
    available_agents = load_all_agent_configuration_files()
    return available_agents
