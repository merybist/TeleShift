const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

async function run() {
    console.log('🚀 TeleShift Deployment Manager starting...');

    // 1. Calculate new version (YYYY.MM.DD.Attempt)
    const packagePath = path.join(__dirname, '../package.json');
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const oldVersion = pkg.version;
    
    const now = new Date();
    const todayStr = `${now.getFullYear()}.${now.getMonth() + 1}.${now.getDate()}`;
    
    let newVersion;
    if (oldVersion.startsWith(todayStr)) {
        // Same day, increment attempt (handle both . and - for transition)
        const parts = oldVersion.split(/[.-]/);
        const attempt = parseInt(parts[parts.length - 1] || '0') + 1;
        newVersion = `${todayStr}.${attempt}`;
    } else {
        // New day, start from .1
        newVersion = `${todayStr}.1`;
    }

    console.log(`Current version: ${oldVersion}`);
    console.log(`Target version:  ${newVersion}`);

    const answer = await new Promise(resolve => rl.question('Confirm version bump and start build? (y/n): ', resolve));
    
    if (answer.toLowerCase() !== 'y') {
        console.log('Aborted.');
        process.exit(0);
    }

    // Update package.json (with hyphen for the EXE filename)
    const versionForPkg = newVersion.replace(/\.(\d+)$/, '-$1');
    const versionForTag = newVersion; // Dots only for GitHub
    
    pkg.version = versionForPkg;
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2));
    console.log(`✅ package.json updated to ${versionForPkg} (for filename).`);

    // 2. Build
    console.log('🧹 Cleaning dist folder...');
    if (fs.existsSync(path.join(__dirname, '../dist'))) {
        fs.rmSync(path.join(__dirname, '../dist'), { recursive: true, force: true });
    }

    console.log('🔨 Building for Windows...');
    try {
        execSync('npm run build:win', { stdio: 'inherit' });
    } catch (e) {
        console.error('❌ Build failed.');
        process.exit(1);
    }

    // 3. GitHub Release
    const publishAnswer = await new Promise(resolve => rl.question('\n📦 Build complete. Push to GitHub Releases? (y/n): ', resolve));
    
    if (publishAnswer.toLowerCase() === 'y') {
        console.log('📤 Publishing to GitHub...');
        
        const releaseNotes = `
## TeleShift Stable Release v${versionForTag}

### 🔄 What's New:
*   **💓 Heartbeat System:** Real-time online status tracking with precise accuracy.
*   **🚀 Auto-Start:** Added a toggle in settings to launch the app on system startup.
*   **✅ Process Indicators:** Improved detection of running apps (e.g., Majestic Launcher).
*   **💬 Screen Messages:** Send text messages directly to the PC screen via the bot.
        `.trim();

        fs.writeFileSync('release_notes.md', releaseNotes);

        try {
            const distFiles = fs.readdirSync(path.join(__dirname, '../dist'));
            const artifacts = distFiles.filter(f => 
                f.endsWith('.exe') && 
                !f.includes('blockmap') &&
                (f.includes(versionForPkg) || f.includes(versionForTag))
            );
            
            if (artifacts.length === 0) {
                console.error(`❌ No .exe artifacts found in dist/`);
                process.exit(1);
            }

            const exeFile = `dist/"${artifacts[0]}"`;
            
            console.log(`Pushing tag ${versionForTag} and uploading ${exeFile}...`);
            
            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
            
            console.log('Syncing with remote (pull --rebase)...');
            try {
                execSync(`git pull origin ${branch} --rebase`, { stdio: 'inherit' });
            } catch(e) {
                console.warn('⚠️ Pull failed, check for conflicts.');
            }

            console.log('Pushing code changes...');
            try {
                execSync(`git add package.json && git commit -m "chore: release ${versionForTag}"`, { stdio: 'ignore' });
            } catch(e) {}

            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit' });
            } catch (e) {
                console.error('❌ Git push failed. Please push manually.');
            }

            execSync(`gh release create ${versionForTag} ${exeFile} --title "v${versionForTag}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
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
