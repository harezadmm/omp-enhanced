# GitHub Actions Workflows

## `deploy.yml` - Automated GitHub Pages Deployment

This workflow automatically builds and deploys the project to GitHub Pages whenever changes are pushed to the `main` or `master` branch.

### What it does:

1. **Build Stage:**
   - Checks out the repository
   - Sets up Node.js (v24) with npm cache enabled
   - Installs dependencies with `npm ci`
   - Runs test suite with `npm run test:all`
   - Runs `npm run build` which:
     - Copies static files to `dist/` (`copy-static.js`)
     - Builds transformer index (`build-index.js`)
     - Bundles all transformers to `dist/js/bundles/` (`build-transforms.js`)
     - Generates emoji data to `dist/js/data/` (`build-emoji-data.js`)
     - Injects tool scripts (`inject-tool-scripts.js`)
     - Injects tool templates into `dist/index.html` (`inject-tool-templates.js`)
   - Verifies critical build files exist in `dist/`
   - Uploads only the `dist/` folder as a Pages artifact (7-day retention)

2. **Deploy Stage:**
   - Deploys the `dist/` artifact to GitHub Pages
   - Makes the site available at your GitHub Pages URL

### Manual Deployment

You can also trigger a deployment manually from the GitHub Actions tab by selecting "Build and Deploy to GitHub Pages" and clicking "Run workflow".

### Required GitHub Settings

For this workflow to function, ensure GitHub Pages is configured in your repository settings:

1. Go to **Settings** → **Pages**
2. Under **Build and deployment**:
   - Source: **GitHub Actions**
3. Save the settings

The site will be available at: `https://<username>.github.io/<repository-name>/`

### Troubleshooting

- **Build fails**: Check the Actions tab for error logs
- **Tests fail**: Run `npm run test:all` locally to debug issues
- **Missing templates**: Ensure all templates exist in `templates/` directory
- **Test locally first**: Run `npm run build` before pushing to catch errors early
- **Verify build output**: Check that `dist/index.html` and other files exist in `dist/` folder after build
- **Build timeout**: Build has a 10-minute timeout; if it exceeds this, check for infinite loops or large file processing

### Workflow Triggers

- **Push**: Automatically runs on push to `main` or `master`
- **Workflow Dispatch**: Can be manually triggered from the Actions tab

