#!/usr/bin/env node

const { spawn, execSync } = require('child_process');
const path = require('path');

// Locate python script relative to this wrapper
const scriptPath = path.join(__dirname, '../hf_autov3.py');

function getPythonCommand() {
    // Try 'python'
    try {
        execSync('python --version', { stdio: 'ignore' });
        return 'python';
    } catch (e) {}

    // Try 'python3'
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return 'python3';
    } catch (e) {}

    return null;
}

const pythonCmd = getPythonCommand();
if (!pythonCmd) {
    console.error('Error: Python was not found in your system PATH.');
    console.error('Please install Python (https://www.python.org/downloads/) and try again.');
    process.exit(1);
}

// Spawn the Python CLI shell in interactive mode
const child = spawn(pythonCmd, [scriptPath], { stdio: 'inherit' });

child.on('close', (code) => {
    process.exit(code || 0);
});
