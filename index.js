#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

function findPythonExecutable() {
    // Try different Python executables in order of preference
    const pythonCandidates = ['python3', 'python'];

    for (const candidate of pythonCandidates) {
        try {
            // Check if the executable exists and can be called
            const result = spawn(candidate, ['--version'], { stdio: 'pipe' });
            return candidate;
        } catch (error) {
            // Continue to next candidate
        }
    }

    throw new Error('Python executable not found. Please install Python 3.x');
}

function checkPythonDependencies(pythonExe, scriptDir) {
    return new Promise((resolve, reject) => {
        const checkProcess = spawn(pythonExe, ['-c', 'import pydantic, mcp'], {
            cwd: scriptDir,
            stdio: 'pipe'
        });

        checkProcess.on('close', (code) => {
            if (code === 0) {
                resolve(true);
            } else {
                reject(new Error('Python dependencies not installed.'));
            }
        });

        checkProcess.on('error', () => {
            reject(new Error('Failed to check Python dependencies'));
        });
    });
}

function installPythonDependencies(pythonExe, scriptDir) {
    return new Promise((resolve, reject) => {
        const requirementsPath = path.join(scriptDir, 'requirements.txt');

        const installProcess = spawn(pythonExe, ['-m', 'pip', 'install', '-r', requirementsPath], {
            cwd: scriptDir,
            stdio: ['ignore', 'ignore', 'inherit'] // Redirect stdout to devnull, stderr to parent
        });

        installProcess.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`pip install failed with code ${code}`));
            }
        });

        installProcess.on('error', (error) => {
            reject(new Error(`Failed to run pip install: ${error.message}`));
        });
    });
}

function main() {
    try {
        // Get the directory where this script is located
        const scriptDir = __dirname;
        const runServerPath = path.join(scriptDir, 'run_server.py');

        // Check if run_server.py exists
        if (!fs.existsSync(runServerPath)) {
            console.error(`Error: run_server.py not found at ${runServerPath}`);
            process.exit(1);
        }

        // Find Python executable
        const pythonExe = findPythonExecutable();

        // Check Python dependencies and install if missing
        checkPythonDependencies(pythonExe, scriptDir).catch(async (error) => {
            console.error(`${error.message}`);
            console.error('Installing Python dependencies...');

            try {
                await installPythonDependencies(pythonExe, scriptDir);
                console.error('Dependencies installed successfully. Starting server...');
                startPythonServer(pythonExe, runServerPath, scriptDir);
            } catch (installError) {
                console.error(`Failed to install dependencies: ${installError.message}`);
                console.error('Please manually run: npm run install-python-deps');
                process.exit(1);
            }
        }).then(() => {
            startPythonServer(pythonExe, runServerPath, scriptDir);
        });

    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
}

function startPythonServer(pythonExe, runServerPath, scriptDir) {
    try {

        // Spawn the Python server process
        const pythonProcess = spawn(pythonExe, [runServerPath], {
            stdio: 'inherit', // Forward stdin, stdout, stderr to the parent process
            cwd: scriptDir
        });

        // Handle process events
        pythonProcess.on('error', (error) => {
            console.error(`Failed to start Python server: ${error.message}`);
            process.exit(1);
        });

        pythonProcess.on('exit', (code, signal) => {
            if (signal) {
                console.error(`Python server terminated by signal: ${signal}`);
            } else if (code !== 0) {
                console.error(`Python server exited with code: ${code}`);
            }
            process.exit(code || 0);
        });

        // Handle process termination gracefully
        process.on('SIGINT', () => {
            pythonProcess.kill('SIGINT');
        });

        process.on('SIGTERM', () => {
            pythonProcess.kill('SIGTERM');
        });

    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { main };