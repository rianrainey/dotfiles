# Global Workflow Guidance

## Jira Review Workflow

When I say "review" followed by a Jira URL (e.g., `review https://goodrx-dev.atlassian.net/browse/SDRP-661`):

1. Use `acli` to transition the Jira ticket to "In Review"
2. Use `acli` to add me (Rian Rainey, `rian.rainey@goodrx.com`) as a collaborator on the ticket
3. Then proceed with the normal PR review workflow — look up the linked PR from the Jira ticket and perform the code review
