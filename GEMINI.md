# NotebookLM / Gemini Enterprise License Management Agent

This document provides a technical overview of the `gemini-license-agent`, an ADK-based agent for managing enterprise licenses through the Google Cloud Discovery Engine API.

## 1. Overview

The project's goal is to provide a robust, interactive agent capable of listing subscriptions, and granting or revoking user licenses. It is built using the `google-adk` framework and interacts with Google Cloud APIs using a combination of the `google-cloud-discoveryengine` client library and direct RESTful calls.

## 2. Core Components

-   **`agent.py`**: The main file containing all agent logic, tool definitions, and core instructions.
-   **`root_agent`**: An instance of `google.adk.agents.llm_agent.Agent` which is configured with the tools and instructions necessary to manage the license workflow.

## 3. API Tool Functions

The agent's capabilities are exposed through four primary functions:

-   **`list_licenses()`**: Fetches and returns a list of all currently assigned user licenses.
-   **`list_subscriptions()`**: Lists all available license subscriptions and their usage statistics.
-   **`grant_license()`**: Grants a license to a specified user from a specified subscription.
-   **`revoke_license()`**: Revokes a license from a specified user.

## 4. Key Architectural Decisions & Workarounds

Several key decisions and workarounds have been implemented to ensure robust and efficient operation.

### 4.1. Subscription Management Workflow

To solve the challenge of needing specific subscription identifiers for API calls, the following workflow was implemented:

1.  **Enriched Subscription Data**: The `list_subscriptions` function was updated to return a list of subscription objects, each containing both:
    -   `display_name`: A short, human-readable ID for the subscription (e.g., `my-subscription`).
    -   `config_path`: The full, unambiguous Google Cloud resource name (e.g., `projects/12345/locations/global/licenseConfigs/my-subscription`). This path includes the numeric **Project Number**, ensuring API calls are accurate.

2.  **Direct Path Forwarding**: The `grant_license` function was refactored to accept a `license_config_path` parameter directly. The agent is instructed to pass the `config_path` from the user's selection to this function, eliminating any ambiguity or need for the function to construct the path itself.

3.  **Agent Instruction**: The agent's core prompt explicitly guides it to use this workflow: list subscriptions, show the `display_name` to the user, and use the corresponding `config_path` for the grant/revoke action.

### 4.2. `revoke_license` Implementation

The `revoke_license` function has a specific implementation based on user requirements:

-   It uses the `batch_update_user_licenses` method with the `delete_unassigned_user_licenses` flag set to `True`.
-   **Crucially, it does not require or use a `license_config` parameter.** The user has specified this behavior, and the implementation reflects this. The function still requires a `license_config_path` parameter to satisfy the agent's workflow, but it is not used in the final API call.

### 4.3. Client Library Considerations

-   **RESTful Workaround**: The `list_subscriptions` function uses direct REST calls via the `requests` library. A `TODO` in the code notes this is a temporary workaround for a version conflict between the `google-cloud-discoveryengine` and `google-adk` libraries.
-   **API Field Changes**: During development, a `ValueError` indicated that the `license_config_path` field was being passed in the wrong part of the API request object. The code was corrected to pass it as `license_config` within the `UserLicense` object itself for the `grant_license` function. This highlights that the agent's functionality is sensitive to the specific version of the `google-cloud-discoveryengine` client library.

## 5. Setup & Configuration

The agent relies on the following environment variables for configuration:

-   `GOOGLE_CLOUD_PROJECT`: The text-based Google Cloud Project ID.
-   `GOOGLE_CLOUD_LOCATION`: The location for the API calls (e.g., `global`).
-   `SUBSCRIPTION_ID`: (Optional) A default subscription ID to use if one is not selected interactively.