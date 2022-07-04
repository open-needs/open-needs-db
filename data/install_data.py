import json
import rich_click as click

from rich import print
from rich.console import Console

import requests
import urllib.parse

from open_needs_server.config import settings


console = Console()


@click.command()
@click.argument("input", type=click.File("rb"))
@click.option("--server", default=settings.server.server, type=str)
@click.option("--port", default=settings.server.port, type=str)
def install(input, server, port):
    base_url = f"http://{server}:{port}"
    user_url = urllib.parse.urljoin(base_url, "auth/register")
    login_url = urllib.parse.urljoin(base_url, "auth/jwt/login")
    role_url = urllib.parse.urljoin(base_url, "api/roles")
    org_url = urllib.parse.urljoin(base_url, "api/organizations")
    project_url = urllib.parse.urljoin(base_url, "api/projects")
    needs_url = urllib.parse.urljoin(base_url, "api/needs")
    domains_url = urllib.parse.urljoin(base_url, "api/domains")

    data = json.load(input)

    console.rule(f"[bold red]Users")
    users = {}
    for index, user in enumerate(data["users"]):
        r = requests.post(user_url, json=user)
        print(
            f'{index}. {user["email"]}\t{r.status_code}: {r.text if r.status_code > 300 else ""}'
        )
        if r.status_code < 300:
            users[user["email"]] = r.json()

    console.rule(f"[bold red]Roles")
    for index, role in enumerate(data["roles"]):
        user_ids = []
        for user_email in role["users"]:
            user_ids.append(users[user_email]["id"])

        role_data = {"users": user_ids}
        url = f'{role_url}/{role["role"]}'
        r = requests.put(url, json=role_data)
        print(
            f'{index}. {role["role"]}\t {r.status_code}: {r.text if r.status_code != 200 else ""}'
        )

    console.rule(f"[bold red]Admin login")
    login_data = {
        "username": data["users"][0]["email"],
        "password": data["users"][0]["password"],
    }
    r = requests.post(login_url, data=login_data)
    if r.status_code > 300:
        print("Can not login")
        return
    token = r.json()["access_token"]
    auth_header = {
        "Authorization": f"Bearer {token}"
    }  # Always use this one from now on
    print(f"Login: {r.status_code} - Token: {token}")

    console.rule(f"[bold red]Organizations")
    for index, org in enumerate(data["organizations"]):
        r = requests.post(org_url, json=org, headers=auth_header)
        print(
            f'{index}. {org["title"]}\t {r.status_code}: {r.text if r.status_code != 200 else ""}'
        )

    console.rule(f"[bold red]Domains")
    for index, domain in enumerate(data["domains"]):
        r = requests.post(domains_url, json=domain, headers=auth_header)
        print(
            f'{index}. {domain["title"]}\t {r.status_code}: {r.text if r.status_code != 200 else ""}'
        )

    console.rule(f"[bold red]Projects")
    for index, project in enumerate(data["projects"]):
        r = requests.post(project_url, json=project, headers=auth_header)
        print(
            f'{index}. {project["title"]}\t {r.status_code}: {r.text if r.status_code != 200 else ""}'
        )

    console.rule(f"[bold red]Needs")
    for index, need in enumerate(data["needs"]):
        r = requests.post(needs_url, json=need, headers=auth_header)
        print(
            f'{index}. {need["title"]}\t {r.status_code}: {r.text if r.status_code != 200 else ""}'
        )


if __name__ == "__main__":
    install()
