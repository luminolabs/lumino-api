// Purpose: A simple Node.js server to serve multiple OpenAPI specs using Swagger UI.
// Usage: Run the server using `node api-specs.js` and visit http://localhost:5110 to view the API specs.
// Note: This script requires the `express`, `swagger-ui-express`, `yamljs` packages.
//       You can install them using `npm install express swagger-ui-express yamljs`.

const express = require('express');
const path = require('path');
const YAML = require('yamljs');
const swaggerUi = require('swagger-ui-express');
const fs = require('fs');

const app = express();
const PORT = 5110;
const apiSpecsPath = path.join(__dirname, 'api-specs');

// Middleware to serve static YAML files from the api-specs folder
app.use(express.static(apiSpecsPath));

// Serve Swagger UI assets
app.use('/', swaggerUi.serve);

// Helper function to load all YAML files from api-specs
const loadApiSpecs = () => {
    const specs = {};
    const files = fs.readdirSync(apiSpecsPath).filter(file => file.endsWith('.yml'));

    files.forEach(file => {
        const filePath = path.join(apiSpecsPath, file);
        const yamlContent = YAML.load(filePath);
        if (file != "common-structures.yml") {
            specs[file] = yamlContent;
        }
    });

    return specs;
};

// Dynamic Swagger UI setup to load and visualize the YAML files
app.get('/:file', (req, res, next) => {
    const fileName = req.params.file;

    const filePath = path.join(apiSpecsPath, `${fileName}.yml`);
    if (fs.existsSync(filePath)) {
        const swaggerDocument = YAML.load(filePath);
        res.send(swaggerUi.generateHTML(swaggerDocument));
    } else {
        res.status(404).json({ error: 'Spec file not found' });
    }
});

// Serve the Swagger UI for visualizing the OpenAPI specs dynamically
app.get('/', (req, res) => {
    const specs = loadApiSpecs();
    res.send(`
    <html>
      <body>
        <h1>API Specs</h1>
        <ul>
          ${Object.keys(specs).map(file => `<li><a href="/${file.replace('.yml', '')}">${file}</a></li>`).join('')}
        </ul>
      </body>
    </html>
  `);
});

app.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}. Visit http://localhost:${PORT} to view the API specs.`);
});