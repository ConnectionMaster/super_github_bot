import argparse
import os
import sys
import time
from typing import List

from github import Github
import jwt
import requests


def add_to_project(args: List[str]):
    owner, repo = args.repository.split('/')
    github_token = get_github_token(args.app_id, args.private_key, owner)

    gh = Github(github_token)

    organization = gh.get_organization(owner)

    # find project
    for project in organization.get_projects():
        if project.name == args.project:
            project_id = project.node_id
            break
    else:
        raise ValueError(f'Organization {owner} project {args.project} not found')

    if args.issue:
        # Setting project only supported on GraphQL API
        issue = organization.get_repo(repo).get_issue(args.issue)
        mutate_issue = """
        mutation($issueId:ID!, $projectId:ID!) {
          updateIssue(input:{id:$issueId, projectIds:[$projectId]}) {
            issue {
              id
            }
          }
        }
        """
        graphql_vars = {
            'issueId': issue.raw_data['node_id'],
            'projectId': project_id}
        run_graphql_query(github_token, mutate_issue, graphql_vars)
    elif args.pull_request:
        # Setting project only supported on GraphQL API
        pull_request = organization.get_repo(repo).get_pull(args.pull_request)
        mutate_pull_request = """
        mutation($pullRequestId:ID!, $projectId:ID!) {
          updatePullRequest(input:{pullRequestId:$pullRequestId, projectIds:[$projectId]}) {
            pullRequest {
              id
            }
          }
        }
        """
        graphql_vars = {
            'pullRequestId': pull_request.raw_data['node_id'],
            'projectId': project_id}
        run_graphql_query(github_token, mutate_pull_request, graphql_vars)


def get_github_token(app_id: int, private_key: str, owner: str) -> str:
    now = int(time.time())
    payload = dict(
        # issued at time
        iat=now,
        # JWT expiration time (10 minute maximum)
        exp=now + (10 * 60),
        # GitHub App's identifier
        iss=app_id
    )
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256').decode()

    # Find Installation
    headers = {
        'Authorization': f'Bearer {encoded_jwt}',
        'Accept': "application/vnd.github.machine-man-preview+json"
    }

    installations = requests.get("https://api.github.com/app/installations", headers=headers).json()
    for installation in installations:
        if installation['account']['login'] == owner:
            installation_id = installation['id']
            break
    else:
        raise ValueError('Organization not found in installations')

    access_tokens = requests.post(f"https://api.github.com/app/installations/{installation_id}/access_tokens", headers=headers).json()
    return access_tokens['token']


def run_graphql_query(token, query, variables=None):
    headers = {
        'Authorization': f'Bearer {token}',
    }
    payload = {'query': query}
    if variables is not None:
        payload['variables'] = variables
    request = requests.post('https://api.github.com/graphql', json=payload, headers=headers)
    request.raise_for_status()
    result = request.json()
    errors = result.get('errors')
    if errors:
        raise Exception(str(errors))

def parse_args(argv = None):
    argv = argv or sys.argv
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('add_to_project',))
    parser.add_argument('repository')
    parser.add_argument('project')
    parser.add_argument('--issue', type=int)
    parser.add_argument('--pull-request', type=int)

    args = parser.parse_args()

    args.app_id = int(os.environ['BOT_APP_ID'])
    args.private_key = os.environ['BOT_PRIVATE_KEY']

    return args


def main():
    args = parse_args()

    if args.command == 'add_to_project':
        add_to_project(args)
    else:
        assert False, f'unknown command {args.command}'


if __name__ == '__main__':
    main()
