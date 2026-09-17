const express = require("express");

const app = express();
const PORT = 3000;

app.get("/", (req, res) => {
  res.send("<h1>Hello World from Docker Multi-Stage Build!</h1><p>Anshul Mohanty - 24BCS10191</p>");
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
