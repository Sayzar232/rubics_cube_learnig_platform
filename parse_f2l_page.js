/**
 * Collect every F2L case of a saved SpeedCubeDB page.
 *
 * The F2L page has no `jcube`/`data-us` sticker data (unlike OLL and PLL), so a
 * case diagram can only come from its inline `<svg width="75">` - the isometric
 * picture that parse_f2l_svg.js reads. This script turns the whole page into:
 *
 *   - the situations map {"f2l-01": {F, R, U}, ...} merged into
 *     frontend/src/situations.json (the file the web app imports);
 *   - the case metadata (number, name, group, formula, video) for the database
 *     (see the F2L seed migration and SpeedCubeDbParser).
 *
 * The formula of a case is the standard algorithm of its first slot ("Front
 * Right"), the group is the SpeedCubeDB subgroup ("Free Pairs", ...) and the
 * video is the first YouTube link of the case row.
 *
 * Run:
 *   node parse_f2l_page.js                     # response.html -> situations.json
 *   node parse_f2l_page.js --dry-run           # только проверка, без записи
 *   node parse_f2l_page.js --html page.html --merge out/situations.json
 *   node parse_f2l_page.js --html page.html --cases f2l_cases.json
 *   node parse_f2l_page.js --url https://speedcubedb.com/a/3x3/F2L
 *
 * `--url` перезаписывает файл `--html` (по умолчанию response.html), после чего
 * разбор идёт по нему: страницу можно скачать здесь же или сохранить заранее
 * (например, через Selenium — в «сыром» ответе SpeedCubeDB иногда нет
 * инлайновых диаграмм).
 */

const fs = require("fs");
const path = require("path");
const { parseSituation } = require("./parse_f2l_svg.js");

const CATEGORY = "F2L";
const DEFAULT_HTML = "response.html";
const DEFAULT_MERGE = path.join("frontend", "src", "situations.json");
const ROW_SEPARATOR = 'class="row singlealgorithm';

const ENTITIES = Object.freeze({
  "&amp;": "&",
  "&quot;": '"',
  "&#39;": "'",
  "&#x27;": "'",
  "&apos;": "'",
  "&nbsp;": " ",
  "&lt;": "<",
  "&gt;": ">",
});

function decodeEntities(value) {
  return value.replace(/&[#a-zA-Z0-9]+;/g, (entity) => ENTITIES[entity] ?? entity);
}

function situationKey(number) {
  return `${CATEGORY.toLowerCase()}-${String(number).padStart(2, "0")}`;
}

function attribute(row, name) {
  const match = row.match(new RegExp(`${name}="([^"]*)"`));
  return match ? decodeEntities(match[1]).trim() : "";
}

function rowText(row, pattern) {
  const match = row.match(pattern);
  return match ? decodeEntities(match[1]).replace(/\s+/g, " ").trim() : "";
}

function absolute(href) {
  if (!href) return null;
  return /^https?:\/\//i.test(href) ? href : `https://speedcubedb.com/${href.replace(/^\//, "")}`;
}

/** One case row (the page is split on `class="row singlealgorithm"`). */
function parseCaseRow(row) {
  const name = attribute(row, "data-alg");
  const number = Number(/(\d+)$/.exec(name)?.[1]);
  if (!name || !Number.isInteger(number)) {
    throw new Error(`row without a "F2L <number>" name: ${name || row.slice(0, 80)}`);
  }

  const svg = row.match(/<svg[^>]*width="75"[\s\S]*?<\/svg>/)?.[0];
  if (!svg) {
    throw new Error(`${name}: no 75px diagram in the row`);
  }

  return {
    number,
    name,
    group: attribute(row, "data-subgroup") || "Uncategorized",
    formula: rowText(row, /class="formatted-alg"[^>]*>([\s\S]*?)</),
    video_url: absolute(row.match(/href="([^"]*youtube\.com[^"]*)"/)?.[1] ?? ""),
    image_url: `/assets/algorithms/${situationKey(number)}.svg`,
    situation: parseSituation(svg),
  };
}

function collectCases(html) {
  const rows = html.split(ROW_SEPARATOR).slice(1);
  if (!rows.length) {
    throw new Error("no F2L rows found - is this the saved SpeedCubeDB F2L page?");
  }

  const cases = rows.map(parseCaseRow).sort((left, right) => left.number - right.number);
  cases.forEach((item, index) => {
    if (item.number !== index + 1) {
      throw new Error(`expected case ${index + 1}, got ${item.number} (${item.name})`);
    }
  });

  return cases;
}

/** F2L keys first (CFOP stage order), then the existing keys unchanged. */
function mergeSituations(existing, cases) {
  const merged = {};
  for (const item of cases) {
    merged[situationKey(item.number)] = item.situation;
  }
  for (const [key, value] of Object.entries(existing)) {
    if (!(key in merged)) merged[key] = value;
  }
  return merged;
}

function readJson(file) {
  if (!fs.existsSync(file)) return {};
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function writeJson(file, value) {
  const target = path.resolve(file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  return target;
}

function parseArgs(argv) {
  const options = { html: DEFAULT_HTML, url: "", merge: DEFAULT_MERGE, cases: "", dryRun: false };
  const valueFlags = { "--html": "html", "--url": "url", "--merge": "merge", "--cases": "cases" };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (argument === "--no-merge") {
      options.merge = "";
      continue;
    }
    const key = valueFlags[argument];
    if (!key) throw new Error(`Unknown option: ${argument}; see the header of this file`);
    index += 1;
    if (index >= argv.length) throw new Error(`${argument} expects a value`);
    options[key] = argv[index];
  }
  return options;
}

async function loadHtml({ html, url }) {
  if (!url) return fs.readFileSync(html, "utf8");
  const response = await fetch(url, { headers: { "User-Agent": "CFOP Trainer/1.0" } });
  if (!response.ok) throw new Error(`${url} -> HTTP ${response.status}`);
  const text = await response.text();
  fs.writeFileSync(html, text, "utf8");
  return text;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const cases = collectCases(await loadHtml(options));

  const groups = new Map();
  for (const item of cases) groups.set(item.group, (groups.get(item.group) ?? 0) + 1);
  console.log(`Cases: ${cases.length} (${[...groups].map(([group, count]) => `${group}: ${count}`).join(", ")})`);
  console.log(`First: ${cases[0].name} - ${cases[0].formula}`);
  console.log(`Last:  ${cases.at(-1).name} - ${cases.at(-1).formula}`);

  if (options.dryRun) {
    console.log("Dry run: nothing written.");
    return;
  }

  if (options.merge) {
    const merged = mergeSituations(readJson(options.merge), cases);
    console.log(`Merged ${cases.length} cases into ${writeJson(options.merge, merged)}`);
  }

  if (options.cases) {
    const metadata = cases.map(({ situation, ...rest }) => rest);
    console.log(`Cases written to ${writeJson(options.cases, metadata)}`);
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = {
  CATEGORY,
  collectCases,
  mergeSituations,
  parseArgs,
  parseCaseRow,
  situationKey,
};
