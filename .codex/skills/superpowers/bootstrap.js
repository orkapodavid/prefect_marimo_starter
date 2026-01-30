const fs = require('fs');
const path = require('path');
const os = require('os');
const skillsCore = require('./lib/skills-core');

// Paths - Adapted for local project structure
const projectRoot = path.resolve(__dirname, '../../../../');
const superpowersSkillsDir = path.join(__dirname, 'skills');
const personalSkillsDir = path.join(projectRoot, '.agents', 'skills');
const bootstrapFile = path.join(__dirname, 'bootstrap-content.md');
const superpowersRepoDir = __dirname;

// Utility functions
function printSkill(skillPath, sourceType) {
    const skillFile = path.join(skillPath, 'SKILL.md');
    let relPath;

    if (sourceType === 'personal') {
        relPath = path.relative(personalSkillsDir, skillPath);
    } else {
        relPath = path.relative(superpowersSkillsDir, skillPath);
    }

    // Print skill name with namespace
    if (sourceType === 'personal') {
        console.log(relPath.replace(/\\/g, '/')); // Personal skills are not namespaced
    } else {
        console.log(`superpowers:${relPath.replace(/\\/g, '/')}`); // Superpowers skills get superpowers namespace
    }

    // Extract and print metadata
    const { name, description } = skillsCore.extractFrontmatter(skillFile);

    if (description) console.log(`  ${description}`);
    console.log('');
}

// Commands
function runFindSkills() {
    console.log('Available skills:');
    console.log('==================');
    console.log('');

    const foundSkills = new Set();

    // Find personal skills first (these take precedence)
    // Note: since superpowers is a subdirectory of .agents/skills, we might need to filter it out if listing recursively from root
    // But findSkillsInDir finds SKILL.md. superpowers folder itself doesn't have SKILL.md, only its children.

    // Actually, in this setup, personalSkillsDir IS the parent of superpowers. 
    // We should be careful not to list superpowers skills as personal skills if they are just inside the repo.
    // However, the user asked to move skills to .agents/skills, but we are keeping them in superpowers/skills for now based on the repo structure we are mimicking.

    const personalSkills = skillsCore.findSkillsInDir(personalSkillsDir, 'personal', 2);
    for (const skill of personalSkills) {
        // Exclude skills inside superpowers dir if found via personalDir traversal
        if (skill.path.includes('superpowers')) continue;

        const relPath = path.relative(personalSkillsDir, skill.path);
        foundSkills.add(relPath);
        printSkill(skill.path, 'personal');
    }

    // Find superpowers skills
    const superpowersSkills = skillsCore.findSkillsInDir(superpowersSkillsDir, 'superpowers', 1);
    for (const skill of superpowersSkills) {
        const relPath = path.relative(superpowersSkillsDir, skill.path);
        if (!foundSkills.has(relPath)) {
            printSkill(skill.path, 'superpowers');
        }
    }

    console.log('Skill naming:');
    console.log('  Superpowers skills: superpowers:skill-name');
    console.log('  Personal skills: skill-name');
    console.log('');
}

function runUseSkill(skillName) {
    const result = skillsCore.resolveSkillPath(skillName, superpowersSkillsDir, personalSkillsDir);

    if (!result) {
        console.error(`Skill not found: ${skillName}`);
        process.exit(1);
    }

    console.log(`Loading skill: ${skillName} from ${result.skillFile}`);
    console.log('');
    try {
        const content = fs.readFileSync(result.skillFile, 'utf8');
        console.log(content);
    } catch (e) {
        console.error(`Error reading skill file: ${e.message}`);
    }
}

function runBootstrap() {
    console.log('# Superpowers Bootstrap');
    console.log('# ======================');
    console.log('');

    // Show the bootstrap instructions
    if (fs.existsSync(bootstrapFile)) {
        console.log('## Bootstrap Instructions:');
        console.log('');
        try {
            const content = fs.readFileSync(bootstrapFile, 'utf8');
            console.log(content);
        } catch (error) {
            console.log(`Error reading bootstrap file: ${error.message}`);
        }
        console.log('');
        console.log('---');
        console.log('');
    }

    // Run find-skills to show available skills
    console.log('## Available Skills:');
    console.log('');
    runFindSkills();

    console.log('');
    console.log('---');
    console.log('');

    // Load the using-superpowers skill automatically
    console.log('## Auto-loading superpowers:using-superpowers skill:');
    console.log('');
    runUseSkill('superpowers:using-superpowers');

    console.log('');
    console.log('# Bootstrap Complete!');
}

// Main execution
const args = process.argv.slice(2);
const command = args[0] || 'bootstrap';

switch (command) {
    case 'bootstrap':
        runBootstrap();
        break;
    case 'use-skill':
        if (!args[1]) {
            console.error('Usage: node bootstrap.js use-skill <skill-name>');
            process.exit(1);
        }
        runUseSkill(args[1]);
        break;
    default:
        console.log('Usage: node bootstrap.js [bootstrap|use-skill <name>]');
}
