import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const docsRoot = path.resolve("docs");
const allowedLocomoUrlPrefixes = [
  "https://github.com/snap-research/locomo",
  "https://snap-research.github.io/locomo",
];
const forbiddenPatterns = [
  {
    description: "the obsolete Shopify/locomo repository link",
    pattern: /Shopify\/locomo/gi,
  },
  {
    description: "attributing LOCOMO to Shopify",
    pattern: /(?:Shopify\s*开发[^\n。]*LOCOMO|LOCOMO[^\n。]*Shopify\s*开发)/gi,
  },
];

async function findMarkdownFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return findMarkdownFiles(entryPath);
      }
      return entry.isFile() && entry.name.endsWith(".md") ? [entryPath] : [];
    }),
  );
  return files.flat();
}

function locomoUrls(content) {
  return [...content.matchAll(/https?:\/\/[^\s)<]+/g)]
    .map((match) => match[0])
    .filter((url) => url.toLowerCase().includes("locomo"));
}

const markdownFiles = await findMarkdownFiles(docsRoot);
const failures = [];

for (const file of markdownFiles) {
  const content = await readFile(file, "utf8");
  const relativePath = path.relative(process.cwd(), file);

  for (const { description, pattern } of forbiddenPatterns) {
    if (pattern.test(content)) {
      failures.push(`${relativePath}: contains ${description}`);
    }
    pattern.lastIndex = 0;
  }

  for (const url of locomoUrls(content)) {
    if (!allowedLocomoUrlPrefixes.some((prefix) => url.startsWith(prefix))) {
      failures.push(`${relativePath}: uses an unapproved LOCOMO URL: ${url}`);
    }
  }
}

if (failures.length > 0) {
  console.error("Documentation reference check failed:\n" + failures.join("\n"));
  process.exit(1);
}

console.log(`Checked LOCOMO references in ${markdownFiles.length} Markdown files.`);
