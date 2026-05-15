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
                (f.endsWith('.exe') || f.endsWith('latest.yml')) && 
                !f.includes('blockmap') &&
                (f.includes(version) || f.includes(targetVersion) || f === 'latest.yml')
            );
            
            if (artifacts.length === 0) {
                console.error(`❌ Could not find artifacts for version ${targetVersion} in dist/`);
                console.log('Available files:', distFiles.filter(f => f.endsWith('.exe')));
                process.exit(1);
            }

            const filesToUpload = artifacts.map(f => `dist/"${f}"`).join(' ');
            console.log(`Uploading artifacts: ${artifacts.join(', ')}...`);
            
            // Get current branch name
            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
            
            console.log('Pushing code changes (non-fatal)...');
            try {
                execSync(`git add . && git commit -m "chore: release ${targetVersion}"`, { stdio: 'ignore' });
            } catch(e) {}
            
            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit' });
            } catch (e) {
                console.warn('⚠️ Git push failed, but continuing to GitHub Release...');
            }

            console.log('Checking for existing release...');
            try {
                const existing = execSync(`gh release view ${targetVersion}`).toString();
                if (existing) {
                    const del = await new Promise(resolve => rl.question(`⚠️ Release ${targetVersion} already exists. Overwrite? (y/n): `, resolve));
                    if (del.toLowerCase() === 'y') {
                        console.log('Deleting old release and tag...');
                        execSync(`gh release delete ${targetVersion} --yes`, { stdio: 'inherit' });
                        execSync(`git tag -d ${targetVersion}`, { stdio: 'ignore' });
                        execSync(`git push origin :refs/tags/${targetVersion}`, { stdio: 'ignore' });
                    } else {
                        console.log('Aborted to prevent conflict.');
                        process.exit(0);
                    }
                }
            } catch (e) {}

            execSync(`gh release create ${targetVersion} ${filesToUpload} --title "v${targetVersion}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
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
