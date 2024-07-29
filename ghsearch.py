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

def create_branch(repo, branch_name):
    try:
        source = repo.get_branch("main")
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
        return True
    except GithubException as e:
        print(f"Error creating branch in {repo.name}: {e}")
        return False

def update_workflow_file(repo, file_path, old_content, new_content, branch_name):
    try:
        file = repo.get_contents(file_path, ref=branch_name)
        file_content = file.decoded_content.decode()
        if re.search(old_content, file_content, re.MULTILINE | re.DOTALL):
            updated_content = re.sub(old_content, new_content, file_content, flags=re.MULTILINE | re.DOTALL)
            repo.update_file(
                file_path,
                "Update build-and-push-image job to use OIDC",
                updated_content,
                file.sha,
                branch=branch_name
            )
            return True
    except GithubException as e:
        print(f"Error updating file {file_path} in {repo.name}: {e}")
    return False

def create_pull_request(repo, branch_name, base="main"):
    try:
        pr = repo.create_pull(
            title="Update build-and-push-image job to use OIDC",
            body="This PR updates the workflow to use OIDC for AWS authentication.",
            head=branch_name,
            base=base
        )
        print(f"Created PR: {pr.html_url}")
    except GithubException as e:
        print(f"Error creating pull request for {repo.name}: {e}")

def update_repository(repo, old_content_pattern, new_content):
    branch_name = f"update-workflow-oidc-{repo.name}"
    if create_branch(repo, branch_name):
        updated = False
        try:
            contents = repo.get_contents(".github/workflows", ref=branch_name)
            for content_file in contents:
                if content_file.name.endswith(('.yml', '.yaml')):
                    if update_workflow_file(repo, content_file.path, old_content_pattern, new_content, branch_name):
                        updated = True
                        print(f"Updated {repo.name}/{content_file.path}")
            
            if updated:
                create_pull_request(repo, branch_name)
            else:
                print(f"No changes needed in {repo.name}")
        except GithubException as e:
            print(f"Error processing {repo.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Update GitHub workflow files")
    parser.add_argument("--org", required=True, help="GitHub organization name")
    parser.add_argument("--repo", help="Specific repository to update (optional)")
    args = parser.parse_args()

    g = get_github_client()
    org = get_organization(g, args.org)
    if not org:
        return

    old_content_pattern = r"""build-and-push-image:\s*
    uses:\s*LearnWithHomer/infrastructure-public/\.github/workflows/build-and-push-image-to-ecr\.yml@main\s*
    secrets:\s*
      ecr_repo:\s*\$\{\{\s*secrets\.ECR_REPOSITORY\s*\}\}\s*
      access_key_id:\s*\$\{\{\s*secrets\.CODESPARK_AWS_ACCESS_KEY_ID\s*\}\}\s*
      secret_access_key:\s*\$\{\{\s*secrets\.CODESPARK_AWS_SECRET_ACCESS_KEY\s*\}\}\s*
      aws_region:\s*\$\{\{\s*secrets\.CODESPARK_AWS_REGION\s*\}\}\s*
      gh_pkg_token:\s*\$\{\{\s*secrets\.GH_PKG_TOKEN\s*\}\}"""

    new_content = """build-and-push-image:
    uses: LearnWithHomer/infrastructure-public/.github/workflows/build-and-push-image-to-ecr.yml@workflows/ecr-oidc
    with:
      role_arn: arn:aws:iam::929871197119:role/gha-ecr-exec
    secrets:
      ecr_repo: ${{ secrets.ECR_REPOSITORY }}
      aws_region: ${{ secrets.CODESPARK_AWS_REGION }}
      gh_pkg_token: ${{ secrets.GH_PKG_TOKEN }}"""

    if args.repo:
        repo = org.get_repo(args.repo)
        update_repository(repo, old_content_pattern, new_content)
    else:
        for repo in org.get_repos():
            update_repository(repo, old_content_pattern, new_content)

    print("Update process completed.")

if __name__ == "__main__":
    main()