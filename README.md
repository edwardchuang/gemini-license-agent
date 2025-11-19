# NotebookLM / Gemini Enterprise License Management Agent

This project provides an ADK powered agent for managing enterprise licenses through the Google Cloud Discovery Engine API. It's designed to offer a robust, interactive command-line interface for listing subscriptions, and granting or revoking user licenses for NotebookLM / Gemini Enterprise ecosystems.

## Overview

The `gemini_license_agent` is built using the `google-adk` framework, interacting with Google Cloud APIs primarily through the `google-cloud-discoveryengine` client library, supplemented by direct RESTful calls where necessary.

## Core Components

-   **`license_agent/agent.py`**: Contains the main agent logic, tool definitions, and core instructions for license management.
-   **`root_agent`**: An instance of `google.adk.agents.llm_agent.Agent` configured to manage the license workflow.

## API Tool Functions

The agent exposes the following primary functions:

-   **`list_licenses()`**: Fetches and returns a list of all currently assigned user licenses.
-   **`list_subscriptions()`**: Lists all available license subscriptions and their usage statistics.
-   **`grant_license(user_id, license_config_path)`**: Grants a license to a specified user from a specified subscription.
-   **`revoke_license(user_id, license_config_path)`**: Revokes a license from a specified user.

## Setup & Configuration

To set up and run the agent, you need to configure the following environment variables in .env:

-   `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.
-   `GOOGLE_CLOUD_LOCATION`: The Google Cloud location for API calls (e.g., `global`).
-   `SUBSCRIPTION_ID`: (Optional) A default subscription ID to use if one is not selected interactively.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/edwardchuang/gemini-license-agent.git
    cd gemini-license-agent
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set environment variables:**
    Create a `.env` file in the `license_agent/` directory with your Google Cloud project details:
    ```
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=global
    # SUBSCRIPTION_ID=optional-default-subscription-id
    ```
    Or set them in your shell:
    ```bash
    export GOOGLE_CLOUD_PROJECT=your-project-id
    export GOOGLE_CLOUD_LOCATION=global
    ```

## Usage

Once configured, you can interact with the agent through the `google-adk` CLI.
Activate the virtual environment before execute the adk command.

Example: Web Interface
```bash
cd gemini-license-agent
adk web
```
Now access to http://127.0.0.1:8000 (default port)

Or, interact with a CLI interface
```bash
cd gemini-license-agent
adk run license_agent
```

Example commands:

-   **`list licenses`** - list current license usage/assignment status
-   **`list subscriptions`** - list subscriptions and seat usage status
-   **`assign license to <user/principle>`** - assign license to a user
-   **`revoke <user/principle>`** - revoke license of a user

Disclaimler: 

This is not an officially supported Google product. 
This project is intended for demonstration purposes only. It is not
intended for use in a production environment.
