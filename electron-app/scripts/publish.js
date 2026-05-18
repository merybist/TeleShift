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

    // Ensure version uses dots only (YYYY.MM.DD.Attempt)
    let targetVersion = version.replace(/-/g, '.');

    const publishAnswer = await new Promise(resolve => rl.question(`\n📦 Push version ${targetVersion} to GitHub Releases? (y/n): `, resolve));
    
    if (publishAnswer.toLowerCase() === 'y') {
        console.log('📤 Publishing to GitHub...');
        
        const releaseNotes = `
## TeleShift Stable Release v${targetVersion}

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
                (f.includes(targetVersion) || f.includes(targetVersion.replace(/\./g, '-')))
            );
            
            if (artifacts.length === 0) {
                console.error(`❌ Could not find .exe artifact for version ${targetVersion} in dist/`);
                console.log('Available files:', distFiles.filter(f => f.endsWith('.exe')));
                process.exit(1);
            }

            const exeFile = `dist/"${artifacts[0]}"`;
            console.log(`Uploading ${exeFile}...`);
            
            // Get current branch name
            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
            
            console.log('Pushing code changes (non-fatal)...');
            try {
                execSync(`git add package.json && git commit -m "chore: release ${targetVersion}"`, { stdio: 'ignore' });
            } catch(e) {}
            
            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit' });
            } catch (e) {
                console.warn('⚠️ Git push failed, but continuing to GitHub Release...');
            }

            execSync(`gh release create ${targetVersion} ${exeFile} --title "v${targetVersion}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
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
