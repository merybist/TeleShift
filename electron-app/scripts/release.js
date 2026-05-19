#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const DIST = path.join(__dirname, '../dist');

function getBuiltArtifacts() {
    if (!fs.existsSync(DIST)) return [];
    const files = fs.readdirSync(DIST);
    return files.filter(f =>
        (f.endsWith('.dmg') || f.endsWith('.exe')) && !f.includes('blockmap')
    );
}

function getMetadataFiles() {
    if (!fs.existsSync(DIST)) return [];
    const files = fs.readdirSync(DIST);
    return files.filter(f => f === 'latest-mac.yml' || f === 'latest.yml');
}

function getMetadataVersion(filename) {
    try {
        const content = fs.readFileSync(path.join(DIST, filename), 'utf-8');
        const match = content.match(/^version:\s*([^\s]+)/m);
        return match ? match[1].trim() : null;
    } catch {
        return null;
    }
}

function getReferencedFiles(metadataFilename) {
    try {
        const content = fs.readFileSync(path.join(DIST, metadataFilename), 'utf-8');
        const matches = [...content.matchAll(/url:\s*([^\s]+)/g)];
        return matches.map(m => m[1]);
    } catch {
        return [];
    }
}

function extractVersion(filename) {
    const match = filename.match(/(\d{4}\.\d{1,2}\.\d{1,2})[.-](\d+)/);
    if (!match) return null;
    return { pkg: `${match[1]}-${match[2]}`, tag: `${match[1]}.${match[2]}` };
}

async function selectArtifacts(artifacts) {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

    console.log('\n📦 Built artifacts:\n');
    artifacts.forEach((f, i) => {
        const size = (fs.statSync(path.join(DIST, f)).size / 1024 / 1024).toFixed(1);
        console.log(`  [${i + 1}] ${f}  (${size} MB)`);
    });

    const answer = await new Promise(resolve =>
        rl.question('\n→ Select (space-separated numbers, or "all" [default]): ', resolve)
    );
    rl.close();

    const choice = answer.trim() === '' ? 'all' : answer.trim().toLowerCase();
    if (choice === 'all') return artifacts;

    const indices = choice.split(/\s+/).map(n => parseInt(n) - 1);
    return indices.filter(i => i >= 0 && i < artifacts.length).map(i => artifacts[i]);
}

async function run() {
    console.log('🚀 TSrelease\n');

    const artifacts = getBuiltArtifacts();
    if (artifacts.length === 0) {
        console.log('❌ No built artifacts in dist/. Run build:mac or build:win first.');
        process.exit(1);
    }

    const selected = await selectArtifacts(artifacts);
    if (selected.length === 0) {
        console.log('Nothing selected. Aborted.');
        process.exit(0);
    }

    const version = extractVersion(selected[0]);
    if (!version) {
        console.error('❌ Could not extract version from filename:', selected[0]);
        process.exit(1);
    }

    console.log(`\n📋 Release v${version.tag}`);
    console.log(`   Artifacts: ${selected.join(', ')}`);

    // Filter metadata files to only include those matching the release version
    const metadata = getMetadataFiles().filter(f => {
        const v = getMetadataVersion(f);
        if (v === version.pkg) {
            return true;
        } else {
            console.log(`   ⚠️  Skipping ${f} (version ${v} does not match release version ${version.pkg})`);
            return false;
        }
    });

    if (metadata.length > 0) {
        console.log(`   Metadata:  ${metadata.join(', ')} (for auto-update)`);
        
        // Ensure all files referenced in the yml metadata files are also selected for upload
        for (const metaFile of metadata) {
            const refFiles = getReferencedFiles(metaFile);
            for (const refFile of refFiles) {
                if (!selected.includes(refFile)) {
                    console.error(`\n❌ Error: ${metaFile} references "${refFile}", but it is not selected for upload!`);
                    console.error(`   To avoid a broken auto-updater release, you must upload all referenced files.`);
                    console.error(`   Please run the release script again and select all files or choose 'all'.`);
                    process.exit(1);
                }
            }
        }
    } else {
        console.log('   ⚠️  No metadata files (latest-mac.yml / latest.yml) match this version — auto-update won\'t work!');
    }

    // Git push
    const branch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: path.join(__dirname, '..') }).toString().trim();
    console.log(`\n📤 Pushing to ${branch}...`);

    try {
        execSync(`git add package.json && git commit -m "release: v${version.tag}" --allow-empty`, {
            stdio: 'pipe', cwd: path.join(__dirname, '..')
        });
    } catch (e) {}

    try {
        execSync(`git push origin ${branch}`, { stdio: 'inherit', cwd: path.join(__dirname, '..') });
    } catch (e) {
        console.warn('⚠️  Git push failed, continuing to release...');
    }

    // Upload: artifacts + metadata
    const allFiles = [...selected, ...metadata].map(f => `"dist/${f}"`).join(' ');

    console.log('\n🎯 Creating GitHub Release...');
    try {
        execSync(
            `gh release create v${version.tag} ${allFiles} --title "v${version.tag}" --notes "TeleShift v${version.tag}" --clobber`,
            { stdio: 'inherit', cwd: path.join(__dirname, '..') }
        );
        console.log(`\n✅ v${version.tag} published. Auto-update will pick it up.`);
    } catch (e) {
        console.error('❌ Release failed:', e.message);
        process.exit(1);
    }
}

run();
