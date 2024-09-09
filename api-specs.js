// Usage: node api-specs.js

// This script serves multiple OpenAPI specs read from the 'api-specs' directory.

const express = require('express');
const swaggerUi = require('swagger-ui-express');
const YAML = require('yamljs');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 5110;

// Serve Swagger UI assets
app.use('/api-specs', swaggerUi.serve);

// Define the specs directory
const specsDir = path.join(__dirname, 'api-specs');

// Check if specs directory exists
let specs = [];
if (fs.existsSync(specsDir)) {
    // Load all YML files from the api-specs directory
    specs = fs.readdirSync(specsDir)
        .filter(file => file.endsWith('.yml'))
        .map(file => {
            const name = path.basename(file, '.yml');
            const filePath = path.join(specsDir, file);
            return { name, filePath };
        });
} else {
    console.warn(`Warning: The directory ${specsDir} does not exist. No API specs will be served.`);
}

// Create a route for each spec
specs.forEach(({ name, filePath }) => {
    app.get(`/api-specs/${name}`, (req, res, next) => {
        try {
            const spec = YAML.load(filePath);
            swaggerUi.setup(spec)(req, res, next);
        } catch (error) {
            console.error(`Error loading spec ${name}:`, error);
            res.status(500).send(`Error loading API spec: ${error.message}`);
        }
    });
});

// Serve an index page with links to all specs
app.get('/', (req, res) => {
    if (specs.length === 0) {
        res.send(`
      <html>
        <head><title>API Documentation</title></head>
        <body>
          <h1>No API Specifications Available</h1>
          <p>The api-specs directory is empty or does not exist. Please add your OpenAPI YML files to the 'api-specs' directory.</p>
        </body>
      </html>
    `);
    } else {
        const links = specs.map(({ name }) =>
            `<li><a href="/api-specs/${name}">${name} API</a></li>`
        ).join('');

        res.send(`
      <html>
        <head><title>API Documentation</title></head>
        <body>
          <h1>Available API Documentations:</h1>
          <ul>${links}</ul>
        </body>
      </html>
    `);
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
    if (specs.length > 0) {
        console.log('Available API docs:');
        specs.forEach(({ name }) => {
            console.log(`- http://localhost:${port}/api-specs/${name}`);
        });
    } else {
        console.log('No API specs available. Add YML files to the "api-specs" directory to serve them.');
    }
});