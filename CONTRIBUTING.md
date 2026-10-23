# Contributing to Dropen3

Dropen3 is research software. All development discussion, issue titles, pull requests, documentation, code identifiers, comments and user-facing text should be in **English**.

## Joining the project

The repository owner can invite a collaborator in GitHub **Repository > Settings > Collaborators and teams** (or **Collaborators**, depending on the repository type) > **Add people**. Enter the researcher's GitHub username and send the invitation. The researcher must accept it. This requires appropriate repository administration permission. For an organization repository, use the organization's access-management controls and the least privilege necessary.

Never share passwords, personal access tokens, or account credentials. Contributors should use their own GitHub accounts.

## Development workflow

1. Read `README.md`, `docs/LINUX.md` (Linux) or the Windows setup instructions (Windows), and `docs/VALIDATION.md`.
2. Clone the repo and create a feature branch from the team's agreed base branch: `git switch -c feature/short-description`.
3. Install the project in a local venv with `pip install -e '.[test]'` and run `python -m pytest -q`.
4. Make a small, reviewable change. Avoid mixing scientific numerical changes with GUI refactoring.
5. Include regression tests for changed algorithms and document measurement definitions, units, calibration assumptions and known limitations.
6. Push the feature branch and open a Pull Request. Request review by a scientific author for any algorithm, threshold, angle convention or measurement change.
7. Merge only after review and applicable tests; for research changes, record the reference dataset or validation evidence.

## Scientific quality rules

- Preserve raw experimental input and provenance. Do not commit confidential datasets or unlicensed third-party material.
- Keep side-view projected silhouette width separate from substrate contact width and distinguish acquired FPS from playback FPS.
- Record parameters and units when modifying the processing pipeline.
- Do not describe test coverage as experimental validation. Verify reference images/videos and retain representative datasets when permitted.
- Document reproducibility constraints, platform versions and video-decoder issues.

The software license and external release process must be agreed by the maintainers before redistributing the software under a particular open-source license.
