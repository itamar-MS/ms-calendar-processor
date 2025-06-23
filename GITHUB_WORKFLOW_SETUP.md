# GitHub Workflow Setup Guide

This repository includes a GitHub workflow that automatically syncs calendar data with Base44 every 3 hours.

## Workflow Details

- **File**: `.github/workflows/calendar-sync.yml`
- **Schedule**: Runs every 3 hours (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC)
- **Manual Trigger**: Can be manually triggered via GitHub Actions UI
- **Command**: `python main.py --instructor-reports --current-month --handlers base44sync`

## Required GitHub Secrets

To enable the workflow, you need to add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add each of the following:

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 operations | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 operations | `...` |
| `AWS_DEFAULT_REGION` | AWS region for S3 bucket | `us-east-1` |
| `HUBSPOT_API_KEY` | HubSpot API key for contact updates | `...` |
| `BASE44_API_KEY` | Base44 API key for time tracking sync | `...` |
| `DATABASE_URL` | Database connection string | `postgresql://user:pass@host:port/db` |

### How to Enable Environment Variables

1. Edit `.github/workflows/calendar-sync.yml`
2. Uncomment the `env:` section in the "Run calendar sync" step
3. Remove the comment markers (`#`) from the environment variables you want to use

Example:
```yaml
- name: Run calendar sync
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_DEFAULT_REGION: ${{ secrets.AWS_DEFAULT_REGION }}
    HUBSPOT_API_KEY: ${{ secrets.HUBSPOT_API_KEY }}
    BASE44_API_KEY: ${{ secrets.BASE44_API_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: |
    python main.py --instructor-reports --current-month --handlers base44sync
```

## Monitoring

- **Logs**: Check the Actions tab in your GitHub repository to view workflow execution logs
- **Artifacts**: Output files are automatically uploaded as artifacts for 7 days
- **Manual Execution**: You can manually trigger the workflow from the Actions tab

## Troubleshooting

1. **Workflow fails**: Check the logs in the Actions tab for error details
2. **Missing secrets**: Ensure all required secrets are properly configured
3. **Permission issues**: Verify that your AWS credentials have the necessary permissions
4. **API rate limits**: Check if you're hitting rate limits with external APIs

## Security Notes

- Never commit sensitive credentials directly to the repository
- Use GitHub secrets for all sensitive information
- Regularly rotate your API keys and access credentials
- Consider using least-privilege IAM policies for AWS access 