#!/usr/bin/env node
/**
 * Generates favicon.ico from public/favicon.png with 16x16 and 32x32 sizes.
 * Run from frontend/: node scripts/generate-favicon.mjs
 * This ensures DuckDuckGo and other crawlers that request /favicon.ico get a valid ICO.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';
import pngToIco from 'png-to-ico';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, '..', 'public');
const srcPng = path.join(publicDir, 'favicon.png');
const outIco = path.join(publicDir, 'favicon.ico');

async function main() {
  if (!fs.existsSync(srcPng)) {
    console.error('Missing public/favicon.png');
    process.exit(1);
  }
  const sizes = [16, 32];
  const buffers = await Promise.all(
    sizes.map((size) =>
      sharp(srcPng)
        .resize(size, size)
        .png()
        .toBuffer()
    )
  );
  const ico = await pngToIco(buffers);
  fs.writeFileSync(outIco, ico);
  console.log('Wrote public/favicon.ico (16x16, 32x32)');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
