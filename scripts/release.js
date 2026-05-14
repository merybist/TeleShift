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

    // Update package.json
    pkg.version = newVersion;
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2));
    console.log('✅ package.json updated.');

    // 2. Build
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
## TeleShift Stable Release v${newVersion}

### 🔄 What's New:
*   **Real-time App Status:** Now with ✅ indicators for running apps in the launcher.
*   **Settings Fix:** All buttons in the Telegram bot are now fully functional.
*   **macOS Stability:** Native shutdown/reboot/lock commands for Mac users.
*   **Performance:** Improved uptime precision and telemetry reporting.

### 🛠 Technical:
*   Updated system-information engine.
*   Enhanced IPC communication security.
*   New HTML-based message parsing in Telegram bot.
        `.trim();

        fs.writeFileSync('release_notes.md', releaseNotes);

        try {
            // Adjust path if there is a space in the name (electron-builder default)
            const distFiles = fs.readdirSync(path.join(__dirname, '../dist'));
            const versionSafe = newVersion.replace(/\./g, '\\.');
            const artifacts = distFiles.filter(f => 
                f.endsWith('.exe') && 
                !f.includes('blockmap') &&
                (f.includes(newVersion) || f.includes(newVersion.replace(/\./g, '-')))
            );
            
            // Fallback: search for just the version numbers
            if (artifacts.length === 0) {
                const versionParts = newVersion.split('.');
                const majorMinor = versionParts.slice(0, 2).join('.');
                const match = distFiles.find(f => f.endsWith('.exe') && f.includes(majorMinor) && !f.includes('blockmap'));
                if (match) artifacts.push(match);
            }
            
            if (artifacts.length === 0) {
                console.error('❌ Could not find .exe artifact in dist/');
                console.log('Available files:', distFiles.filter(f => f.endsWith('.exe')));
                process.exit(1);
            }

            const exeFile = `dist/"${artifacts[0]}"`;
            
            console.log(`Pushing tag v${newVersion} and uploading ${exeFile}...`);
            
            // Get current branch name
            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
            
            console.log('Pushing code changes (non-fatal)...');
            try {
                execSync(`git add . && git commit -m "chore: release ${newVersion}"`, { stdio: 'ignore' });
            } catch(e) {}

            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit' });
            } catch (e) {
                console.warn('⚠️ Git push failed, but continuing to GitHub Release...');
            }

            execSync(`gh release create ${newVersion} ${exeFile} --title "v${newVersion}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
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
