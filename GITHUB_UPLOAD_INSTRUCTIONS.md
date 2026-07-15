# Uploading This Repository to GitHub

## Browser method

1. Sign into GitHub.
2. Click **New repository**.
3. Name it `AlphaVelocity`.
4. Select **Private**.
5. Do not add a README, `.gitignore`, or license on GitHub.
6. Create the repository.
7. Extract `AlphaVelocity_GitHub_Ready.zip`.
8. Open the extracted `AlphaVelocity` folder.
9. On the empty GitHub repository page, choose **uploading an existing file**.
10. Drag all files and folders from inside `AlphaVelocity` into the GitHub upload page.
11. Commit with the message:

   `Create integrated controlled Alpha Velocity 2.0 baseline`

## Git command-line method

Open Git Bash inside the extracted `AlphaVelocity` folder:

```bash
git init
git branch -M main
git add .
git commit -m "Create integrated controlled Alpha Velocity 2.0 baseline"
git remote add origin https://github.com/YOUR_USERNAME/AlphaVelocity.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## After upload

Open the repository's **Actions** tab. The `Alpha Velocity Tests` workflow should run
automatically. Do not treat a release as ready when the workflow is failing.
