# CI/CD Runner Notes

The GitLab pipeline validates the repository, but it still depends on an eligible GitLab runner.

If a job page says `This job does not have a trace` or `the job got stuck`, the job did not start. That is normally a runner configuration problem, not a Python, Docker Compose, or Ansible syntax failure.

Check the project runner settings in GitLab:

- at least one runner is online
- the runner is enabled for this project
- the runner accepts untagged jobs, or `.gitlab-ci.yml` uses the runner's required tag
- the runner is allowed to run jobs on protected branches if `main` is protected

Current automatic validation jobs:

- `python:syntax`
- `ansible:syntax`
- `compose:config`
- `k8s:yaml`
- `helm:template`
- `monitoring:syntax`

The `docker:image-build` job is manual because it requires Docker-in-Docker or an equivalent privileged Docker runner. If the university runner does not allow privileged Docker, validate the image build locally with:

```bash
docker compose build
docker compose config --quiet
```

If the GitLab runner requires a tag, add it near the top of `.gitlab-ci.yml`:

```yaml
default:
  tags:
    - your-runner-tag
```
