const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const os = require('os');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

async function run() {
    console.log('🚀 TeleShift Deployment Manager starting...');

    const platform = os.platform();
    const isMac = platform === 'darwin';
    const isWin = platform === 'win32';

    // 1. Calculate new version (YYYY.MM.DD.Attempt)
    const packagePath = path.join(__dirname, '../package.json');
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const oldVersion = pkg.version;

    const now = new Date();
    const todayStr = `${now.getFullYear()}.${now.getMonth() + 1}.${now.getDate()}`;

    let newVersion;
    if (oldVersion.startsWith(todayStr)) {
        const parts = oldVersion.split(/[.-]/);
        const attempt = parseInt(parts[parts.length - 1] || '0') + 1;
        newVersion = `${todayStr}.${attempt}`;
    } else {
        newVersion = `${todayStr}.1`;
    }

    console.log(`Current version: ${oldVersion}`);
    console.log(`Target version:  ${newVersion}`);
    console.log(`Platform:        ${isMac ? 'macOS' : isWin ? 'Windows' : platform}`);

    const answer = await new Promise(resolve => rl.question('Confirm version bump and start build? (y/n): ', resolve));

    if (answer.toLowerCase() !== 'y') {
        console.log('Aborted.');
        process.exit(0);
    }

    // Update package.json
    const versionForPkg = newVersion.replace(/\.(\d+)$/, '-$1');
    const versionForTag = newVersion;

    pkg.version = versionForPkg;
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2));
    console.log(`✅ package.json updated to ${versionForPkg}`);

    // 2. Build
    console.log('🧹 Cleaning dist folder...');
    if (fs.existsSync(path.join(__dirname, '../dist'))) {
        fs.rmSync(path.join(__dirname, '../dist'), { recursive: true, force: true });
    }

    const buildCmd = isMac ? 'npm run build:mac' : 'npm run build:win';
    console.log(`🔨 Building for ${isMac ? 'macOS' : 'Windows'}...`);
    try {
        execSync(buildCmd, { stdio: 'inherit', cwd: path.join(__dirname, '..') });
    } catch (e) {
        console.error('❌ Build failed.');
        process.exit(1);
    }

    // 3. GitHub Release
    const publishAnswer = await new Promise(resolve => rl.question('\n📦 Build complete. Push to GitHub Releases? (y/n): ', resolve));

    if (publishAnswer.toLowerCase() === 'y') {
        console.log('📤 Publishing to GitHub...');

        const releaseNotes = `
## TeleShift v${versionForTag}

### 🔄 What's New:
*   **🖥️ macOS LaunchAgent:** Auto-start now works without code signing.
*   **💓 Heartbeat System:** Real-time online status tracking.
*   **🚀 Auto-Start:** Launch the app on system startup.
*   **✅ Process Indicators:** Improved detection of running apps.
*   **💬 Screen Messages:** Send text messages directly to the PC screen.
        `.trim();

        fs.writeFileSync('release_notes.md', releaseNotes);

        try {
            const distPath = path.join(__dirname, '../dist');
            const distFiles = fs.readdirSync(distPath);

            let artifacts;
            if (isMac) {
                artifacts = distFiles.filter(f =>
                    f.endsWith('.dmg') && !f.includes('blockmap')
                );
            } else {
                artifacts = distFiles.filter(f =>
                    f.endsWith('.exe') &&
                    !f.includes('blockmap') &&
                    (f.includes(versionForPkg) || f.includes(versionForTag))
                );
            }

            if (artifacts.length === 0) {
                console.error(`❌ No artifacts found in dist/`);
                console.log('Files in dist:', distFiles.join(', '));
                process.exit(1);
            }

            const artifactFiles = artifacts.map(f => `"dist/${f}"`).join(' ');

            console.log(`Uploading: ${artifacts.join(', ')}`);

            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();

            console.log('Syncing with remote (pull --rebase)...');
            try {
                execSync(`git pull origin ${branch} --rebase`, { stdio: 'inherit', cwd: path.join(__dirname, '..') });
            } catch(e) {
                console.warn('⚠️ Pull failed, check for conflicts.');
            }

            console.log('Pushing code changes...');
            try {
                execSync(`git add package.json && git commit -m "chore: release ${versionForTag}"`, { stdio: 'ignore', cwd: path.join(__dirname, '..') });
            } catch(e) {}

            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit', cwd: path.join(__dirname, '..') });
            } catch (e) {
                console.error('❌ Git push failed. Please push manually.');
            }

            execSync(`gh release create ${versionForTag} ${artifactFiles} --title "v${versionForTag}" --notes-file release_notes.md`, { stdio: 'inherit', cwd: path.join(__dirname, '..') });

            console.log('\n✨ SUCCESS! Update is live and users will be notified.');
        } catch (e) {
            console.error('❌ GitHub publishing failed. Make sure you have "gh" CLI installed and logged in.');
            console.error(e.message);
        } finally {
            if (fs.existsSync('release_notes.md')) fs.unlinkSync('release_notes.md');
        }
    } else {
        console.log('Skipped publishing. Version in package.json was updated.');
    }

    rl.close();
}

run();
