const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

async function run() {
    console.log('📤 TeleShift Fast Publisher starting...');

    const packagePath = path.join(__dirname, '../package.json');
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const version = pkg.version;

    console.log(`Current version: ${version}`);

    const publishAnswer = await new Promise(resolve => rl.question(`\n📦 Push version v${version} to GitHub Releases? (y/n): `, resolve));
    
    if (publishAnswer.toLowerCase() === 'y') {
        console.log('📤 Publishing to GitHub...');
        
        const releaseNotes = `
## TeleShift Stable Release v${version}

### 🔄 What's New:
*   **Real-time App Status:** Now with ✅ indicators for running apps in the launcher.
*   **Settings Fix:** All buttons in the Telegram bot are now fully functional.
*   **macOS Stability:** Native shutdown/reboot/lock commands for Mac users.
*   **Performance:** Improved uptime precision and telemetry reporting.
        `.trim();

        fs.writeFileSync('release_notes.md', releaseNotes);

        try {
            const distFiles = fs.readdirSync(path.join(__dirname, '../dist'));
            const artifacts = distFiles.filter(f => 
                f.endsWith('.exe') && 
                !f.includes('blockmap') &&
                (f.includes(version) || f.includes(version.replace(/\./g, '-')))
            );

            // Fallback for 4-part versions
            if (artifacts.length === 0) {
                const versionParts = version.split('.');
                const majorMinor = versionParts.slice(0, 2).join('.');
                const match = distFiles.find(f => f.endsWith('.exe') && f.includes(majorMinor) && !f.includes('blockmap'));
                if (match) artifacts.push(match);
            }
            
            if (artifacts.length === 0) {
                console.error('❌ Could not find .exe artifact in dist/. Did you build it?');
                process.exit(1);
            }

            const exeFile = `dist/"${artifacts[0]}"`;
            console.log(`Uploading ${exeFile}...`);
            
            execSync(`git add . && git commit -m "chore: release v${version}" && git push`, { stdio: 'inherit' });
            execSync(`gh release create v${version} ${exeFile} --title "TeleShift Release v${version}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
            console.log('\n✨ SUCCESS! Version pushed to GitHub.');
        } catch (e) {
            console.error('❌ Publishing failed.');
            console.error(e.message);
        } finally {
            if (fs.existsSync('release_notes.md')) fs.unlinkSync('release_notes.md');
        }
    }

    rl.close();
}

run();
