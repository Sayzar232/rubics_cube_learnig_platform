/**
 * Generate OLL situations as SVG diagrams.
 *
 * A situation is described by five arrays:
 *
 *   U - the 3x3 upper face, left-to-right and top-to-bottom
 *   B - the three stickers behind the upper face (shown above U)
 *   F - the three stickers in front of the upper face (shown below U)
 *   L - the three stickers on the left, top-to-bottom
 *   R - the three stickers on the right, top-to-bottom
 *
 * Y means a yellow sticker and N means a non-yellow sticker.
 *
 * Run:
 *   node create_svg.js
 *
 * The example situation is written to svg/oll_01.svg. More situations
 * can be added to OLLS and will be generated in the same run.
 */

const fs = require("fs");
const path = require("path");

const COLORS = Object.freeze({
  Y: "#FFFF00",
  N: "#8D8D8D",
  BACKGROUND: "#111111",
  FRAME: "#000000",
});

// These values match the proportions of the reference diagram.
const SVG_WIDTH = 637;
const SVG_HEIGHT = 563;
const CELL = 123;
const EDGE_STICKER = 45;
const GAP = 13;
const FACE_X = 106;
const FACE_Y = 86;
const FACE_SIZE = CELL * 3 + GAP * 2;
const FACE_RADIUS = 16;
const EDGE_RADIUS = 8;

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function rect(x, y, width, height, fill, radius = 0) {
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}"` +
    ` rx="${radius}" ry="${radius}" fill="${escapeXml(fill)}"/>`;
}

function validate(state) {
  const expectedLengths = { U: 9, B: 3, F: 3, L: 3, R: 3 };
  const keys = Object.keys(state ?? {});
  const missing = Object.keys(expectedLengths).filter((key) => !(key in (state ?? {})));
  const extra = keys.filter((key) => !(key in expectedLengths));

  if (missing.length || extra.length) {
    const details = [];
    if (missing.length) details.push(`missing keys: ${missing.join(", ")}`);
    if (extra.length) details.push(`unknown keys: ${extra.join(", ")}`);
    throw new Error(`Invalid OLL dictionary (${details.join("; ")})`);
  }

  for (const [face, expectedLength] of Object.entries(expectedLengths)) {
    const stickers = state[face];
    if (!Array.isArray(stickers) || stickers.length !== expectedLength) {
      throw new Error(`${face} must contain exactly ${expectedLength} values`);
    }

    const invalid = stickers.filter((value) => value !== "Y" && value !== "N");
    if (invalid.length) {
      throw new Error(
        `${face} contains invalid values: ${[...new Set(invalid)].join(", ")}; use Y or N`,
      );
    }
  }
}

function generateSvg(state, filename) {
  validate(state);

  const columns = [0, 1, 2].map((index) => FACE_X + index * (CELL + GAP));
  const rows = [0, 1, 2].map((index) => FACE_Y + index * (CELL + GAP));
  const elements = [
    // Background and the black cross-shaped frame behind the stickers.
    rect(99, 21, 409, 59, COLORS.FRAME),
    rect(41, 79, 525, 409, COLORS.FRAME),
    rect(99, 488, 409, 59, COLORS.FRAME),
  ];

  // U: the 3x3 upper face.
  state.U.forEach((value, index) => {
    const row = Math.floor(index / 3);
    const column = index % 3;
    elements.push(
      rect(columns[column], rows[row], CELL, CELL, COLORS[value], FACE_RADIUS),
    );
  });

  // B is above U and F is below U.
  const topY = FACE_Y - GAP - EDGE_STICKER;
  const bottomY = FACE_Y + FACE_SIZE + GAP;
  state.B.forEach((value, column) => {
    elements.push(
      rect(columns[column], topY, CELL, EDGE_STICKER, COLORS[value], EDGE_RADIUS),
    );
  });
  state.F.forEach((value, column) => {
    elements.push(
      rect(columns[column], bottomY, CELL, EDGE_STICKER, COLORS[value], EDGE_RADIUS),
    );
  });

  // L and R are vertical strips, read from top to bottom.
  const leftX = FACE_X - GAP - EDGE_STICKER;
  const rightX = FACE_X + FACE_SIZE + GAP;
  state.L.forEach((value, row) => {
    elements.push(
      rect(leftX, rows[row], EDGE_STICKER, CELL, COLORS[value], EDGE_RADIUS),
    );
  });
  state.R.forEach((value, row) => {
    elements.push(
      rect(rightX, rows[row], EDGE_STICKER, CELL, COLORS[value], EDGE_RADIUS),
    );
  });

  const svg = [
    '<?xml version="1.0" encoding="utf-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" width="${SVG_WIDTH}" height="${SVG_HEIGHT}" viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}">`,
    ...elements.map((element) => `  ${element}`),
    "</svg>",
    "",
  ].join("\n");

  const outputPath = path.resolve(filename);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, svg, "utf8");
  return outputPath;
}

function generateMany(olls, outputDir = "svg") {
  return Object.entries(olls).map(([name, state]) =>
    generateSvg(state, path.join(outputDir, `${name}.svg`)),
  );
}

const OLL_01 = {
    "U": [
      "Y",
      "N",
      "Y",
      "N",
      "Y",
      "Y",
      "N",
      "Y",
      "N"
    ],
    "F": [
      "Y",
      "N",
      "Y"
    ],
    "R": [
      "N",
      "N",
      "N"
    ],
    "B": [
      "N",
      "Y",
      "N"
    ],
    "L": [
      "N",
      "Y",
      "N"
    ]
  };

const OLLS = { oll_01: OLL_01 };

if (require.main === module) {
  for (const filename of generateMany(OLLS)) {
    console.log(`Created: ${filename}`);
  }
}

module.exports = {
  COLORS,
  OLL_01,
  OLLS,
  generateSvg,
  generateMany,
  validate,
};
