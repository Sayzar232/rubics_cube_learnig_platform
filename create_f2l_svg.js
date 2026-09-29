/**
 * Generate F2L situations as SpeedCubeDB style isometric SVG diagrams.
 *
 * A situation is described by three arrays of nine single letters:
 *
 *   F - the front face (drawn on the left), row by row, left to right
 *   R - the right face (drawn on the right), row by row, left to right
 *   U - the upper face, back row first, left to right inside a row
 *
 * N is the grey "not part of the case" sticker, the other letters are real
 * colours: W white, Y yellow, G green, R red, O orange, B blue.
 *
 * The geometry lives in frontend/src/f2l-diagram.json - the layout of the
 * reference diagram (f2l.svg): three dark quads that form the cube silhouette
 * followed by 27 sticker polygons in export order. Every sticker knows which
 * face and which of the nine cells it draws, so only the fills change between
 * situations, the generated file is byte identical to the export of the same
 * case and the web app draws exactly the same picture. The matching reader is
 * parse_f2l_svg.js (round trip: parse -> generate -> parse is stable).
 *
 * Run:
 *   node create_f2l_svg.js                          -> svg/f2l_01.svg
 *   node create_f2l_svg.js situation.json           -> svg/<name>.svg
 *   node create_f2l_svg.js situations.json svg      -> one file per situation
 *   node create_f2l_svg.js situation.json svg --pretty
 *
 * The JSON may be a single situation ({ F, R, U }) or a map of named
 * situations ({"f2l-01": { F, R, U }}), i.e. the shape used by
 * frontend/src/situations.json. Without arguments the built-in case from the
 * reference diagram is written.
 */

const fs = require("fs");
const path = require("path");

// Colours used by the downloaded SpeedCubeDB SVGs (lower-case hex).
const COLORS = Object.freeze({
  N: "#888888",
  W: "#ffffff",
  Y: "#ffff00",
  G: "#11aa00",
  R: "#d00000",
  O: "#ee8800",
  B: "#2040d0",
});

// Shared with the Vue component (frontend/src/App.vue) and the server-side
// renderer (backend/app/services/diagram_service.py): one geometry, one picture.
const GEOMETRY = JSON.parse(
  fs.readFileSync(path.join(__dirname, "frontend", "src", "f2l-diagram.json"), "utf8"),
);

const SVG_WIDTH = GEOMETRY.width;
const SVG_HEIGHT = GEOMETRY.height;
const SVG_HEADER =
  '<svg xmlns="http://www.w3.org/2000/svg" version="1.1"' +
  ' xmlns:xlink="http://www.w3.org/1999/xlink"' +
  ' xmlns:svgjs="http://svgjs.dev/svgjs"' +
  ` width="${SVG_WIDTH}" height="${SVG_HEIGHT}">`;
const FACES = Object.freeze(["F", "R", "U"]);
const DEFAULT_OUTPUT_DIR = "svg";

const BACKGROUND_POINTS = Object.freeze(GEOMETRY.backgrounds);
const STICKERS = Object.freeze(GEOMETRY.stickers);

const LETTERS = Object.freeze(Object.keys(COLORS));

function polygon(points, fill) {
  const paint = fill ? ` fill="${fill}"` : "";
  return `<polygon points="${points}"${paint}></polygon>`;
}

function validate(situation) {
  const keys = Object.keys(situation ?? {});
  const missing = FACES.filter((face) => !keys.includes(face));
  const extra = keys.filter((key) => !FACES.includes(key));

  if (missing.length || extra.length) {
    const details = [];
    if (missing.length) details.push(`missing keys: ${missing.join(", ")}`);
    if (extra.length) details.push(`unknown keys: ${extra.join(", ")}`);
    throw new Error(`Invalid F2L dictionary (${details.join("; ")})`);
  }

  for (const face of FACES) {
    const stickers = situation[face];
    if (!Array.isArray(stickers) || stickers.length !== 9) {
      throw new Error(`${face} must contain exactly 9 values`);
    }

    const invalid = stickers.filter((value) => !LETTERS.includes(value));
    if (invalid.length) {
      throw new Error(
        `${face} contains invalid values: ${[...new Set(invalid)].join(", ")}; ` +
          `use one of ${LETTERS.join(", ")}`,
      );
    }
  }
}

// The reference export is a single line, so the default output is too.
function buildSvg(situation, multiline = false) {
  validate(situation);

  const elements = BACKGROUND_POINTS.map((points) => polygon(points)).concat(
    STICKERS.map((sticker) =>
      polygon(sticker.points, COLORS[situation[sticker.face][sticker.cell]]),
    ),
  );

  const separator = multiline ? "\n" : "";
  const svg = [SVG_HEADER, ...elements, "</svg>"].join(separator);
  return multiline ? `${svg}\n` : svg;
}

function generateSvg(situation, filename, { multiline = false } = {}) {
  const svg = buildSvg(situation, multiline);
  const outputPath = path.resolve(filename);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, svg, "utf8");
  return outputPath;
}

function generateMany(situations, outputDir = DEFAULT_OUTPUT_DIR, options = {}) {
  return Object.entries(situations).map(([name, situation]) =>
    generateSvg(situation, path.join(outputDir, `${name}.svg`), options),
  );
}

function isSituation(value) {
  return (
    Boolean(value) &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    FACES.every((face) => Array.isArray(value[face]))
  );
}

// Accepts a single situation or a map of named ones, like situations.json
// (which is written with a UTF-8 BOM).
function loadSituations(filename) {
  const text = fs.readFileSync(filename, "utf8").replace(/^\uFEFF/, "");
  const data = JSON.parse(text);
  return isSituation(data) ? { [path.parse(filename).name]: data } : data;
}

function parseArgs(argv) {
  const unknown = argv.filter(
    (argument) => argument.startsWith("--") && argument !== "--pretty",
  );
  if (unknown.length) {
    throw new Error(`Unknown option: ${unknown.join(", ")}; supported: --pretty`);
  }

  const positional = argv.filter((argument) => !argument.startsWith("--"));
  return {
    input: positional[0],
    output: positional[1] || DEFAULT_OUTPUT_DIR,
    multiline: argv.includes("--pretty"),
  };
}

// The case of the reference diagram: cross solved, one pair slot still free.
const F2L_01 = {
  F: ["N", "N", "W", "G", "G", "N", "G", "G", "N"],
  R: ["O", "O", "N", "N", "O", "O", "N", "O", "O"],
  U: ["N", "N", "N", "N", "N", "G", "N", "N", "G"],
};

const F2L_SITUATIONS = { f2l_01: F2L_01 };

if (require.main === module) {
  const { input, output, multiline } = parseArgs(process.argv.slice(2));
  const situations = input ? loadSituations(input) : F2L_SITUATIONS;

  for (const filename of generateMany(situations, output, { multiline })) {
    console.log(`Created: ${filename}`);
  }
}

module.exports = {
  BACKGROUND_POINTS,
  COLORS,
  DEFAULT_OUTPUT_DIR,
  FACES,
  F2L_01,
  F2L_SITUATIONS,
  LETTERS,
  STICKERS,
  SVG_HEIGHT,
  SVG_WIDTH,
  buildSvg,
  generateMany,
  generateSvg,
  isSituation,
  loadSituations,
  parseArgs,
  validate,
};

