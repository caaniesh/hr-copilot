/**
 * Vercel static build: mirror FastAPI layout — /index.html and /static/* assets.
 * Copies every file from app/static except index.html (goes to public/).
 */
const fs = require("fs");
const path = require("path");

const root = __dirname;
const srcDir = path.join(root, "app", "static");
const outDir = path.join(root, "public");
const outStatic = path.join(outDir, "static");

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outStatic, { recursive: true });

const entries = fs.readdirSync(srcDir, { withFileTypes: true });
for (const ent of entries) {
  if (!ent.isFile()) {
    continue;
  }
  const name = ent.name;
  const from = path.join(srcDir, name);
  if (name === "index.html") {
    fs.copyFileSync(from, path.join(outDir, "index.html"));
  } else {
    fs.copyFileSync(from, path.join(outStatic, name));
  }
}

console.log("Static site built into public/");
