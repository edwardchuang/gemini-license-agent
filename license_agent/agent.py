# Copyright 2025 Google LLC.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 

"""Agent for managing Gemini Enterprise / NotebookLM Enterprise licenses."""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse as parse_datetime

import logging

# --- Configuration & Logging ---
logger = logging.getLogger(__name__)

from google.adk.agents.llm_agent import Agent
from google.cloud import discoveryengine_v1
import google.auth
import google.auth.exceptions
from google.auth.transport import requests as auth_requests
import requests

# --- Constants ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
SUBSCRIPTION_ID = os.environ.get("SUBSCRIPTION_ID")
USER_STORE_ID = "default_user_store"  # Fixed value as per user instruction
BASE_API_URL = "https://global-discoveryengine.googleapis.com"


def _create_authed_session() -> Optional[auth_requests.AuthorizedSession]:
    """Creates a requests session with Google Cloud authentication.

    The session automatically handles token refreshing.

    Returns:
        An authorized session object, or None if credentials could not be
        obtained.
    """
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return auth_requests.AuthorizedSession(credentials)
    except google.auth.exceptions.DefaultCredentialsError as e:
        logger.error(f"Error getting default credentials: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during credential loading.
        logger.error(f"An unexpected error occurred during authentication: {e}")
        return None


def _get_subscription_details(
    session: requests.Session, subscription_name: str
) -> Optional[Dict[str, Any]]:
    """Fetches details for a single Subscription resource via REST API.

    Args:
        session: The authorized requests session to use for the API call.
        subscription_name: The full resource name of the subscription.

    Returns:
        A dictionary containing the subscription details, or None if an
        error occurred.
    """
    headers = {"X-Goog-User-Project": PROJECT_ID}
    url = f"{BASE_API_URL}/v1/{subscription_name}"

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling REST API: {e}")
        if e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response content: {e.response.text}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during the API request.
        logger.error(f"An unexpected error occurred: {e}")
        return None


# --- Tool Functions ---


def list_licenses() -> List[dict]:
    """Lists all user licenses in the configured NotebookLM user store.

    Returns:
        A list of user license objects, each represented as a dictionary.
    """
    client = discoveryengine_v1.UserLicenseServiceClient()
    parent = client.user_store_path(
        project=PROJECT_ID, location=LOCATION, user_store=USER_STORE_ID
    )
    request = discoveryengine_v1.ListUserLicensesRequest(parent=parent)
    return [type(p).to_dict(p) for p in client.list_user_licenses(request=request)]


def grant_license(user_id: str, license_config_path: Optional[str] = None) -> dict:
    """Grants or updates a user's license using a full license_config_path.

    Args:
        user_id: The unique identifier for the user (e.g., their email address).
        license_config_path: The full resource path of the subscription to use.
            (e.g., projects/123/locations/global/licenseConfigs/sub_id)

    Returns:
        A dictionary representing the result of the batch update operation or
        an error if no license_config_path is available.
    """
    if not license_config_path:
        return {
            "error": (
                "A license_config_path is required. Please use list_subscriptions "
                "to find an available subscription and pass its config_path."
            )
        }

    client = discoveryengine_v1.UserLicenseServiceClient()
    user_license_obj = discoveryengine_v1.UserLicense(
        user_principal=user_id, license_config=license_config_path
    )
    inline_source = discoveryengine_v1.BatchUpdateUserLicensesRequest.InlineSource(
        user_licenses=[user_license_obj]
    )

    parent = client.user_store_path(
        project=PROJECT_ID, location=LOCATION, user_store=USER_STORE_ID
    )

    request = discoveryengine_v1.BatchUpdateUserLicensesRequest(
        inline_source=inline_source,
        delete_unassigned_user_licenses=False,
        parent=parent,
    )
    operation = client.batch_update_user_licenses(request=request)
    response = operation.result()
    return type(response).to_dict(response)

def revoke_license(user_id: str, license_config_path: Optional[str] = None) -> dict:
    """Revokes a license from a specific user.

    Args:
        user_id: The unique identifier for the user whose license to revoke.
        license_config_path: The full resource path of the subscription associated
            with the license.

    Returns:
        A dictionary representing the result of the batch update operation.
    """
    if not license_config_path:
        return {
            "error": (
                "A license_config_path is required. Please use list_subscriptions "
                "to find the user's subscription and pass its config_path."
            )
        }

    client = discoveryengine_v1.UserLicenseServiceClient()
    user_license_obj = discoveryengine_v1.UserLicense(
        user_principal=user_id
    )
    inline_source = discoveryengine_v1.BatchUpdateUserLicensesRequest.InlineSource(
        user_licenses=[user_license_obj]
    )

    parent = client.user_store_path(
        project=PROJECT_ID, location=LOCATION, user_store=USER_STORE_ID
    )

    request = discoveryengine_v1.BatchUpdateUserLicensesRequest(
        inline_source=inline_source,
        delete_unassigned_user_licenses=True,
        parent=parent,
    )
    operation = client.batch_update_user_licenses(request=request)
    response = operation.result()
    return type(response).to_dict(response)


def release_stale_licenses(stale_after_days: int) -> dict:
    """Identifies and revokes licenses that have not been used recently.

    This tool finds users who have not logged in for a specified number of
    days and revokes their licenses to free up capacity.

    Args:
        stale_after_days: The number of days of inactivity after which a
                          license is considered stale and should be revoked.
                          Set to -1 to revoke licenses for users who have
                          never logged in.

    Returns:
        A dictionary summarizing the actions taken, including a list of users
        whose licenses were revoked.
    """
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(days=stale_after_days)
    revoked_users = []
    errors = []

    try:
        all_licenses = list_licenses()
    except Exception as e:
        return {"error": f"Failed to retrieve license list: {e}"}

    for license_info in all_licenses:
        user_id = license_info.get("user_principal")
        last_login_str = license_info.get("last_login_time")
        license_config = license_info.get("license_config")

        if not user_id or not license_config:
            errors.append(f"Skipping license with missing user_id or config: {license_info}")
            continue

        # Handle "Never Logged In" case (stale_after_days == -1)
        if stale_after_days == -1:
            if not last_login_str:
                logger.info(f"Found user {user_id} who has never logged in. Revoking...")
                try:
                    revoke_license(user_id=user_id, license_config_path=license_config)
                    revoked_users.append(user_id)
                except Exception as e:
                    errors.append(f"Failed to revoke license for '{user_id}': {e}")
            continue

        # Handle "Stale" case (stale_after_days > 0)
        if not last_login_str:
            # If checking for staleness, skip users who have never logged in (or handle differently if desired)
            continue

        try:
            last_login_time = parse_datetime(last_login_str)
        except (ValueError, TypeError):
            errors.append(
                f"Skipping user '{user_id}' due to invalid last_login_time: "
                f"'{last_login_str}'"
            )
            continue

        if last_login_time < stale_threshold:
            logger.info(
                f"Found stale license for user {user_id} (last login: "
                f"{last_login_time.strftime('%Y-%m-%d')}). Revoking..."
            )
            try:
                revoke_license(user_id=user_id, license_config_path=license_config)
                revoked_users.append(user_id)
            except Exception as e:
                errors.append(f"Failed to revoke license for '{user_id}': {e}")

    if not revoked_users and not errors:
        return {"status": "No stale licenses found.", "revoked_count": 0}

    return {
        "status": f"Completed license reclamation.",
        "revoked_count": len(revoked_users),
        "revoked_users": revoked_users,
        "errors": errors,
    }


def list_subscriptions() -> dict:
    """Lists all available subscriptions and their usage stats.

    Returns:
        A dictionary containing a list of subscriptions, or an error
        message if the request fails.
    """

    ## TODO: RESTful approach is temporarily approach due to google-cloud-discoveryengine and google-adk version conflicts
    ## It should be migrate back to function implementation after that

    session = _create_authed_session()
    if not session:
        return {"error": "Unable to obtain default credential for API calls."}

    headers = {"X-Goog-User-Project": PROJECT_ID}
    url = (
        f"{BASE_API_URL}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/"
        f"userStores/{USER_STORE_ID}/licenseConfigsUsageStats"
    )
    subscriptions_data = []

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if "licenseConfigUsageStats" not in data or not data["licenseConfigUsageStats"]:
            logger.info("  No subscriptions usage stats found.")
            return {"subscriptions": []}

        for stats in data["licenseConfigUsageStats"]:
            full_name = stats.get("licenseConfig")
            if not full_name:
                continue

            subscription_details = _get_subscription_details(session, full_name)
            if not subscription_details:
                # Log or handle the case where details for a specific
                # config could not be fetched.
                logger.warning(f"Could not fetch details for {full_name}. Skipping.")
                continue

            subscriptions_data.append({
                "display_name": full_name.split('/')[-1],
                "config_path": full_name,
                "used_count": int(stats.get("usedLicenseCount", "0")),
                "total_count": int(subscription_details.get("licenseCount", "-1")),
                "status": subscription_details.get("state", "Unknown"),
                "start_date": subscription_details.get("startDate", "N/A"),
                "end_date": subscription_details.get("endDate", "N/A"),
            })

        return {"subscriptions": subscriptions_data}

    except requests.exceptions.RequestException as e:
        error_info = {"error": f"Error calling REST API: {e}"}
        if e.response is not None:
            error_info["status_code"] = e.response.status_code
            error_info["response_content"] = e.response.text
        return error_info
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


# --- Agent Definition ---

root_agent = Agent(
    model="gemini-3-pro-preview",
    name="gemini_license_agent",
    description="Manages Gemini Enterprise / NotebookLM Enterprise licenses.",
    instruction="""
    You are the official License Administrator for the Gemini Enterprise ecosystems. 
    Your mission is to manage enterprise licenses with precision, clarity, and a focus on user safety.

**Your Operating Protocol:**

*   **Granting a License:**
    *   To grant a license, you must first get a list of available subscriptions
        by calling the `list_subscriptions` tool.
    *   Present the `display_name` of each subscription to the user.
    *   Once the user chooses a subscription, you must pass the corresponding
        `config_path` from the chosen subscription to the `grant_license` tool 
        via the `license_config_path` parameter.
    *   Intelligently guide the user to choose a valid option – one that is `ACTIVE` and has available seats.
    *   Never grant a license without first confirming availability through usage stats.

*   **Reclaiming Stale Licenses:**
    *   You can automatically reclaim licenses from inactive users by using the
        `release_stale_licenses` tool.
    *   This tool requires you to specify the number of days of inactivity that
        define a "stale" license. For example, using `90` would target users
        who haven't logged in for 90 days or more.

*   **User Safety:**
    *   Granting and revoking are critical operations. Always confirm the user's 
        intent with a clear confirmation prompt before proceeding.

*   **Data Presentation:**
    *   All your reports must be professional. Use padded, well-formatted tables for easy reading.
    *   For non-CLI users, use HTML-friendly format such as markdown to visualized the results such as table.
    *   Dates and times must follow the `YYYY-MM-DD HH:MM:SS` standard.
    *   When listing user licenses, make the `License Assignment State` easy to understand and always include 
        the User, State, Creation Time, and Last Login.
    """,
    tools=[
        list_licenses,
        grant_license,
        revoke_license,
        list_subscriptions,
        release_stale_licenses,
    ],
)
