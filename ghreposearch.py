import os
import re
import argparse
from github import Github, GithubException

def get_github_client():
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    return Github(github_token)

def get_organization(g, org_name):
    try:
        return g.get_organization(org_name)
    except GithubException as e:
        print(f"Error accessing organization {org_name}: {e}")
        return None

def check_workflow_files(repo, old_content_pattern):
    matching_files = []
    try:
        contents = repo.get_contents(".github/workflows")
        for content_file in contents:
            if content_file.name.endswith(('.yml', '.yaml')):
                file_content = content_file.decoded_content.decode()
                if old_content_pattern.search(file_content):
                    matching_files.append(content_file.path)
    except GithubException as e:
        print(f"Error processing {repo.name}: {e}")
    return matching_files

def main():
    parser = argparse.ArgumentParser(description="List GitHub repositories with matching workflow content")
    parser.add_argument("--org", required=True, help="GitHub organization name")
    args = parser.parse_args()

    g = get_github_client()
    org = get_organization(g, args.org)
    if not org:
        return

    old_content_pattern = re.compile(r'LearnWithHomer/infrastructure-public/\.github/workflows/build-and-push-image-to-ecr\.yml@main')

    matching_repos = {}

    for repo in org.get_repos():
        matching_files = check_workflow_files(repo, old_content_pattern)
        if matching_files:
            matching_repos[repo.name] = matching_files

    print("\nRepositories with matching workflow content:")
    for repo_name, files in matching_repos.items():
        print(f"\n{repo_name}:")
        for file in files:
            print(f"  - {file}")

    print(f"\nTotal repositories found: {len(matching_repos)}")

if __name__ == "__main__":
    main()