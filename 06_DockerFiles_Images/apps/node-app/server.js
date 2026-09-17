const express = require("express");
const app = express();
app.get("/", (req, res) =>
  res.send("<h1>Node.js app</h1><p>Anshul Mohanty - 24BCS10191</p>"));
app.listen(3000, () => console.log("Node app listening on 3000"));
