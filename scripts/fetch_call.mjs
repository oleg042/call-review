#!/usr/bin/env node
// Fetch one call (or list candidates) from the OneAway meetings DB (Grain recordings, read-only role).
//
// Usage:
//   node fetch_call.mjs <meeting-id | portal link | grain link> <outDir>
//   node fetch_call.mjs --search "<name, company or email fragment>"
//   node fetch_call.mjs --recent [N]            # latest N external calls (default 15)
//
// Writes <outDir>/transcript.txt (one speaker turn per line, "Name: text") and <outDir>/meta.json.
// Reads MEETINGS_DATABASE_URL from the env or from the oneaway-app .env.
import fs from "fs";
import path from "path";

// The oneaway-app checkout supplies the database driver and the .env; override with ONEAWAY_APP_DIR.
const APP = process.env.ONEAWAY_APP_DIR || path.join(process.env.HOME, "Projects/oneaway-app");
const { neon } = await import(`${APP}/node_modules/@neondatabase/serverless/index.mjs`);

function dbUrl() {
  if (process.env.MEETINGS_DATABASE_URL) return process.env.MEETINGS_DATABASE_URL;
  const line = fs.readFileSync(path.join(APP, ".env"), "utf8").split("\n").find((l) => l.startsWith("MEETINGS_DATABASE_URL="));
  if (!line) throw new Error("MEETINGS_DATABASE_URL not found in env or oneaway-app/.env");
  return line.slice(line.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "");
}
const sql = neon(dbUrl());
const fmt = (r) => `${r.at}  ${String(r.min).padStart(3)}m  ${r.scope ?? ""}  ${r.title}  |  ${(r.participants || []).map((p) => `${p.name}${p.email ? `<${p.email}>` : ""}`).join(", ")}  |  ${r.id}`;

const [arg, outDir] = process.argv.slice(2);
if (!arg) { console.error("usage: fetch_call.mjs <id|link> <outDir> | --search <q> | --recent [N]"); process.exit(1); }

if (arg === "--search" || arg === "--recent") {
  const q = arg === "--search" ? `%${outDir ?? ""}%` : "%";
  const limit = arg === "--recent" ? Number(outDir) || 15 : 15;
  const rows = await sql`
    SELECT m.id, m.title, m.meeting_type_scope AS scope, to_char(m.start_at, 'YYYY-MM-DD HH24:MI') AS at,
           round(m.duration_ms / 60000.0) AS min, m.participants
    FROM meetings m
    WHERE m.status = 'ready'
      AND (${arg === "--recent"} OR m.title ILIKE ${q} OR m.participants::text ILIKE ${q})
      AND (${arg === "--search"} OR m.meeting_type_scope = 'external')
    ORDER BY m.start_at DESC LIMIT ${limit}`;
  rows.forEach((r) => console.log(fmt(r)));
  if (!rows.length) console.log("no matches");
  process.exit(0);
}

// Accept a bare id, a portal link (?meeting=<uuid>), or a Grain share link (matched on meetings.url).
const uuid = arg.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
const isGrain = /grain\.com/.test(arg);
const [r] = isGrain
  ? await sql`SELECT m.*, to_char(m.start_at,'YYYY-MM-DD HH24:MI') AS at, round(m.duration_ms/60000.0) AS min, t.content FROM meetings m JOIN transcripts t ON t.meeting_id = m.id WHERE m.url = ${arg.split("?")[0]} OR m.url LIKE ${arg.split("?")[0] + "%"} LIMIT 1`
  : await sql`SELECT m.*, to_char(m.start_at,'YYYY-MM-DD HH24:MI') AS at, round(m.duration_ms/60000.0) AS min, t.content FROM meetings m JOIN transcripts t ON t.meeting_id = m.id WHERE m.id = ${uuid ? uuid[0] : arg} LIMIT 1`;
if (!r) { console.error(`no ready meeting with a transcript for: ${arg}`); process.exit(2); }
if (!outDir) { console.error("outDir required"); process.exit(1); }

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "transcript.txt"), r.content);
const meta = {
  id: r.id, title: r.title, date: r.at, minutes: Number(r.min), scope: r.meeting_type_scope, grainUrl: r.url,
  portalUrl: `https://portal.oneaway.io/tasks?board=meetings&meeting=${r.id}`,
  participants: (r.participants || []).map((p) => ({ name: p.name, email: p.email || null, scope: p.scope || null })),
  grainSummary: r.ai_summary || null,
};
fs.writeFileSync(path.join(outDir, "meta.json"), JSON.stringify(meta, null, 2));
console.log(`${meta.title} | ${meta.date} | ${meta.minutes}m | ${meta.participants.map((p) => p.name).join(", ")}`);
console.log(`wrote ${outDir}/transcript.txt (${r.content.split("\n").length} lines) + meta.json`);
