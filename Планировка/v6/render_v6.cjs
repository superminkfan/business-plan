// Run with Node and the sharp package available through NODE_PATH.
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

(async () => {
  for (const filename of fs.readdirSync(__dirname).filter(x => x.endsWith('.svg'))) {
    const input = path.join(__dirname, filename);
    const output = path.join(__dirname, filename.replace('.svg', '.png'));
    const meta = await sharp(input).metadata();
    await sharp(input, { density: 108, limitInputPixels: false })
      .resize({ width: Math.round(meta.width * 1.5) })
      .png().withMetadata({ density: 300 }).toFile(output);
    console.log(path.basename(output));
  }
})().catch(error => { console.error(error); process.exit(1); });
