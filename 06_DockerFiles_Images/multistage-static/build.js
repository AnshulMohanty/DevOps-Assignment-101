// Stands in for a real front-end build step: generates the static site into dist/
const fs = require("fs");

fs.mkdirSync("dist", { recursive: true });
fs.writeFileSync(
  "dist/index.html",
  `<!doctype html>
<html>
  <head><title>Multi-Stage Build Demo</title></head>
  <body>
    <h1>Built with Node, served by NGINX</h1>
    <p>Anshul Mohanty - 24BCS10191</p>
  </body>
</html>
`
);
console.log("build complete -> dist/index.html");
