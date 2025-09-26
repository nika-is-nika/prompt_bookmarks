#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

function findPythonExecutable() {
    const pythonCandidates = ['python3', 'python'];

    for (const candidate of pythonCandidates) {
        try {
            const result = spawn(candidate, ['--version'], { stdio: 'pipe' });
            return candidate;
        } catch (error) {
            continue;
        }
    }
    throw new Error('Python executable not found');
}

function installPythonDependencies() {
    return new Promise((resolve, reject) => {
        try {
            const pythonExe = findPythonExecutable();
            const scriptDir = __dirname;
            const requirementsPath = path.join(scriptDir, 'requirements.txt');

            console.log('Installing Python dependencies...');

            const installProcess = spawn(pythonExe, ['-m', 'pip', 'install', '-r', requirementsPath], {
                stdio: 'inherit',
                cwd: scriptDir
            });

            installProcess.on('close', (code) => {
                if (code === 0) {
                    console.log('Python dependencies installed successfully');
                    resolve();
                } else {
                    reject(new Error(`pip install failed with code ${code}`));
                }
            });

            installProcess.on('error', (error) => {
                reject(new Error(`Failed to run pip install: ${error.message}`));
            });

        } catch (error) {
            reject(error);
        }
    });
}

function runInstallScript() {
    return new Promise((resolve, reject) => {
        try {
            const pythonExe = findPythonExecutable();
            const scriptDir = __dirname;
            const installScriptPath = path.join(scriptDir, 'install.py');

            console.log('Running install script...');

            const installProcess = spawn(pythonExe, [installScriptPath], {
                stdio: 'inherit',
                cwd: scriptDir
            });

            installProcess.on('close', (code) => {
                if (code === 0) {
                    console.log('Install script completed successfully');
                    resolve();
                } else {
                    reject(new Error(`install.py failed with code ${code}`));
                }
            });

            installProcess.on('error', (error) => {
                reject(new Error(`Failed to run install.py: ${error.message}`));
            });

        } catch (error) {
            reject(error);
        }
    });
}

async function main() {
    try {
        await installPythonDependencies();
        await runInstallScript();
        console.log('Installation completed successfully!');
    } catch (error) {
        console.error(`Installation failed: ${error.message}`);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { installPythonDependencies, runInstallScript };