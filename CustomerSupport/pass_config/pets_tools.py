from typing import List
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig

@tool(parse_docstring=True)
def update_favorite_pets(pets: List[str], config: RunnableConfig) -> None:
    """Add the list of favorite pets.

    Args:
        pets: List of favorite pets to set.
    """
    user_id = config.get("configurable", {}).get("user_id")
    # user_to_pets[user_id] = pets


@tool
def delete_favorite_pets(config: RunnableConfig) -> None:
    """ Delete the list of favorite pets."""
    user_id = config.get("configurable", {}).get("user_id")
    # if user_id in user_to_pets:
    #     del user_to_pets[user_id]


@tool
def list_favorite_pets(config: RunnableConfig):
    """List favorite pets if any."""
    user_id = config.get("configurable", {}).get("user_id")
    # return ", ".join(user_to_pets.get(user_id, []))


@tool
def fetch_user_info(config:RunnableConfig):
    """
    fetch user info.
    :param config:
    :return:
    """
    user_id = config.get("configurable", {}).get("user_id")
    print(user_id)
    return user_id
