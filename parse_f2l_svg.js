/**
 * Parse an F2L situation SVG diagram into a plain colour dictionary.
 *
 * The input is a SpeedCubeDB style isometric SVG (see f2l.svg): three dark
 * background quads describe the visible faces and 27 sticker polygons are
 * drawn on top of them, nine stickers per face.
 *
 * Only the three visible faces are returned, in this order:
 *
 *   F - the front face (drawn on the left), row by row, left to right
 *   R - the right face (drawn on the right), row by row, left to right
 *   U - the upper face, back row first, left to right inside each row
 *
 * Sticker values are single letters:
 *
 *   N - None (the grey "empty" sticker)
 *   W - white, Y - yellow, G - green, R - red, O - orange, B - blue
 *
 * Geometry, not document order, decides which sticker belongs where: every
 * sticker is assigned to the face quad that contains its centroid and is
 * then projected onto the axes of that parallelogram.
 *
 * Run:
 *   node parse_f2l_svg.js [input.svg] [output.json]
 *
 * Defaults: reads f2l.svg and writes f2l_situations.json next to this file.
 * The JSON is also printed to stdout.
 */

const fs = require("fs");
const path = require("path");

// Colours used by the downloaded SpeedCubeDB SVGs (lower-case hex).
const COLORS = Object.freeze({
  "#888888": "N",
  "#ffffff": "W",
  "#ffff00": "Y",
  "#11aa00": "G",
  "#d00000": "R",
  "#ee8800": "O",
  "#2040d0": "B",
});

const BACKGROUND_FILLS = new Set([null, "#000000"]);
const FACE_NAMES = Object.freeze({ TOP: "U", LEFT: "F", RIGHT: "R" });

function attribute(tag, name) {
  const match = tag.match(new RegExp(`(?:^|\\s)${name}\\s*=\\s*("([^"]*)"|'([^']*)')`));
  if (!match) return null;
  return match[2] !== undefined ? match[2] : match[3];
}

function expandHex(value) {
  if (/^#[0-9a-f]{3}$/.test(value)) {
    return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`;
  }
  if (/^#[0-9a-f]{8}$/.test(value)) {
    return value.slice(0, 7);
  }
  return value;
}

function normalizeFill(raw) {
  if (raw === null || raw === undefined) return null;
  const value = String(raw).trim().toLowerCase();
  if (value === "" || value === "none" || value === "black") return null;
  const rgb = value.match(/^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/);
  if (rgb) {
    const toHex = (part) => Number(part).toString(16).padStart(2, "0");
    return `#${toHex(rgb[1])}${toHex(rgb[2])}${toHex(rgb[3])}`;
  }
  if (value.startsWith("#")) return expandHex(value);
  return value;
}

function hexToRgb(hex) {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/.exec(hex);
  if (!match) return null;
  return {
    r: parseInt(match[1], 16),
    g: parseInt(match[2], 16),
    b: parseInt(match[3], 16),
  };
}

function parsePolygons(svgText) {
  const polygons = [];
  const pattern = /<polygon\b([^>]*)>/g;
  let match = pattern.exec(svgText);
  while (match) {
    const tag = match[1];
    const rawPoints = attribute(tag, "points");
    if (rawPoints) {
      const points = rawPoints
        .trim()
        .split(/\s+/)
        .map((pair) => {
          const [x, y] = pair.split(",").map(Number);
          if (!Number.isFinite(x) || !Number.isFinite(y)) {
            throw new Error(`invalid polygon point ${JSON.stringify(pair)}`);
          }
          return { x, y };
        });
      if (points.length >= 3) {
        polygons.push({ points, fill: attribute(tag, "fill") });
      }
    }
    match = pattern.exec(svgText);
  }
  if (!polygons.length) {
    throw new Error("no <polygon> elements found - expected a SpeedCubeDB isometric SVG");
  }
  return polygons;
}

function centroid(points) {
  const total = points.reduce(
    (accumulator, point) => ({ x: accumulator.x + point.x, y: accumulator.y + point.y }),
    { x: 0, y: 0 },
  );
  return { x: total.x / points.length, y: total.y / points.length };
}

function pointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i];
    const b = polygon[j];
    const crosses = a.y > point.y !== b.y > point.y;
    if (crosses && point.x < ((b.x - a.x) * (point.y - a.y)) / (b.y - a.y) + a.x) {
      inside = !inside;
    }
  }
  return inside;
}

function subtract(a, b) {
  return { x: a.x - b.x, y: a.y - b.y };
}

// Express `point` as origin + u * axisU + v * axisV for a parallelogram.
function project(origin, axisU, axisV, point) {
  const delta = subtract(point, origin);
  const determinant = axisU.x * axisV.y - axisU.y * axisV.x;
  if (Math.abs(determinant) < 1e-9) {
    throw new Error("degenerate face quadrilateral");
  }
  return {
    u: (delta.x * axisV.y - delta.y * axisV.x) / determinant,
    v: (axisU.x * delta.y - axisU.y * delta.x) / determinant,
  };
}

function indexOfMinY(points) {
  let index = 0;
  for (let i = 1; i < points.length; i += 1) {
    if (points[i].y < points[index].y) index = i;
  }
  return index;
}

// The upper face: rows run from the back edge towards the viewer, columns
// from left to right. The topmost corner is the far back corner; the two
// silhouette edges leaving it give the row and column directions.
function orientTopFace(corners) {
  const index = indexOfMinY(corners);
  const origin = corners[index];
  const previous = corners[(index + corners.length - 1) % corners.length];
  const next = corners[(index + 1) % corners.length];
  const left = previous.x < next.x ? previous : next;
  const right = previous.x < next.x ? next : previous;
  return { origin, colAxis: subtract(right, origin), rowAxis: subtract(left, origin) };
}

// A side face: the top edge is the edge closest to the upper face, the
// origin is its left end; rows go down the remaining edge leaving the
// origin, columns follow the top edge from left to right.
function orientSideFace(corners) {
  const edges = corners.map((point, index) => {
    const other = corners[(index + 1) % corners.length];
    return { a: point, b: other, middleY: (point.y + other.y) / 2 };
  });
  const topEdge = edges.reduce((best, edge) => (edge.middleY < best.middleY ? edge : best));
  const origin = topEdge.a.x <= topEdge.b.x ? topEdge.a : topEdge.b;
  const columnEnd = origin === topEdge.a ? topEdge.b : topEdge.a;
  const rowEdge = edges.find(
    (edge) => edge !== topEdge && (edge.a === origin || edge.b === origin),
  );
  if (!rowEdge) {
    throw new Error("unexpected face geometry: top corner has no downward edge");
  }
  const rowEnd = rowEdge.a === origin ? rowEdge.b : rowEdge.a;
  return { origin, colAxis: subtract(columnEnd, origin), rowAxis: subtract(rowEnd, origin) };
}

function letterFor(rawFill) {
  const fill = normalizeFill(rawFill);
  if (fill === null) {
    throw new Error("sticker polygon without a fill colour");
  }
  if (Object.prototype.hasOwnProperty.call(COLORS, fill)) {
    return COLORS[fill];
  }
  // Unknown colour: fall back to the closest palette entry so that slight
  // rendering differences (for example #12ab01) do not break the parse.
  const rgb = hexToRgb(fill);
  if (!rgb) {
    throw new Error(`unsupported sticker colour ${JSON.stringify(rawFill)}`);
  }
  let best = null;
  for (const [hex, letter] of Object.entries(COLORS)) {
    const palette = hexToRgb(hex);
    const distance =
      (rgb.r - palette.r) ** 2 + (rgb.g - palette.g) ** 2 + (rgb.b - palette.b) ** 2;
    if (best === null || distance < best.distance) {
      best = { letter, distance };
    }
  }
  return best.letter;
}

function gridFor(face) {
  const axes = face.kind === FACE_NAMES.TOP
    ? orientTopFace(face.quad.points)
    : orientSideFace(face.quad.points);

  const grid = new Array(9).fill(null);
  for (const sticker of face.stickers) {
    const { u, v } = project(
      axes.origin,
      axes.colAxis,
      axes.rowAxis,
      centroid(sticker.points),
    );
    if (u < -0.1 || u > 1.1 || v < -0.1 || v > 1.1) {
      throw new Error(`sticker does not align with the ${face.kind} face grid`);
    }
    const cell = (value) => Math.min(2, Math.max(0, Math.floor(value * 3)));
    const index = cell(v) * 3 + cell(u);
    if (grid[index] !== null) {
      throw new Error(`two stickers map to the same ${face.kind} cell`);
    }
    grid[index] = letterFor(sticker.fill);
  }
  if (grid.some((value) => value === null)) {
    throw new Error(`${face.kind} face is missing stickers`);
  }
  return grid;
}

/**
 * Parse the text of one F2L SVG into `{ F, R, U }` colour arrays.
 */
function parseSituation(svgText) {
  const polygons = parsePolygons(svgText);
  const backgrounds = polygons.filter((polygon) =>
    BACKGROUND_FILLS.has(normalizeFill(polygon.fill)),
  );
  const stickers = polygons.filter(
    (polygon) => !BACKGROUND_FILLS.has(normalizeFill(polygon.fill)),
  );

  if (backgrounds.length !== 3) {
    throw new Error(`expected 3 face backgrounds, got ${backgrounds.length}`);
  }

  const faces = backgrounds.map((quad) => ({
    quad,
    stickers: [],
    center: centroid(quad.points),
  }));
  for (const sticker of stickers) {
    const center = centroid(sticker.points);
    const face = faces.find((candidate) => pointInPolygon(center, candidate.quad.points));
    if (!face) {
      const position = `(${center.x.toFixed(1)}, ${center.y.toFixed(1)})`;
      throw new Error(`sticker at ${position} is outside every face`);
    }
    face.stickers.push(sticker);
  }
  for (const face of faces) {
    if (face.stickers.length !== 9) {
      throw new Error(`expected 9 stickers per face, got ${face.stickers.length}`);
    }
  }

  // Visible layout: the upper face is on top, the front face on the left,
  // the right face on the right.
  const upper = faces.reduce((best, face) => (face.center.y < best.center.y ? face : best));
  const sides = faces.filter((face) => face !== upper).sort((a, b) => a.center.x - b.center.x);
  upper.kind = FACE_NAMES.TOP;
  sides[0].kind = FACE_NAMES.LEFT;
  sides[1].kind = FACE_NAMES.RIGHT;

  return {
    [FACE_NAMES.LEFT]: gridFor(sides[0]),
    [FACE_NAMES.RIGHT]: gridFor(sides[1]),
    [FACE_NAMES.TOP]: gridFor(upper),
  };
}

function parseSvgFile(filename) {
  const resolved = path.resolve(filename);
  return parseSituation(fs.readFileSync(resolved, "utf8"));
}

if (require.main === module) {
  const input = process.argv[2] || path.join(__dirname, "f2l.svg");
  const output = process.argv[3] || path.join(__dirname, "f2l_situations.json");
  try {
    const situation = parseSvgFile(input);
    const json = JSON.stringify(situation, null, 2) + "\n";
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, json, "utf8");
    console.log(json.trim());
    console.log(`Saved situation to ${path.resolve(output)}`);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

module.exports = {
  COLORS,
  parsePolygons,
  parseSituation,
  parseSvgFile,
  letterFor,
};
