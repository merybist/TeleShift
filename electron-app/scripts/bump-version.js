const fs = require('fs');
const path = require('path');

function bumpVersion() {
    const packagePath = path.join(__dirname, '../package.json');
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const oldVersion = pkg.version;

    const now = new Date();
    const todayStr = `${now.getFullYear()}.${now.getMonth() + 1}.${now.getDate()}`;

    let attempt;
    if (oldVersion.startsWith(todayStr)) {
        const parts = oldVersion.split(/[.-]/);
        attempt = parseInt(parts[parts.length - 1] || '0') + 1;
    } else {
        attempt = 1;
    }

    const versionForPkg = `${todayStr}-${attempt}`;
    const versionForTag = `${todayStr}.${attempt}`;

    pkg.version = versionForPkg;
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2));
    console.log(`✅ Version: ${oldVersion} → ${versionForPkg} (tag: ${versionForTag})`);
    return { versionForPkg, versionForTag };
}

if (require.main === module) {
    bumpVersion();
}

module.exports = bumpVersion;
