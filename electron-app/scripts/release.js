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

    // 1. Fetch latest tags from remote to be sure
    try {
        console.log('Fetching tags from remote...');
        execSync('git fetch --tags', { stdio: 'ignore' });
    } catch (e) {}

    // 1. Calculate new version based on today's date and existing tags
    const now = new Date();
    const todayStr = `${now.getFullYear()}.${now.getMonth() + 1}.${now.getDate()}`;
    
    let latestAttempt = 0;
    try {
        const tags = execSync('git tag -l').toString().split('\n');
        tags.forEach(tag => {
            if (tag.startsWith(todayStr)) {
                const parts = tag.split('.');
                const attempt = parseInt(parts[parts.length - 1]);
                if (!isNaN(attempt) && attempt > latestAttempt) {
                    latestAttempt = attempt;
                }
            }
        });
    } catch (e) {
        console.warn('⚠️ Could not fetch tags, starting from 0');
    }

    const nextAttempt = latestAttempt + 1;
    let newVersion = `${todayStr}.${nextAttempt}`;

    const packagePath = path.join(__dirname, '../package.json');
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const oldVersion = pkg.version;

    console.log(`Current version: ${oldVersion}`);
    console.log(`Suggested version: ${newVersion}`);
    
    const customVersion = await new Promise(resolve => rl.question(`Enter version to build (default: ${newVersion}): `, resolve));
    if (customVersion) newVersion = customVersion;

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
        let buildCmd = 'npm run build && electron-builder --win';
        
        // Pass certificate if env vars are present
        if (process.env.WIN_CERT_PATH && process.env.WIN_CERT_PASSWORD) {
            console.log('🛡️ Code signing enabled via environment variables.');
            // We use -c.win.certificateFile to override config
            buildCmd += ` -c.win.certificateFile="${process.env.WIN_CERT_PATH}" -c.win.certificatePassword="${process.env.WIN_CERT_PASSWORD}"`;
        }

        execSync(buildCmd, { stdio: 'inherit' });
    } catch (e) {
        console.error('❌ Build failed.');
        process.exit(1);
    }

    // 3. GitHub Release
    const publishAnswer = await new Promise(resolve => rl.question('\n📦 Build complete. Push to GitHub Releases? (y/n): ', resolve));
    
    if (publishAnswer.toLowerCase() === 'y') {
        console.log('📤 Publishing to GitHub...');
        
        // 3. Generate dynamic Release Notes from Git commits
        let releaseNotes = `## TeleShift Stable Release v${versionForTag}\n\n### 🔄 Що нового:\n`;
        try {
            const latestTag = execSync('git describe --tags --abbrev=0').toString().trim();
            const commits = execSync(`git log ${latestTag}..HEAD --oneline`).toString().split('\n');
            const cleanCommits = commits
                .filter(c => c.trim().length > 0)
                .map(c => `* ${c.substring(c.indexOf(' ') + 1)}`)
                .join('\n');
            
            if (cleanCommits) {
                releaseNotes += cleanCommits;
            } else {
                releaseNotes += '* Технічні виправлення та покращення стабільності.';
            }
        } catch (e) {
            releaseNotes += '* Перший публічний реліз або не вдалося отримати список змін.';
        }

        fs.writeFileSync('release_notes.md', releaseNotes);

        try {
            const distFiles = fs.readdirSync(path.join(__dirname, '../dist'));
            const artifacts = distFiles.filter(f => 
                (f.endsWith('.exe') || f.endsWith('latest.yml')) && 
                !f.includes('blockmap') &&
                (f.includes(versionForPkg) || f.includes(versionForTag) || f === 'latest.yml')
            );
            
            if (artifacts.length === 0) {
                console.error(`❌ No artifacts found in dist/`);
                process.exit(1);
            }

            const filesToUpload = artifacts.map(f => `dist/"${f}"`).join(' ');
            
            console.log(`Pushing tag ${versionForTag} and uploading artifacts: ${artifacts.join(', ')}...`);
            
            const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
            
            console.log('Syncing with remote (pull --rebase)...');
            try {
                // Stash local changes to allow rebase
                execSync('git stash', { stdio: 'ignore' });
                execSync(`git pull origin ${branch} --rebase`, { stdio: 'inherit' });
                execSync('git stash pop', { stdio: 'ignore' });
            } catch(e) {
                console.warn('⚠️ Pull/Stash failed, check for conflicts.');
            }

            console.log('Pushing code changes...');
            try {
                execSync(`git add . && git commit -m "chore: release ${versionForTag}"`, { stdio: 'ignore' });
            } catch(e) {}

            try {
                execSync(`git push origin ${branch}`, { stdio: 'inherit' });
            } catch (e) {
                console.error('❌ Git push failed. Please push manually.');
            }

            console.log('Checking for existing release...');
            try {
                const existing = execSync(`gh release view ${versionForTag}`).toString();
                if (existing) {
                    const del = await new Promise(resolve => rl.question(`⚠️ Release ${versionForTag} already exists. Overwrite? (y/n): `, resolve));
                    if (del.toLowerCase() === 'y') {
                        console.log('Deleting old release and tag...');
                        execSync(`gh release delete ${versionForTag} --yes`, { stdio: 'inherit' });
                        execSync(`git tag -d ${versionForTag}`, { stdio: 'ignore' });
                        execSync(`git push origin :refs/tags/${versionForTag}`, { stdio: 'ignore' });
                    } else {
                        console.log('Aborted to prevent conflict.');
                        process.exit(0);
                    }
                }
            } catch (e) {
                // Release doesn't exist, fine
            }

            execSync(`gh release create ${versionForTag} ${filesToUpload} --title "v${versionForTag}" --notes-file release_notes.md`, { stdio: 'inherit' });
            
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
